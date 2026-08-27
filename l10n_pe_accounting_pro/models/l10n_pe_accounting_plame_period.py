# -*- coding: utf-8 -*-
from odoo import api, fields, models


class L10nPeAccountingPlamePeriodLine(models.Model):
    _name = 'l10n_pe_accounting.plame.period.line'
    _description = 'PLAME - Concepto del Trabajador en el Periodo'
    _order = 'worker_id'

    period_id = fields.Many2one('l10n_pe_accounting.plame.period', string="Periodo", required=True,
                                 ondelete='cascade')
    worker_id = fields.Many2one('l10n_pe_accounting.plame.worker', string="Trabajador", required=True)
    currency_id = fields.Many2one(related='period_id.currency_id')

    basic_remuneration = fields.Monetary(string="Remuneración básica", currency_field='currency_id')
    bonuses = fields.Monetary(string="Bonificaciones / asignaciones", currency_field='currency_id')
    overtime = fields.Monetary(string="Horas extra", currency_field='currency_id')
    gross_income = fields.Monetary(string="Total ingresos", compute='_compute_totals', store=True,
                                    currency_field='currency_id')

    essalud_rate = fields.Float(string="Tasa EsSalud empleador (%)", default=9.0)
    essalud_contribution = fields.Monetary(
        string="Aporte EsSalud (empleador)", compute='_compute_totals', store=True,
        currency_field='currency_id')
    pension_rate = fields.Float(string="Tasa aporte pensionario trabajador (%)", default=13.0)
    pension_contribution = fields.Monetary(
        string="Aporte pensionario (trabajador)", compute='_compute_totals', store=True,
        currency_field='currency_id')
    income_tax_retention = fields.Monetary(string="Retención renta 5ta/4ta categoría",
                                            currency_field='currency_id')
    net_pay = fields.Monetary(string="Neto a pagar", compute='_compute_totals', store=True,
                               currency_field='currency_id')

    @api.depends('basic_remuneration', 'bonuses', 'overtime', 'essalud_rate', 'pension_rate',
                 'income_tax_retention')
    def _compute_totals(self):
        for line in self:
            line.gross_income = line.basic_remuneration + line.bonuses + line.overtime
            line.essalud_contribution = line.gross_income * line.essalud_rate / 100.0
            line.pension_contribution = line.gross_income * line.pension_rate / 100.0
            line.net_pay = line.gross_income - line.pension_contribution - line.income_tax_retention


class L10nPeAccountingPlamePeriod(models.Model):
    _name = 'l10n_pe_accounting.plame.period'
    _description = 'Periodo PLAME/T-Registro'
    _order = 'period desc'
    _rec_name = 'period'

    company_id = fields.Many2one('res.company', string="Empresa", default=lambda self: self.env.company,
                                  required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    period = fields.Char(string="Periodo (AAAAMM)", required=True)
    line_ids = fields.One2many('l10n_pe_accounting.plame.period.line', 'period_id', string="Trabajadores")
    total_gross = fields.Monetary(string="Total ingresos", compute='_compute_totals', currency_field='currency_id')
    total_essalud = fields.Monetary(string="Total EsSalud", compute='_compute_totals',
                                     currency_field='currency_id')
    total_net = fields.Monetary(string="Total neto a pagar", compute='_compute_totals',
                                 currency_field='currency_id')
    state = fields.Selection([('draft', 'Borrador'), ('exported', 'Exportado')], default='draft')

    _sql_constraints = [
        ('uniq_company_period', 'unique(company_id, period)',
         'Ya existe un periodo PLAME para esta empresa.'),
    ]

    @api.depends('line_ids.gross_income', 'line_ids.essalud_contribution', 'line_ids.net_pay')
    def _compute_totals(self):
        for period in self:
            period.total_gross = sum(period.line_ids.mapped('gross_income'))
            period.total_essalud = sum(period.line_ids.mapped('essalud_contribution'))
            period.total_net = sum(period.line_ids.mapped('net_pay'))

    def action_load_active_workers(self):
        """Precarga una línea por cada trabajador activo de la empresa a la fecha del periodo,
        para no tener que ir agregándolos uno por uno."""
        for period in self:
            Worker = self.env['l10n_pe_accounting.plame.worker']
            existing = period.line_ids.mapped('worker_id')
            workers = Worker.search([('company_id', '=', period.company_id.id), ('active', '=', True),
                                      ('id', 'not in', existing.ids)])
            period.line_ids = [(0, 0, {'worker_id': w.id, 'basic_remuneration': 0.0}) for w in workers]
        return True
