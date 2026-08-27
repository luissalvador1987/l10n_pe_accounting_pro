# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nPeAccountingRetention(models.Model):
    _name = 'l10n_pe_accounting.retention'
    _description = 'Comprobante de Retención de IGV'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    direction = fields.Selection([
        ('issued', 'Emitida (yo retengo a mi proveedor, soy Agente de Retención)'),
        ('received', 'Sufrida (mi cliente me retuvo a mí)'),
    ], string="Dirección", required=True, default='issued')
    number = fields.Char(string="N° de comprobante", copy=False, readonly=True)
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string="Proveedor / Cliente", required=True)
    company_id = fields.Many2one('res.company', string="Empresa", default=lambda self: self.env.company,
                                  required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')

    invoice_ids = fields.Many2many(
        'account.move', string="Comprobantes afectados", required=True,
        help="Factura(s) de compra (si emites la retención) o de venta (si la sufriste) sobre las "
             "que se aplica esta retención.")
    base_amount = fields.Monetary(string="Importe de la operación", required=True,
                                   currency_field='currency_id')
    rate = fields.Float(string="Tasa (%)", required=True, default=3.0)
    retention_amount = fields.Monetary(string="Monto retenido", compute='_compute_retention_amount',
                                        store=True, currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Contabilizada'),
        ('cancelled', 'Anulada'),
    ], string="Estado", default='draft', required=True, tracking=True)
    move_id = fields.Many2one('account.move', string="Asiento contable", copy=False, readonly=True)

    @api.depends('base_amount', 'rate')
    def _compute_retention_amount(self):
        for rec in self:
            rec.retention_amount = rec.currency_id.round(rec.base_amount * rec.rate / 100.0) \
                if rec.currency_id else round(rec.base_amount * rec.rate / 100.0, 2)

    def action_post(self):
        for rec in self:
            rec._post_one()
        return True

    def _post_one(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se pueden contabilizar retenciones en borrador."))
        company = self.company_id
        if self.direction == 'issued':
            payable_account = self.partner_id.with_company(company).property_account_payable_id
            contra_account = company.l10n_pe_retention_payable_account_id
            if not contra_account:
                raise UserError(_(
                    "Configura la cuenta 'IGV Retenciones por Pagar' en Contabilidad > "
                    "Configuración > Perú - Retenciones/Percepciones."))
            line_vals = [
                (0, 0, {
                    'name': _("Retención IGV %s") % (self.number or ''),
                    'account_id': payable_account.id, 'partner_id': self.partner_id.id,
                    'debit': self.retention_amount, 'credit': 0.0,
                }),
                (0, 0, {
                    'name': _("Retención IGV %s") % (self.number or ''),
                    'account_id': contra_account.id, 'partner_id': self.partner_id.id,
                    'debit': 0.0, 'credit': self.retention_amount,
                }),
            ]
        else:
            receivable_account = self.partner_id.with_company(company).property_account_receivable_id
            contra_account = company.l10n_pe_retention_receivable_account_id
            if not contra_account:
                raise UserError(_(
                    "Configura la cuenta 'IGV Retenido por Terceros' en Contabilidad > "
                    "Configuración > Perú - Retenciones/Percepciones."))
            line_vals = [
                (0, 0, {
                    'name': _("Retención IGV sufrida %s") % (self.number or ''),
                    'account_id': contra_account.id, 'partner_id': self.partner_id.id,
                    'debit': self.retention_amount, 'credit': 0.0,
                }),
                (0, 0, {
                    'name': _("Retención IGV sufrida %s") % (self.number or ''),
                    'account_id': receivable_account.id, 'partner_id': self.partner_id.id,
                    'debit': 0.0, 'credit': self.retention_amount,
                }),
            ]

        journal = self.env['account.journal'].search([
            ('type', '=', 'general'), ('company_id', '=', company.id)], limit=1)
        move = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': journal.id, 'date': self.date,
            'ref': _("Retención IGV - %s") % self.partner_id.name,
            'line_ids': line_vals,
        })
        move.action_post()

        # Concilia la línea de retención contra las facturas afectadas, para que su saldo
        # pendiente baje exactamente en el monto retenido.
        target_account = payable_account if self.direction == 'issued' else receivable_account
        retention_line = move.line_ids.filtered(lambda l: l.account_id == target_account)
        open_invoice_lines = self.invoice_ids.line_ids.filtered(
            lambda l: l.account_id == target_account and not l.reconciled)
        (retention_line + open_invoice_lines).reconcile()

        if not self.number:
            seq_method = (company._l10n_pe_accounting_get_next_retention_sequence)
            self.number = seq_method()
        self.write({'state': 'posted', 'move_id': move.id})

    def action_cancel(self):
        for rec in self:
            if rec.move_id and rec.move_id.state == 'posted':
                rec.move_id.button_draft()
                rec.move_id.button_cancel()
            rec.state = 'cancelled'
