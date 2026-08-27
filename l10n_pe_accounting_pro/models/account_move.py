# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

DETRACTION_MOVE_TYPES = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
PERCEPTION_ISSUE_TYPES = ('out_invoice', 'out_refund')


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pe_detraction_ids = fields.One2many(
        'l10n_pe_accounting.detraction', 'move_id', string="Detracciones (SPOT)")
    l10n_pe_is_subject_to_detraction = fields.Boolean(
        compute='_compute_l10n_pe_is_subject_to_detraction', store=True)
    l10n_pe_perception_ids = fields.One2many(
        'l10n_pe_accounting.perception', 'invoice_id', string="Percepciones")
    l10n_pe_retention_count = fields.Integer(compute='_compute_l10n_pe_retention_count')

    @api.depends('invoice_line_ids.product_id.product_tmpl_id.l10n_pe_detraction_category_id')
    def _compute_l10n_pe_is_subject_to_detraction(self):
        for move in self:
            move.l10n_pe_is_subject_to_detraction = bool(move.invoice_line_ids.mapped(
                'product_id.product_tmpl_id.l10n_pe_detraction_category_id'))

    def _compute_l10n_pe_retention_count(self):
        Retention = self.env['l10n_pe_accounting.retention']
        for move in self:
            move.l10n_pe_retention_count = Retention.search_count(
                [('invoice_ids', 'in', move.id)]) if move.id else 0

    def action_l10n_pe_view_retentions(self):
        self.ensure_one()
        retentions = self.env['l10n_pe_accounting.retention'].search([('invoice_ids', 'in', self.id)])
        return {
            'type': 'ir.actions.act_window', 'name': _("Retenciones"),
            'res_model': 'l10n_pe_accounting.retention', 'view_mode': 'list,form',
            'domain': [('id', 'in', retentions.ids)],
        }

    # ------------------------------------------------------------------
    # Percepción de IGV: se agrega como línea del propio comprobante,
    # así que tiene que aplicarse ANTES de contabilizar (mientras es borrador).
    # ------------------------------------------------------------------
    def _l10n_pe_accounting_is_perception_applicable(self):
        self.ensure_one()
        company = self.company_id
        return bool(
            self.move_type in PERCEPTION_ISSUE_TYPES
            and company.l10n_pe_is_perception_agent
            and company.l10n_pe_perception_payable_account_id
            and self.partner_id
            and not self.partner_id.l10n_pe_perception_excluded
            and not any(
                line.account_id == company.l10n_pe_perception_payable_account_id
                for line in self.invoice_line_ids)
        )

    def _l10n_pe_accounting_apply_perception(self):
        self.ensure_one()
        company = self.company_id
        base_amount = self.amount_total
        rate = company.l10n_pe_perception_rate
        perception_amount = self.currency_id.round(base_amount * rate / 100.0)
        if self.currency_id.is_zero(perception_amount):
            return
        self.write({
            'invoice_line_ids': [(0, 0, {
                'name': _("Percepción IGV Ventas Internas (%.2f%%)") % rate,
                'account_id': company.l10n_pe_perception_payable_account_id.id,
                'quantity': 1.0, 'price_unit': perception_amount, 'tax_ids': [(5, 0, 0)],
            })],
        })
        perception = self.env['l10n_pe_accounting.perception'].create({
            'direction': 'issued', 'partner_id': self.partner_id.id, 'invoice_id': self.id,
            'base_amount': base_amount, 'rate': rate, 'date': self.invoice_date or fields.Date.context_today(self),
            'company_id': company.id,
        })
        perception.action_post()

    def action_post(self):
        for move in self:
            if move.state == 'draft' and move._l10n_pe_accounting_is_perception_applicable():
                move._l10n_pe_accounting_apply_perception()
        res = super().action_post()
        for move in self:
            move._l10n_pe_accounting_create_detraction_if_needed()
            move._l10n_pe_accounting_create_ple_line()
        return res

    # ------------------------------------------------------------------
    # Registro de Compras / Ventas (PLE)
    # ------------------------------------------------------------------
    def _l10n_pe_accounting_exchange_rate(self):
        self.ensure_one()
        if self.currency_id == self.company_id.currency_id:
            return 1.0
        try:
            return self.currency_id._convert(
                1.0, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        except Exception:  # noqa: BLE001
            return 1.0

    def _l10n_pe_accounting_ple_base_split(self, exclude_account_ids):
        """Separa las líneas de un comprobante entre base gravada (con IGV) y no
        gravada/exonerada, e identifica el ISC si lo hubiera."""
        self.ensure_one()
        base_taxed = base_exempt = isc_amount = 0.0
        for line in self.invoice_line_ids.filtered(lambda l: l.account_id.id not in exclude_account_ids):
            tax_names = line.tax_ids.mapped('name') or []
            has_isc = any('ISC' in (n or '') for n in tax_names)
            has_igv = any(t.amount > 0 for t in line.tax_ids)
            if has_isc:
                isc_amount += line.price_subtotal
            elif has_igv:
                base_taxed += line.price_subtotal
            else:
                base_exempt += line.price_subtotal
        return base_taxed, base_exempt, isc_amount

    def _l10n_pe_accounting_create_ple_line(self):
        self.ensure_one()
        company = self.company_id
        is_purchase = self.move_type in ('in_invoice', 'in_refund')
        is_sale = self.move_type in ('out_invoice', 'out_refund')
        if not (is_purchase or is_sale):
            return
        model_name = 'l10n_pe_accounting.ple.purchase.line' if is_purchase else 'l10n_pe_accounting.ple.sale.line'
        if self.env[model_name].search_count([('move_id', '=', self.id)]):
            return

        exclude_accounts = company.l10n_pe_perception_payable_account_id.ids
        base_taxed, base_exempt, isc_amount = self._l10n_pe_accounting_ple_base_split(exclude_accounts)
        doc_type = self.l10n_latam_document_type_id.code or ('80' if is_purchase else '00')
        serie, numero = '', (self.name or '')
        if self.l10n_latam_document_number and '-' in self.l10n_latam_document_number:
            serie, numero = self.l10n_latam_document_number.split('-', 1)

        vals = {
            'move_id': self.id, 'period': (self.date or fields.Date.context_today(self)).strftime('%Y%m'),
            'cuo': str(self.id), 'emission_date': self.invoice_date or self.date,
            'doc_type_code': doc_type, 'series': serie, 'number': numero,
            'partner_vat_type_code': self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code or '',
            'partner_vat': (self.partner_id.vat or '').replace('PE', ''),
            'partner_name': self.partner_id.name or '',
            'base_taxed': base_taxed, 'base_exempt': base_exempt, 'isc_amount': isc_amount,
            'igv_amount': self.amount_tax, 'other_taxes_amount': 0.0, 'total_amount': self.amount_total,
            'currency_id': self.currency_id.id, 'currency_code': self.currency_id.name,
            'exchange_rate': self._l10n_pe_accounting_exchange_rate(),
        }
        if is_purchase:
            detraction = self.l10n_pe_detraction_ids[:1]
            vals.update({
                'is_subject_to_detraction': bool(detraction),
                'detraction_constancia': detraction.constancia_number if detraction else False,
            })
        self.env[model_name].create(vals)

    # ------------------------------------------------------------------
    # Detracción (SPOT): se registra DESPUÉS de contabilizar, como un
    # control aparte (no cambia el importe del comprobante).
    # ------------------------------------------------------------------
    def _l10n_pe_accounting_create_detraction_if_needed(self):
        self.ensure_one()
        if self.move_type not in DETRACTION_MOVE_TYPES or not self.l10n_pe_is_subject_to_detraction:
            return
        if self.l10n_pe_detraction_ids:
            return  # ya existe (p.ej. reapertura/recontabilización)
        categories = self.invoice_line_ids.mapped('product_id.product_tmpl_id.l10n_pe_detraction_category_id')
        if not categories:
            return
        category = categories.sorted('percentage', reverse=True)[0]
        base_amount = self.amount_total
        if category.anexo != '1' and base_amount < category.min_amount:
            return
        self.env['l10n_pe_accounting.detraction'].create({
            'move_id': self.id, 'category_id': category.id, 'percentage': category.percentage,
            'base_amount': base_amount,
        })
