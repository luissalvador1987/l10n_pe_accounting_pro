# -*- coding: utf-8 -*-
from odoo import fields, models


class L10nPeAccountingClosingLog(models.Model):
    _name = 'l10n_pe_accounting.closing.log'
    _description = 'Registro de Cierre Contable Asistido'
    _order = 'period desc'
    _rec_name = 'period'

    company_id = fields.Many2one('res.company', string="Empresa", default=lambda self: self.env.company,
                                  required=True)
    period = fields.Char(string="Periodo (AAAAMM)", required=True)

    cts_move_id = fields.Many2one('account.move', string="Asiento de provisión de CTS", copy=False)
    gratification_move_id = fields.Many2one(
        'account.move', string="Asiento de provisión de Gratificación", copy=False)
    vacation_move_id = fields.Many2one('account.move', string="Asiento de provisión de Vacaciones", copy=False)
    exchange_diff_move_id = fields.Many2one(
        'account.move', string="Asiento de diferencia de cambio", copy=False)
    ple_generated = fields.Boolean(string="PLE Compras/Ventas generado")
    notes = fields.Text(string="Notas del cierre")
    state = fields.Selection([
        ('in_progress', 'En proceso'),
        ('done', 'Cerrado'),
    ], string="Estado", default='in_progress', required=True)

    _sql_constraints = [
        ('uniq_company_period', 'unique(company_id, period)',
         'Ya existe un registro de cierre para esta empresa y periodo.'),
    ]

    def action_mark_done(self):
        self.write({'state': 'done'})
