# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nPeAccountingPerception(models.Model):
    _name = 'l10n_pe_accounting.perception'
    _description = 'Comprobante de Percepción de IGV'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    direction = fields.Selection([
        ('issued', 'Emitida (yo percibo a mi cliente, soy Agente de Percepción)'),
        ('received', 'Sufrida (mi proveedor me percibió a mí)'),
    ], string="Dirección", required=True, default='issued')
    number = fields.Char(string="N° de comprobante", copy=False, readonly=True)
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string="Cliente / Proveedor", required=True)
    company_id = fields.Many2one('res.company', string="Empresa", default=lambda self: self.env.company,
                                  required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')

    invoice_id = fields.Many2one('account.move', string="Comprobante", required=True)
    base_amount = fields.Monetary(string="Importe de la operación (con IGV)", required=True,
                                   currency_field='currency_id')
    rate = fields.Float(string="Tasa (%)", required=True, default=2.0)
    perception_amount = fields.Monetary(string="Monto percibido", compute='_compute_perception_amount',
                                         store=True, currency_field='currency_id')

    reclass_account_id = fields.Many2one(
        'account.account', string="Cuenta a reclasificar (solo si es 'sufrida')",
        help="Cuenta de gasto/compra donde el proveedor cargó el monto percibido dentro del total de "
             "su comprobante; se reclasificará hacia la cuenta de percepciones por aplicar.")

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Contabilizada'),
        ('cancelled', 'Anulada'),
    ], string="Estado", default='draft', required=True, tracking=True)
    move_id = fields.Many2one('account.move', string="Asiento de reclasificación", copy=False, readonly=True)

    @api.depends('base_amount', 'rate')
    def _compute_perception_amount(self):
        for rec in self:
            rec.perception_amount = rec.currency_id.round(rec.base_amount * rec.rate / 100.0) \
                if rec.currency_id else round(rec.base_amount * rec.rate / 100.0, 2)

    def action_post(self):
        for rec in self:
            rec._post_one()
        return True

    def _post_one(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se pueden contabilizar percepciones en borrador."))
        company = self.company_id
        if not self.number:
            self.number = company._l10n_pe_accounting_get_next_perception_sequence()

        if self.direction == 'issued':
            # La percepción emitida ya se agregó como línea del propio comprobante de venta
            # (ver account_move.py); aquí solo se registra el documento formal.
            self.write({'state': 'posted'})
            return

        if not self.reclass_account_id:
            raise UserError(_("Indica la cuenta a reclasificar para registrar una percepción sufrida."))
        contra_account = company.l10n_pe_perception_receivable_account_id
        if not contra_account:
            raise UserError(_(
                "Configura la cuenta 'IGV Percepciones por Aplicar' en Contabilidad > "
                "Configuración > Perú - Retenciones/Percepciones."))
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'), ('company_id', '=', company.id)], limit=1)
        move = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': journal.id, 'date': self.date,
            'ref': _("Percepción IGV sufrida - %s") % self.partner_id.name,
            'line_ids': [
                (0, 0, {
                    'name': _("Percepción IGV por aplicar %s") % self.number,
                    'account_id': contra_account.id, 'partner_id': self.partner_id.id,
                    'debit': self.perception_amount, 'credit': 0.0,
                }),
                (0, 0, {
                    'name': _("Reclasificación de percepción %s") % self.number,
                    'account_id': self.reclass_account_id.id, 'partner_id': self.partner_id.id,
                    'debit': 0.0, 'credit': self.perception_amount,
                }),
            ],
        })
        move.action_post()
        self.write({'state': 'posted', 'move_id': move.id})

    def action_cancel(self):
        for rec in self:
            if rec.move_id and rec.move_id.state == 'posted':
                rec.move_id.button_draft()
                rec.move_id.button_cancel()
            rec.state = 'cancelled'
