# -*- coding: utf-8 -*-
from odoo import api, fields, models


class L10nPeAccountingDetraction(models.Model):
    _name = 'l10n_pe_accounting.detraction'
    _description = 'Detracción (SPOT) de un Comprobante'
    _order = 'id desc'
    _rec_name = 'move_id'

    move_id = fields.Many2one('account.move', string="Comprobante", required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='move_id.partner_id', store=True)
    move_type = fields.Selection(related='move_id.move_type', store=True)
    company_id = fields.Many2one(related='move_id.company_id', store=True)
    currency_id = fields.Many2one(related='move_id.currency_id', store=True)

    category_id = fields.Many2one('l10n_pe_accounting.detraction.category', string="Categoría SPOT",
                                   required=True)
    percentage = fields.Float(string="Porcentaje (%)", required=True)
    base_amount = fields.Monetary(string="Importe de la operación (con IGV)", required=True,
                                   currency_field='currency_id')
    detraction_amount = fields.Monetary(string="Monto a depositar", compute='_compute_detraction_amount',
                                         store=True, currency_field='currency_id')
    net_payable = fields.Monetary(string="Neto a pagar al proveedor", compute='_compute_detraction_amount',
                                   store=True, currency_field='currency_id')

    state = fields.Selection([
        ('pending', 'Pendiente de depósito'),
        ('deposited', 'Depositado'),
    ], string="Estado", default='pending', required=True)
    constancia_number = fields.Char(string="N° de Constancia de Depósito", copy=False)
    constancia_date = fields.Date(string="Fecha de depósito", copy=False)
    bank_account_id = fields.Many2one('res.partner.bank', string="Cuenta de detracciones usada")

    @api.depends('base_amount', 'percentage')
    def _compute_detraction_amount(self):
        for rec in self:
            rec.detraction_amount = rec.currency_id.round(rec.base_amount * rec.percentage / 100.0)
            rec.net_payable = rec.base_amount - rec.detraction_amount

    def action_register_deposit(self, constancia_number, constancia_date, bank_account_id=False):
        self.ensure_one()
        self.write({
            'state': 'deposited', 'constancia_number': constancia_number,
            'constancia_date': constancia_date, 'bank_account_id': bank_account_id,
        })
        self.move_id.message_post(body=self.env._(
            "Detracción depositada: %(amount)s (constancia N° %(number)s del %(date)s).",
            amount=self.detraction_amount, number=constancia_number, date=constancia_date))
