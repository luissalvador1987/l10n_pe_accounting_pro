# -*- coding: utf-8 -*-
from odoo import fields, models

from ..tools.sunat_soap_client import get_endpoint


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_edi_trade_name = fields.Char(string="Nombre comercial")
    l10n_pe_edi_environment = fields.Selection([
        ('beta', 'Beta / Homologación'),
        ('production', 'Producción'),
    ], string="Ambiente SUNAT", default='beta', required=True)
    l10n_pe_edi_certificate_id = fields.Many2one('pe.edi.certificate', string="Certificado digital activo",
                                                  domain="[('company_id', '=', id)]")

    # SOL credentials (billService: Factura/Boleta/Notas)
    l10n_pe_edi_sol_user = fields.Char(
        string="Usuario SOL", help="Usuario secundario SOL, sin el RUC (ej: MODDATOS).")
    l10n_pe_edi_sol_password = fields.Char(string="Clave SOL")

    # GRE OAuth2 credentials (Guía de Remisión Electrónica)
    l10n_pe_edi_gre_client_id = fields.Char(string="Client ID (GRE)")
    l10n_pe_edi_gre_client_secret = fields.Char(string="Client Secret (GRE)")
    l10n_pe_edi_gre_submission_url = fields.Char(
        string="URL de envío GRE",
        default="https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/guiaremision",
        help="SUNAT ha cambiado esta ruta más de una vez; confirma la vigente en el Manual del "
             "Programador de Guía de Remisión Electrónica antes de emitir en Producción.")

    def l10n_pe_edi_get_bill_service_url(self):
        self.ensure_one()
        return get_endpoint(self.l10n_pe_edi_environment)

    def l10n_pe_edi_get_ruc(self):
        self.ensure_one()
        return (self.vat or '').replace('PE', '').strip()
