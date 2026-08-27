# -*- coding: utf-8 -*-
from odoo import api, fields, models


class L10nPeAccountingFinancialReportResultLine(models.TransientModel):
    _name = 'l10n_pe_accounting.financial.report.wizard.result.line'
    _description = 'Línea calculada de un Estado Financiero'
    _order = 'sequence'

    wizard_id = fields.Many2one('l10n_pe_accounting.financial.report.wizard', ondelete='cascade')
    sequence = fields.Integer()
    name = fields.Char()
    level = fields.Integer()
    bold = fields.Boolean()
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')


class L10nPeAccountingFinancialReportWizard(models.TransientModel):
    _name = 'l10n_pe_accounting.financial.report.wizard'
    _description = 'Generar Estado Financiero NIIF'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    report_type = fields.Selection([
        ('bs', 'Estado de Situación Financiera'),
        ('pl', 'Estado de Resultados'),
        ('cf', 'Estado de Flujo de Efectivo (versión base)'),
        ('eq', 'Estado de Cambios en el Patrimonio (versión base)'),
    ], required=True, default='bs')
    date_from = fields.Date(string="Desde", default=lambda self: fields.Date.context_today(self).replace(
        month=1, day=1))
    date_to = fields.Date(string="Hasta / Al", default=fields.Date.context_today)
    result_line_ids = fields.One2many(
        'l10n_pe_accounting.financial.report.wizard.result.line', 'wizard_id', string="Resultado")

    @staticmethod
    def _prefix_domain(code_prefixes):
        prefixes = [p.strip() for p in (code_prefixes or '').split(',') if p.strip()]
        if not prefixes:
            return [('id', '=', False)]
        domain = []
        for p in prefixes[:-1]:
            domain.append('|')
        for p in prefixes:
            domain.append(('account_id.code', '=like', '%s%%' % p))
        return domain

    def _compute_line_amount(self, line, cache):
        if line.id in cache:
            return cache[line.id]
        if line.is_total:
            amount = sum(self._compute_line_amount(c, cache) for c in line.component_line_ids)
        else:
            domain = [
                ('company_id', '=', self.company_id.id), ('parent_state', '=', 'posted'),
            ] + self._prefix_domain(line.code_prefixes)
            if line.balance_mode == 'as_of':
                domain.append(('date', '<=', self.date_to))
            else:
                domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
            grouped = self.env['account.move.line']._read_group(domain, aggregates=['balance:sum'])
            balance = grouped[0][0] if grouped else 0.0
            amount = (balance or 0.0) * (line.sign or 1)
        cache[line.id] = amount
        return amount

    def action_generate(self):
        self.ensure_one()
        self.result_line_ids.unlink()
        templates = self.env['l10n_pe_accounting.financial.report.line'].search(
            [('report_type', '=', self.report_type)])
        cache = {}
        vals = []
        for tmpl in templates:
            amount = self._compute_line_amount(tmpl, cache)
            vals.append((0, 0, {
                'sequence': tmpl.sequence, 'name': tmpl.name, 'level': tmpl.level,
                'bold': tmpl.bold or tmpl.is_total, 'amount': amount, 'currency_id': self.currency_id.id,
            }))
        self.result_line_ids = vals
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new',
        }
