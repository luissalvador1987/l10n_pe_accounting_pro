# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pe_detraction_category_id = fields.Many2one(
        'l10n_pe_accounting.detraction.category', string="Bien/servicio sujeto a detracción (SPOT)",
        help="Si este producto/servicio está en el Anexo 1/2/3 de bienes y servicios sujetos al "
             "Sistema de Pago de Obligaciones Tributarias (SPOT), indica aquí su categoría para que "
             "la detracción se calcule sola en las facturas donde se use.")
