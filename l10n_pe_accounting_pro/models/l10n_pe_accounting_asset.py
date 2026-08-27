# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nPeAccountingAssetLine(models.Model):
    _name = 'l10n_pe_accounting.asset.line'
    _description = 'Línea de Depreciación Contable (NIIF)'
    _order = 'line_date'

    asset_id = fields.Many2one('l10n_pe_accounting.asset', string="Activo", required=True,
                                ondelete='cascade')
    line_date = fields.Date(string="Fecha", required=True)
    amount = fields.Monetary(string="Depreciación del ejercicio", currency_field='currency_id')
    accumulated = fields.Monetary(string="Depreciación acumulada", currency_field='currency_id')
    currency_id = fields.Many2one(related='asset_id.currency_id')
    move_id = fields.Many2one('account.move', string="Asiento contable", copy=False)
    state = fields.Selection([('draft', 'Pendiente'), ('posted', 'Contabilizada')], default='draft')

    def action_post(self):
        for line in self:
            line.asset_id.action_post_book_line(line.id)
        return True


class L10nPeAccountingAssetTaxLine(models.Model):
    _name = 'l10n_pe_accounting.asset.tax.line'
    _description = 'Línea de Depreciación Tributaria (SUNAT)'
    _order = 'year'

    asset_id = fields.Many2one('l10n_pe_accounting.asset', string="Activo", required=True,
                                ondelete='cascade')
    year = fields.Integer(string="Ejercicio", required=True)
    months = fields.Integer(string="Meses computados")
    amount = fields.Monetary(string="Depreciación tributaria del año", currency_field='currency_id')
    accumulated = fields.Monetary(string="Depreciación tributaria acumulada", currency_field='currency_id')
    currency_id = fields.Many2one(related='asset_id.currency_id')


