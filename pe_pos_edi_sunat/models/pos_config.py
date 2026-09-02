# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_pe_edi_country_code = fields.Char(
        related='company_id.account_fiscal_country_id.code', string="País fiscal (código)")

    l10n_pe_edi_boleta_journal_id = fields.Many2one(
        'account.journal', string="Diario SUNAT para Boleta",
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
        help="Diario de ventas cuya 'Serie SUNAT' (pestaña Facturación Electrónica SUNAT) sea la "
             "serie de Boleta autorizada (ej. B001) para este Punto de Venta. Se usa cuando el "
             "cliente de la venta no tiene RUC (o no se identificó ningún cliente).")
    l10n_pe_edi_factura_journal_id = fields.Many2one(
        'account.journal', string="Diario SUNAT para Factura",
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
        help="Diario de ventas cuya 'Serie SUNAT' sea la serie de Factura autorizada (ej. F001) "
             "para este Punto de Venta. Se usa cuando el cliente de la venta tiene RUC.")
    l10n_pe_edi_default_partner_id = fields.Many2one(
        'res.partner', string="Cliente genérico para Boleta",
        help="Se asigna automáticamente a la venta cuando el cajero no selecciona ningún cliente, "
             "para poder emitir igual la Boleta Electrónica que SUNAT exige para toda venta al "
             "público (ej. un contacto 'Clientes Varios' / 'Público General').")
    l10n_pe_edi_auto_send = fields.Boolean(
        string="Enviar a SUNAT automáticamente al cobrar", default=True,
        help="Si está activo, apenas se cobra el ticket se firma y envía el comprobante a SUNAT en "
             "el mismo momento (igual que el botón 'Enviar' de Contabilidad). Si se desactiva, los "
             "comprobantes quedan en estado 'Por enviar' para enviarlos en lote más tarde desde "
             "Contabilidad > Facturación Electrónica SUNAT.")

    @api.constrains('l10n_pe_edi_boleta_journal_id', 'l10n_pe_edi_factura_journal_id')
    def _check_l10n_pe_edi_journals_have_series(self):
        for config in self:
            for journal in (config.l10n_pe_edi_boleta_journal_id, config.l10n_pe_edi_factura_journal_id):
                if journal and not journal.l10n_pe_edi_series:
                    raise ValidationError(self.env._(
                        "El diario '%s' todavía no tiene una 'Serie SUNAT' configurada (pestaña "
                        "Facturación Electrónica SUNAT del diario). Configúrala antes de usarlo "
                        "desde el Punto de Venta.") % journal.display_name)
