# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nPeAccountingRetentionPayWizard(models.TransientModel):
    _name = 'l10n_pe_accounting.retention.pay.wizard'
    _description = 'Aplicar retención de IGV a un comprobante de compra'

    move_id = fields.Many2one('account.move', string="Comprobante de compra", required=True)
    partner_id = fields.Many2one(related='move_id.partner_id')
    currency_id = fields.Many2one(related='move_id.currency_id')
    base_amount = fields.Monetary(string="Importe sobre el que se retiene", currency_field='currency_id')
    rate = fields.Float(string="Tasa (%)", default=3.0)
    retention_amount = fields.Monetary(string="Monto a retener", compute='_compute_retention_amount',
                                        currency_field='currency_id')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move = self.env['account.move'].browse(res.get('move_id') or self.env.context.get('active_id'))
        if move:
            res['move_id'] = move.id
            res['base_amount'] = move.amount_residual
            res['rate'] = move.company_id.l10n_pe_retention_rate or 3.0
        return res

    @api.depends('base_amount', 'rate')
    def _compute_retention_amount(self):
        for wiz in self:
            wiz.retention_amount = wiz.currency_id.round(wiz.base_amount * wiz.rate / 100.0) \
                if wiz.currency_id else round(wiz.base_amount * wiz.rate / 100.0, 2)

    def action_confirm(self):
        self.ensure_one()
        if self.move_id.state != 'posted':
            raise UserError(_("El comprobante debe estar contabilizado antes de aplicar la retención."))
        retention = self.env['l10n_pe_accounting.retention'].create({
            'direction': 'issued', 'partner_id': self.partner_id.id,
            'invoice_ids': [(6, 0, [self.move_id.id])], 'base_amount': self.base_amount,
            'rate': self.rate, 'company_id': self.move_id.company_id.id,
        })
        retention.action_post()
        # Abre el asistente estándar de "Registrar Pago" ya con el importe neto pendiente
        # (el residual del comprobante bajó automáticamente al conciliarse la retención).
        return {
            'type': 'ir.actions.act_window', 'name': _("Registrar Pago"),
            'res_model': 'account.payment.register', 'view_mode': 'form', 'target': 'new',
            'context': {
                'active_model': 'account.move', 'active_ids': [self.move_id.id],
                'active_id': self.move_id.id,
            },
        }
