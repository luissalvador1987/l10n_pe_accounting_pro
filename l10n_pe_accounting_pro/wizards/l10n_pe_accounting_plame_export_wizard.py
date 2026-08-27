# -*- coding: utf-8 -*-
import base64

from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nPeAccountingPlameExportWizard(models.TransientModel):
    _name = 'l10n_pe_accounting.plame.export.wizard'
    _description = 'Exportar información para PLAME/T-Registro'

    period_id = fields.Many2one('l10n_pe_accounting.plame.period', string="Periodo", required=True)

    def action_export(self):
        self.ensure_one()
        period = self.period_id
        if not period.line_ids:
            raise UserError(_("El periodo no tiene trabajadores cargados."))

        rows = []
        for line in period.line_ids:
            w = line.worker_id
            rows.append('|'.join([
                period.period, w.dni or '', w.name or '', w.worker_type or '',
                w.pension_regime or '', w.afp_cuspp or '', '%.2f' % line.basic_remuneration,
                '%.2f' % line.bonuses, '%.2f' % line.overtime, '%.2f' % line.gross_income,
                '%.2f' % line.essalud_contribution, '%.2f' % line.pension_contribution,
                '%.2f' % line.income_tax_retention, '%.2f' % line.net_pay,
            ]))
        content = '\r\n'.join(rows) + '\r\n'
        filename = "PLAME_%s_%s.txt" % (period.company_id.vat or 'RUC', period.period)
        attachment = self.env['ir.attachment'].create({
            'name': filename, 'type': 'binary',
            'datas': base64.b64encode(content.encode('iso-8859-1', errors='replace')),
            'res_model': self._name, 'res_id': self.id,
        })
        period.state = 'exported'
        return {
            'type': 'ir.actions.act_url', 'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
