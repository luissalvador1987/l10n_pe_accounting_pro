# -*- coding: utf-8 -*-
import base64

from odoo import _, fields, models
from odoo.exceptions import UserError


def _txt(value):
    if value is None or value is False:
        return ''
    return str(value)


def _amount(value):
    return '%.2f' % (value or 0.0)


class L10nPeAccountingPleExportWizard(models.TransientModel):
    _name = 'l10n_pe_accounting.ple.export.wizard'
    _description = 'Exportar Registro de Compras / Ventas (PLE)'

    company_id = fields.Many2one('res.company', string="Empresa", default=lambda self: self.env.company,
                                  required=True)
    period = fields.Char(string="Periodo (AAAAMM)", required=True)
    book_type = fields.Selection([
        ('purchase', 'Registro de Compras (Formato 8.1)'),
        ('sale', 'Registro de Ventas e Ingresos (Formato 14.1)'),
    ], required=True, default='purchase')

    def action_export(self):
        self.ensure_one()
        ruc = self.company_id.l10n_pe_edi_get_ruc() if hasattr(
            self.company_id, 'l10n_pe_edi_get_ruc') else (self.company_id.vat or '').replace('PE', '')

        if self.book_type == 'purchase':
            lines = self.env['l10n_pe_accounting.ple.purchase.line'].search([
                ('company_id', '=', self.company_id.id), ('period', '=', self.period)])
            book_code = '080100'
            row_builder = self._build_purchase_row
        else:
            lines = self.env['l10n_pe_accounting.ple.sale.line'].search([
                ('company_id', '=', self.company_id.id), ('period', '=', self.period)])
            book_code = '140100'
            row_builder = self._build_sale_row

        if not lines:
            raise UserError(_(
                "No hay líneas generadas para el periodo %s. Estas se generan automáticamente al "
                "contabilizar cada comprobante de compra/venta de ese periodo.") % self.period)

        rows = [row_builder(line) for line in lines]
        content = '\r\n'.join(rows) + '\r\n'
        filename = "LE%s%s00%s001.txt" % (ruc, self.period, book_code)
        attachment = self.env['ir.attachment'].create({
            'name': filename, 'type': 'binary',
            'datas': base64.b64encode(content.encode('iso-8859-1', errors='replace')),
            'res_model': self._name, 'res_id': self.id,
        })
        lines.write({'state': 'exported'})
        return {
            'type': 'ir.actions.act_url', 'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }

    @staticmethod
    def _build_purchase_row(line):
        fields_ = [
            line.period, line.cuo, line.cuo, _txt(line.emission_date), '', line.doc_type_code,
            line.series, line.number, '', line.partner_vat_type_code, line.partner_vat,
            line.partner_name, _amount(line.base_taxed), '0.00', '0.00', _amount(line.base_exempt),
            _amount(line.isc_amount), _amount(line.igv_amount), '0.00', '0.00',
            _amount(line.other_taxes_amount), _amount(line.total_amount), line.currency_code or 'PEN',
            '%.3f' % (line.exchange_rate or 1.0), '', '', '', '', '',
            line.detraction_constancia or '', '', '',
        ]
        return '|'.join(_txt(f) for f in fields_) + '|@'

    @staticmethod
    def _build_sale_row(line):
        fields_ = [
            line.period, line.cuo, line.cuo, _txt(line.emission_date), line.doc_type_code, line.series,
            line.number, line.partner_vat_type_code, line.partner_vat, line.partner_name,
            _amount(line.base_taxed), _amount(line.base_exempt), _amount(line.isc_amount),
            _amount(line.igv_amount), _amount(line.other_taxes_amount), _amount(line.total_amount),
            line.currency_code or 'PEN', '%.3f' % (line.exchange_rate or 1.0), '', '',
        ]
        return '|'.join(_txt(f) for f in fields_) + '|@'
