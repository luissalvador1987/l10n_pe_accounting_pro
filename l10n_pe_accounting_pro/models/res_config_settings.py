# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pe_tax_regime = fields.Selection(related='company_id.l10n_pe_tax_regime', readonly=False)
    l10n_pe_income_tax_rate = fields.Float(related='company_id.l10n_pe_income_tax_rate', readonly=False)
    l10n_pe_detraction_bank_account_id = fields.Many2one(
        related='company_id.l10n_pe_detraction_bank_account_id', readonly=False)

    l10n_pe_is_retention_agent = fields.Boolean(related='company_id.l10n_pe_is_retention_agent', readonly=False)
    l10n_pe_retention_rate = fields.Float(related='company_id.l10n_pe_retention_rate', readonly=False)
    l10n_pe_retention_min_amount = fields.Monetary(
        related='company_id.l10n_pe_retention_min_amount', readonly=False)
    l10n_pe_retention_payable_account_id = fields.Many2one(
        related='company_id.l10n_pe_retention_payable_account_id', readonly=False)
    l10n_pe_retention_receivable_account_id = fields.Many2one(
        related='company_id.l10n_pe_retention_receivable_account_id', readonly=False)

    l10n_pe_is_perception_agent = fields.Boolean(related='company_id.l10n_pe_is_perception_agent', readonly=False)
    l10n_pe_perception_rate = fields.Float(related='company_id.l10n_pe_perception_rate', readonly=False)
    l10n_pe_perception_payable_account_id = fields.Many2one(
        related='company_id.l10n_pe_perception_payable_account_id', readonly=False)
    l10n_pe_perception_receivable_account_id = fields.Many2one(
        related='company_id.l10n_pe_perception_receivable_account_id', readonly=False)

    l10n_pe_sire_since_period = fields.Char(related='company_id.l10n_pe_sire_since_period', readonly=False)