class L10nPeAccountingAsset(models.Model):
    _name = 'l10n_pe_accounting.asset'
    _description = 'Activo Fijo (depreciación dual NIIF / SUNAT)'
    _inherit = ['mail.thread']
    _order = 'date_start desc, id desc'

    name = fields.Char(string="Nombre del activo", required=True)
    code = fields.Char(string="Código / referencia")
    company_id = fields.Many2one('res.company', string="Empresa", default=lambda self: self.env.company,
                                  required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    partner_id = fields.Many2one('res.partner', string="Proveedor")
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('running', 'En depreciación'),
        ('closed', 'Totalmente depreciado'),
        ('removed', 'Dado de baja'),
    ], string="Estado", default='draft', required=True, tracking=True)

    account_asset_id = fields.Many2one('account.account', string="Cuenta del activo", required=True)
    account_depreciation_id = fields.Many2one(
        'account.account', string="Cuenta de depreciación acumulada", required=True)
    account_expense_id = fields.Many2one(
        'account.account', string="Cuenta de gasto por depreciación", required=True)
    journal_id = fields.Many2one(
        'account.journal', string="Diario", required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]")

    purchase_value = fields.Monetary(string="Valor de adquisición", required=True, currency_field='currency_id')
    salvage_value = fields.Monetary(string="Valor residual", currency_field='currency_id')
    date_start = fields.Date(string="Fecha de inicio de depreciación", required=True,
                              default=fields.Date.context_today)
    useful_life_years = fields.Integer(string="Vida útil contable (años, NIIF)", default=5, required=True)

    book_line_ids = fields.One2many('l10n_pe_accounting.asset.line', 'asset_id',
                                     string="Cronograma contable (NIIF)")
    book_depreciated_value = fields.Monetary(
        string="Depreciación contable acumulada", compute='_compute_book_amounts', store=True,
        currency_field='currency_id')
    value_residual = fields.Monetary(string="Valor neto en libros", compute='_compute_book_amounts',
                                      store=True, currency_field='currency_id')

    l10n_pe_tax_category_id = fields.Many2one(
        'l10n_pe_accounting.asset.tax.category', string="Categoría tributaria SUNAT")
    l10n_pe_tax_annual_rate = fields.Float(
        string="Tasa tributaria anual (%)", compute='_compute_l10n_pe_tax_annual_rate',
        store=True, readonly=False)
    l10n_pe_tax_rate_exceeds_max = fields.Boolean(compute='_compute_l10n_pe_tax_rate_exceeds_max')
    l10n_pe_tax_line_ids = fields.One2many(
        'l10n_pe_accounting.asset.tax.line', 'asset_id', string="Cronograma tributario (SUNAT)")
    l10n_pe_tax_depreciated_value = fields.Monetary(
        string="Depreciación tributaria acumulada", compute='_compute_l10n_pe_tax_amounts', store=True,
        currency_field='currency_id')
    l10n_pe_temporary_difference = fields.Monetary(
        string="Diferencia temporal (contable - tributaria)", compute='_compute_l10n_pe_tax_amounts',
        store=True, currency_field='currency_id',
        help="Positiva: la depreciación contable (NIIF) va por delante de la tributaria (SUNAT) -> "
             "pasivo por impuesto diferido. Negativa: al revés -> activo por impuesto diferido.")
    l10n_pe_deferred_tax = fields.Monetary(
        string="Impuesto a la renta diferido", compute='_compute_l10n_pe_tax_amounts', store=True,
        currency_field='currency_id')

    @api.depends('book_line_ids.amount', 'book_line_ids.state', 'purchase_value', 'salvage_value')
    def _compute_book_amounts(self):
        for asset in self:
            depreciated = sum(asset.book_line_ids.filtered(lambda l: l.state == 'posted').mapped('amount'))
            asset.book_depreciated_value = depreciated
            asset.value_residual = asset.purchase_value - depreciated

    @api.depends('l10n_pe_tax_category_id')
    def _compute_l10n_pe_tax_annual_rate(self):
        for asset in self:
            if asset.l10n_pe_tax_category_id:
                asset.l10n_pe_tax_annual_rate = asset.l10n_pe_tax_category_id.max_annual_rate
            elif not asset.l10n_pe_tax_annual_rate:
                asset.l10n_pe_tax_annual_rate = 0.0

    @api.depends('l10n_pe_tax_annual_rate', 'l10n_pe_tax_category_id.max_annual_rate')
    def _compute_l10n_pe_tax_rate_exceeds_max(self):
        for asset in self:
            asset.l10n_pe_tax_rate_exceeds_max = bool(
                asset.l10n_pe_tax_category_id
                and asset.l10n_pe_tax_annual_rate > asset.l10n_pe_tax_category_id.max_annual_rate)

    @api.depends('l10n_pe_tax_line_ids.amount', 'book_depreciated_value', 'company_id.l10n_pe_income_tax_rate')
    def _compute_l10n_pe_tax_amounts(self):
        for asset in self:
            tax_depreciated = sum(asset.l10n_pe_tax_line_ids.mapped('amount'))
            asset.l10n_pe_tax_depreciated_value = tax_depreciated
            diff = asset.book_depreciated_value - tax_depreciated
            asset.l10n_pe_temporary_difference = diff
            asset.l10n_pe_deferred_tax = diff * (asset.company_id.l10n_pe_income_tax_rate or 0.0) / 100.0

    # ------------------------------------------------------------------
    # Cronograma contable (NIIF): línea recta anual, prorrateando el primer
    # ejercicio por meses de uso — igual criterio que el cronograma tributario,
    # así ambos son directamente comparables.
    # ------------------------------------------------------------------
    def action_compute_book_depreciation_board(self):
        for asset in self:
            if asset.book_line_ids.filtered(lambda l: l.state == 'posted'):
                raise UserError(_(
                    "No se puede recalcular el cronograma contable: ya hay líneas contabilizadas."))
            asset.book_line_ids.unlink()
            base = asset.purchase_value - asset.salvage_value
            if base <= 0 or not asset.useful_life_years or not asset.date_start:
                continue
            annual_amount = asset.currency_id.round(base / asset.useful_life_years)
            year = asset.date_start.year
            months_left_first_year = 12 - asset.date_start.month + 1
            remaining = base
            accumulated = 0.0
            months = months_left_first_year
            first = True
            lines = []
            while remaining > 0.01 and len(lines) < 60:
                amount = asset.currency_id.round(annual_amount * months / 12.0) if first else annual_amount
                if amount > remaining:
                    amount = remaining
                accumulated += amount
                remaining -= amount
                line_date = fields.Date.from_string('%s-12-31' % year)
                lines.append((0, 0, {
                    'line_date': line_date, 'amount': amount, 'accumulated': accumulated,
                }))
                year += 1
                months = 12
                first = False
            asset.book_line_ids = lines
            if asset.state == 'draft':
                asset.state = 'running'
        return True

    def action_post_book_line(self, line_id):
        line = self.env['l10n_pe_accounting.asset.line'].browse(line_id)
        line.ensure_one()
        asset = line.asset_id
        if line.state == 'posted':
            return True
        move = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': asset.journal_id.id, 'date': line.line_date,
            'ref': _("Depreciación %s") % asset.name,
            'line_ids': [
                (0, 0, {'name': asset.name, 'account_id': asset.account_expense_id.id,
                        'debit': line.amount, 'credit': 0.0}),
                (0, 0, {'name': asset.name, 'account_id': asset.account_depreciation_id.id,
                        'debit': 0.0, 'credit': line.amount}),
            ],
        })
        move.action_post()
        line.write({'move_id': move.id, 'state': 'posted'})
        if asset.currency_id.is_zero(asset.value_residual):
            asset.state = 'closed'
        return True

    # ------------------------------------------------------------------
    # Cronograma tributario (SUNAT)
    # ------------------------------------------------------------------
    def l10n_pe_compute_tax_depreciation_board(self):
        for asset in self:
            asset.l10n_pe_tax_line_ids.unlink()
            rate = asset.l10n_pe_tax_annual_rate
            if not rate or not asset.date_start:
                continue
            annual_amount = asset.currency_id.round(asset.purchase_value * rate / 100.0)
            if asset.currency_id.is_zero(annual_amount):
                continue
            year = asset.date_start.year
            months_left_first_year = 12 - asset.date_start.month + 1
            accumulated = 0.0
            remaining = asset.purchase_value
            months = months_left_first_year
            first = True
            lines = []
            while remaining > 0.01 and len(lines) < 60:
                amount = asset.currency_id.round(annual_amount * months / 12.0) if first else annual_amount
                if amount > remaining:
                    amount = remaining
                accumulated += amount
                remaining -= amount
                lines.append((0, 0, {
                    'year': year, 'months': months if first else 12, 'amount': amount,
                    'accumulated': accumulated,
                }))
                year += 1
                months = 12
                first = False
            asset.l10n_pe_tax_line_ids = lines
        return True

    def action_remove(self):
        for asset in self:
            if asset.state == 'removed':
                continue
            asset.state = 'removed'
