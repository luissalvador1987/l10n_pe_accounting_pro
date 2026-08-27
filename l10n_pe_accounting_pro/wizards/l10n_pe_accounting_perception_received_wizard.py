# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nPeAccountingPerceptionReceivedWizard(models.TransientModel):
    _name = 'l10n_pe_accounting.perception.received.wizard'
    _description = 'Registrar percepción de IGV sufrida en una compra'

    move_id = fields.Many2one('account.move', string="Comprobante de compra", required=True)
    partner_id = fields.Many2one(related='move_id.partner_id')
    currency_id = fields.Many2one(related='move_id.currency_id')
    base_amount = fields.Monetary(string="Importe de la operación (con IGV)", currency_field='currency_id')
    rate = fields.Float(string="Tasa (%)", default=2.0)
    reclass_account_id = fields.Many2one(
        'account.account', string="Cuenta a reclasificar", required=True,
        help="Cuenta de gasto/compra donde quedó incluido el monto percibido por el proveedor.")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move = self.env['account.move'].browse(res.get('move_id') or self.env.context.get('active_id'))
        if move:
            res['move_id'] = move.id
            res['base_amount'] = move.amount_total
        return res

    def action_confirm(self):
        self.ensure_one()
        if self.move_id.state != 'posted':
            raise UserError(_("El comprobante debe estar contabilizado antes de registrar la percepción."))
        perception = self.env['l10n_pe_accounting.perception'].create({
            'direction': 'received', 'partner_id': self.partner_id.id, 'invoice_id': self.move_id.id,
            'base_amount': self.base_amount, 'rate': self.rate,
            'reclass_account_id': self.reclass_account_id.id, 'company_id': self.move_id.company_id.id,
        })
        perception.action_post()
        return {'type': 'ir.actions.act_window_close'}
