# -*- coding: utf-8 -*-
from odoo import fields, models


class L10nPeAccountingAssetTaxCategory(models.Model):
    _name = 'l10n_pe_accounting.asset.tax.category'
    _description = 'Categoría Tributaria de Depreciación (Art. 22 Reglamento LIR)'
    _order = 'max_annual_rate desc'

    name = fields.Char(string="Categoría de bien", required=True)
    max_annual_rate = fields.Float(
        string="Tasa máxima anual (%)", required=True,
        help="Porcentaje anual máximo aceptado tributariamente. Usarlo por encima del máximo genera "
             "una diferencia permanente (adición) en la declaración anual de renta.")
    note = fields.Char(string="Nota")
    active = fields.Boolean(default=True)
