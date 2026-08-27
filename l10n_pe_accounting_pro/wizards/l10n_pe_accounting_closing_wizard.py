# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nPeAccountingClosingWizard(models.TransientModel):
    _name = 'l10n_pe_accounting.closing.wizard'
    _description = 'Asistente de Cierre Contable'

    company_id = fields.Many2one('res.company', string="Empresa", default=lambda self: self.env.company,
                                  required=True)
    period = fields.Char(string="Periodo (AAAAMM)", required=True)
    date = fields.Date(string="Fecha del asiento", required=True, default=fields.Date.context_today)

    cts_base_amount = fields.Monetary(string="Base remunerativa (CTS)", currency_field='currency_id')
    cts_expense_account_id = fields.Many2one('account.account', string="Cuenta de gasto (CTS)")
    cts_payable_account_id = fields.Many2one('account.account', string="CTS por pagar")

    gratification_base_amount = fields.Monetary(string="Base remunerativa (Gratificación)",
                                                  currency_field='currency_id')
    gratification_expense_account_id = fields.Many2one('account.account', string="Cuenta de gasto (Gratif.)")
    gratification_payable_account_id = fields.Many2one('account.account', string="Gratificación por pagar")

    vacation_base_amount = fields.Monetary(string="Base remunerativa (Vacaciones)", currency_field='currency_id')
    vacation_expense_account_id = fields.Many2one('account.account', string="Cuenta de gasto (Vacaciones)")
    vacation_payable_account_id = fields.Many2one('account.account', string="Vacaciones por pagar")

    currency_id = fields.Many2one(related='company_id.currency_id')

    def _get_log(self):
        self.ensure_one()
        log = self.env['l10n_pe_accounting.closing.log'].search([
            ('company_id', '=', self.company_id.id), ('period', '=', self.period)], limit=1)
        if not log:
            log = self.env['l10n_pe_accounting.closing.log'].create({
                'company_id': self.company_id.id, 'period': self.period,
            })
        return log

    def _create_provision_move(self, label, base_amount, fraction, expense_account, payable_account):
        self.ensure_one()
        if not expense_account or not payable_account:
            raise UserError(_("Configura la cuenta de gasto y la cuenta por pagar para %s.") % label)
        amount = self.currency_id.round(base_amount * fraction)
        if self.currency_id.is_zero(amount):
            raise UserError(_("El monto a provisionar para %s es cero.") % label)
        journal = self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.company_id.id)], limit=1)
        move = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': journal.id, 'date': self.date,
            'ref': _("Provisión %s - %s") % (label, self.period),
            'line_ids': [
                (0, 0, {'name': label, 'account_id': expense_account.id, 'debit': amount, 'credit': 0.0}),
                (0, 0, {'name': label, 'account_id': payable_account.id, 'debit': 0.0, 'credit': amount}),
            ],
        })
        move.action_post()
        return move

    def action_provision_cts(self):
        move = self._create_provision_move(
            _("Provisión CTS"), self.cts_base_amount, 1.0 / 12,
            self.cts_expense_account_id, self.cts_payable_account_id)
        self._get_log().write({'cts_move_id': move.id})
        return {'type': 'ir.actions.act_window_close'}

    def action_provision_gratification(self):
        move = self._create_provision_move(
            _("Provisión Gratificación"), self.gratification_base_amount, 1.0 / 6,
            self.gratification_expense_account_id, self.gratification_payable_account_id)
        self._get_log().write({'gratification_move_id': move.id})
        return {'type': 'ir.actions.act_window_close'}

    def action_provision_vacation(self):
        move = self._create_provision_move(
            _("Provisión Vacaciones"), self.vacation_base_amount, 1.0 / 12,
            self.vacation_expense_account_id, self.vacation_payable_account_id)
        self._get_log().write({'vacation_move_id': move.id})
        return {'type': 'ir.actions.act_window_close'}

    def action_adjust_exchange_difference(self):
        """Ajusta al tipo de cambio de cierre las cuentas por cobrar/pagar en moneda extranjera que
        siguen abiertas (no conciliadas), reconociendo la diferencia de cambio no realizada."""
        self.ensure_one()
        company = self.company_id
        gain_account = company.income_currency_exchange_account_id
        loss_account = company.expense_currency_exchange_account_id
        if not gain_account or not loss_account:
            raise UserError(_(
                "Configura las cuentas de ganancia/pérdida por diferencia de cambio en "
                "Contabilidad > Configuración > Ajustes (Cuentas de diferencia de cambio)."))

        open_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id), ('reconciled', '=', False),
            ('currency_id', '!=', False), ('currency_id', '!=', company.currency_id.id),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('parent_state', '=', 'posted'),
        ])
        adjustments = {}
        for line in open_lines:
            if not line.amount_residual_currency:
                continue
            revalued = line.currency_id._convert(
                line.amount_residual_currency, company.currency_id, company, self.date)
            diff = revalued - line.amount_residual
            if company.currency_id.is_zero(diff):
                continue
            key = (line.account_id.id, line.partner_id.id)
            adjustments.setdefault(key, {'account_id': line.account_id, 'partner_id': line.partner_id,
                                          'diff': 0.0})
            adjustments[key]['diff'] += diff

        if not adjustments:
            raise UserError(_("No se encontraron cuentas por cobrar/pagar en moneda extranjera "
                               "pendientes a esa fecha."))

        move_lines = []
        total = 0.0
        for adj in adjustments.values():
            if company.currency_id.is_zero(adj['diff']):
                continue
            move_lines.append((0, 0, {
                'name': _("Ajuste diferencia de cambio - cierre %s") % self.period,
                'account_id': adj['account_id'].id, 'partner_id': adj['partner_id'].id or False,
                'debit': adj['diff'] if adj['diff'] > 0 else 0.0,
                'credit': -adj['diff'] if adj['diff'] < 0 else 0.0,
            }))
            total += adj['diff']

        contra_account = gain_account if total < 0 else loss_account
        move_lines.append((0, 0, {
            'name': _("Diferencia de cambio - cierre %s") % self.period,
            'account_id': contra_account.id,
            'debit': -total if total < 0 else 0.0, 'credit': total if total > 0 else 0.0,
        }))
        journal = self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', company.id)], limit=1)
        move = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': journal.id, 'date': self.date,
            'ref': _("Ajuste por diferencia de cambio - %s") % self.period, 'line_ids': move_lines,
        })
        move.action_post()
        self._get_log().write({'exchange_diff_move_id': move.id})
        return {'type': 'ir.actions.act_window_close'}
