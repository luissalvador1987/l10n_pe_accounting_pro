# -*- coding: utf-8 -*-
from odoo import fields, models


class L10nPeAccountingDetractionRegisterWizard(models.TransientModel):
    _name = 'l10n_pe_accounting.detraction.register.wizard'
    _description = 'Registrar depósito de detracción'

    detraction_id = fields.Many2one('l10n_pe_accounting.detraction', required=True)
    constancia_number = fields.Char(string="N° de Constancia de Depósito", required=True)
    constancia_date = fields.Date(string="Fecha de depósito", required=True, default=fields.Date.context_today)
    bank_account_id = fields.Many2one('res.partner.bank', string="Cuenta usada")

    def action_confirm(self):
        self.ensure_one()
        self.detraction_id.action_register_deposit(
            self.constancia_number, self.constancia_date, self.bank_account_id.id)
        return {'type': 'ir.actions.act_window_close'}
