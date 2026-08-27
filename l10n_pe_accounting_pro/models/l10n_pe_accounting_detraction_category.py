# -*- coding: utf-8 -*-
from odoo import fields, models


class L10nPeAccountingDetractionCategory(models.Model):
    _name = 'l10n_pe_accounting.detraction.category'
    _description = 'Categoría de Detracción SPOT (Anexo 1/2/3)'
    _order = 'anexo, code'

    name = fields.Char(string="Bien/servicio", required=True)
    code = fields.Char(string="Código SPOT", required=True)
    anexo = fields.Selection([
        ('1', 'Anexo 1 (Bienes con tasa fija por Kg./unidad)'),
        ('2', 'Anexo 2 (Bienes)'),
        ('3', 'Anexo 3 (Servicios)'),
    ], string="Anexo", required=True, default='2')
    percentage = fields.Float(string="Porcentaje (%)", required=True)
    min_amount = fields.Float(
        string="Monto mínimo de la operación (S/)", default=700.0,
        help="Por debajo de este importe (S/ 700, salvo excepciones puntuales) no corresponde "
             "detracción para bienes/servicios del Anexo 2/3.")
    active = fields.Boolean(default=True)
    note = fields.Char(string="Nota")

    _sql_constraints = [
        ('uniq_code', 'unique(code)', 'Ya existe una categoría de detracción con ese código.'),
    ]
