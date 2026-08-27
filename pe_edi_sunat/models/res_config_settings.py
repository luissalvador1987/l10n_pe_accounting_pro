# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pe_edi_trade_name = fields.Char(related='company_id.l10n_pe_edi_trade_name', readonly=False)
    l10n_pe_edi_environment = fields.Selection(related='company_id.l10n_pe_edi_environment', readonly=False)
    l10n_pe_edi_certificate_id = fields.Many2one(related='company_id.l10n_pe_edi_certificate_id', readonly=False)
    l10n_pe_edi_sol_user = fields.Char(related='company_id.l10n_pe_edi_sol_user', readonly=False)
    l10n_pe_edi_sol_password = fields.Char(related='company_id.l10n_pe_edi_sol_password', readonly=False)
    l10n_pe_edi_gre_client_id = fields.Char(related='company_id.l10n_pe_edi_gre_client_id', readonly=False)
    l10n_pe_edi_gre_client_secret = fields.Char(related='company_id.l10n_pe_edi_gre_client_secret', readonly=False)
    l10n_pe_edi_gre_submission_url = fields.Char(
        related='company_id.l10n_pe_edi_gre_submission_url', readonly=False)
