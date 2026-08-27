# -*- coding: utf-8 -*-
from odoo import fields, models


class L10nPeAccountingPlePurchase(models.Model):
    _name = 'l10n_pe_accounting.ple.purchase.line'
    _description = 'Registro de Compras (PLE) - Línea'
    _order = 'emission_date, id'
    _rec_name = 'move_id'

    move_id = fields.Many2one('account.move', string="Comprobante", required=True, ondelete='cascade')
    company_id = fields.Many2one(related='move_id.company_id', store=True)
    period = fields.Char(string="Periodo (AAAAMM)", required=True, index=True)
    cuo = fields.Char(string="CUO / Correlativo")

    emission_date = fields.Date(string="Fecha de emisión", required=True)
    doc_type_code = fields.Char(string="Tipo de comprobante (Cat. 10)", required=True)
    series = fields.Char(string="Serie")
    number = fields.Char(string="Número")

    partner_vat_type_code = fields.Char(string="Tipo doc. identidad (Cat. 6)")
    partner_vat = fields.Char(string="N° doc. identidad del proveedor")
    partner_name = fields.Char(string="Proveedor")

    base_taxed = fields.Monetary(string="Base imponible gravada", currency_field='currency_id')
    base_exempt = fields.Monetary(string="Adquisiciones no gravadas", currency_field='currency_id')
    isc_amount = fields.Monetary(string="ISC", currency_field='currency_id')
    igv_amount = fields.Monetary(string="IGV", currency_field='currency_id')
    other_taxes_amount = fields.Monetary(string="Otros tributos", currency_field='currency_id')
    total_amount = fields.Monetary(string="Importe total", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Moneda")
    currency_code = fields.Char(string="Código moneda (Cat. 4)")
    exchange_rate = fields.Float(string="Tipo de cambio", digits=(12, 3))

    is_subject_to_detraction = fields.Boolean(string="Sujeto a detracción")
    detraction_constancia = fields.Char(string="N° constancia de detracción")

    state = fields.Selection([('draft', 'Generado'), ('exported', 'Exportado')],
                              default='draft', string="Estado")
