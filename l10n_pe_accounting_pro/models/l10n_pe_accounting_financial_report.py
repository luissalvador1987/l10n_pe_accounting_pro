# -*- coding: utf-8 -*-
from odoo import fields, models


class L10nPeAccountingFinancialReportLine(models.Model):
    _name = 'l10n_pe_accounting.financial.report.line'
    _description = 'Línea de Estado Financiero NIIF (plantilla)'
    _order = 'report_type, sequence'

    name = fields.Char(required=True)
    report_type = fields.Selection([
        ('bs', 'Estado de Situación Financiera'),
        ('pl', 'Estado de Resultados'),
        ('cf', 'Estado de Flujo de Efectivo (versión base)'),
        ('eq', 'Estado de Cambios en el Patrimonio (versión base)'),
    ], required=True, index=True)
    sequence = fields.Integer(default=10)
    level = fields.Integer(default=0, help="0 = título de sección, 1 = línea, 2 = sub-línea (sangría).")
    code_prefixes = fields.Char(
        string="Prefijos de cuenta (PCGE)",
        help="Códigos de cuenta (separados por coma) cuyo saldo se suma en esta línea. Vacío si es "
             "una línea de total que se arma a partir de otras líneas (ver 'Componentes').")
    sign = fields.Integer(default=1, help="1 o -1: para invertir el signo natural de la cuenta al "
                                           "presentar (p.ej. mostrar el pasivo como positivo).")
    balance_mode = fields.Selection([
        ('as_of', 'Saldo a la fecha (cuentas de balance)'),
        ('period', 'Movimiento del periodo (cuentas de resultados)'),
    ], default='as_of', required=True)
    is_total = fields.Boolean(string="Es línea de total")
    component_line_ids = fields.Many2many(
        'l10n_pe_accounting.financial.report.line', 'l10n_pe_fin_report_line_component_rel',
        'line_id', 'component_id', string="Componentes (si es línea de total)")
    bold = fields.Boolean(string="Negrita")
