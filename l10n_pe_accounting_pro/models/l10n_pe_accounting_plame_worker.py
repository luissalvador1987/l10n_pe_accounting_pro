# -*- coding: utf-8 -*-
from odoo import fields, models


class L10nPeAccountingPlameWorker(models.Model):
    _name = 'l10n_pe_accounting.plame.worker'
    _description = 'Trabajador (Censo básico para PLAME/T-Registro)'
    _order = 'name'

    name = fields.Char(string="Apellidos y nombres", required=True)
    dni = fields.Char(string="DNI", required=True)
    company_id = fields.Many2one('res.company', string="Empresa", default=lambda self: self.env.company,
                                  required=True)
    worker_type = fields.Selection([
        ('employee', 'Empleado (régimen laboral común)'),
        ('worker', 'Obrero (régimen laboral común)'),
        ('independent', 'Trabajador independiente (4ta categoría)'),
    ], string="Tipo de trabajador", default='employee', required=True)
    pension_regime = fields.Selection([
        ('onp', 'ONP (Sistema Nacional de Pensiones)'),
        ('afp_habitat', 'AFP Hábitat'),
        ('afp_integra', 'AFP Integra'),
        ('afp_prima', 'AFP Prima'),
        ('afp_profuturo', 'AFP Profuturo'),
        ('none', 'Ninguno / no aplica'),
    ], string="Régimen pensionario", default='onp')
    afp_cuspp = fields.Char(string="CUSPP (si está en AFP)")
    position = fields.Char(string="Cargo / ocupación")
    start_date = fields.Date(string="Fecha de ingreso", required=True)
    end_date = fields.Date(string="Fecha de cese")
    active = fields.Boolean(default=True)
