# -*- coding: utf-8 -*-
import base64
import logging

from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools import cdr_parser, qr_helper, sunat_soap_client, ubl_invoice_builder, xml_signer, zip_helper
from ..tools.sunat_soap_client import SunatSoapError

_logger = logging.getLogger(__name__)

PE_DOC_CODES = ('01', '03', '07', '08')  # Factura, Boleta, Nota de Crédito, Nota de Débito


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pe_edi_is_required = fields.Boolean(compute='_compute_l10n_pe_edi_is_required')
    l10n_pe_edi_state = fields.Selection([
        ('to_send', 'Por enviar'),
        ('sent', 'Enviado'),
        ('accepted', 'Aceptado por SUNAT'),
        ('rejected', 'Rechazado por SUNAT'),
        ('error', 'Error'),
    ], string="Estado SUNAT", copy=False, tracking=True)
    l10n_pe_edi_issue_time = fields.Char(copy=False, help="Hora de emisión (HH:MM:SS) usada en el XML.")

    l10n_pe_edi_xml_file = fields.Binary(string="XML firmado", copy=False, attachment=True)
    l10n_pe_edi_xml_filename = fields.Char(copy=False)
    l10n_pe_edi_cdr_file = fields.Binary(string="CDR", copy=False, attachment=True)
    l10n_pe_edi_cdr_filename = fields.Char(copy=False)
    l10n_pe_edi_cdr_code = fields.Char(string="Código CDR", copy=False)
    l10n_pe_edi_cdr_description = fields.Text(string="Descripción CDR", copy=False)
    l10n_pe_edi_error_message = fields.Text(copy=False)
    l10n_pe_edi_hash = fields.Char(string="Hash (DigestValue)", copy=False)
    l10n_pe_edi_qr_data = fields.Char(copy=False)
    l10n_pe_edi_qr_image = fields.Binary(copy=False, attachment=True)

    l10n_pe_edi_note_reason_code = fields.Char(
        string="Código de motivo",
        help="Nota de Crédito (Catálogo 09): 01 Anulación de la operación, 02 Anulación por error en el "
             "RUC, 03 Corrección por error en la descripción, 04 Descuento global, 05 Descuento por ítem, "
             "06 Devolución total, 07 Devolución por ítem, 08 Bonificación, 09 Disminución en el valor, "
             "10 Otros, 11/12 Ajustes de exportación/IVAP.\n"
             "Nota de Débito (Catálogo 10): 01 Intereses por mora, 02 Aumento en el valor, 03 Penalidades, "
             "11/12 Ajustes de exportación/IVAP.")
    l10n_pe_edi_note_reason_text = fields.Char(string="Sustento / Motivo")

    @api.depends('company_id.account_fiscal_country_id', 'journal_id.l10n_latam_use_documents',
                 'l10n_latam_document_type_id.code', 'move_type')
    def _compute_l10n_pe_edi_is_required(self):
        for move in self:
            move.l10n_pe_edi_is_required = bool(
                move.company_id.account_fiscal_country_id.code == 'PE'
                and move.journal_id.l10n_latam_use_documents
                and move.journal_id.type == 'sale'
                and move.l10n_latam_document_type_id.code in PE_DOC_CODES
            )

    def _get_starting_sequence(self):
        # Make Odoo's own sequence produce SUNAT's "SERIE-00000001" shape
        # directly, by using the journal's registered 4-character series as
        # the sequence prefix instead of the bare document-type letter.
        if (self.journal_id.l10n_latam_use_documents and self.l10n_latam_document_type_id
                and self.company_id.account_fiscal_country_id.code == 'PE'
                and self.journal_id.l10n_pe_edi_series):
            return "%s-00000000" % self.journal_id.l10n_pe_edi_series
        return super()._get_starting_sequence()

    def l10n_pe_edi_series_number(self):
        """Returns (serie, correlativo) split from l10n_latam_document_number,
        e.g. 'F001-00000032' -> ('F001', '00000032')."""
        self.ensure_one()
        number = self.l10n_latam_document_number or ''
        if '-' not in number:
            raise UserError(self.env._(
                "El comprobante '%s' no tiene un número con formato SERIE-CORRELATIVO. Configura la "
                "serie SUNAT en el diario y valida (publica) el comprobante primero.") % (self.name or self.id))
        serie, correlativo = number.split('-', 1)
        return serie, correlativo.zfill(8)

    # ------------------------------------------------------------------
    # XML generation + signature
    # ------------------------------------------------------------------
    def action_l10n_pe_edi_generate_xml(self):
        for move in self:
            move._l10n_pe_edi_generate_and_sign()
        return True

    def _l10n_pe_edi_generate_and_sign(self):
        self.ensure_one()
        if not self.l10n_pe_edi_is_required:
            raise UserError(self.env._("Este comprobante no requiere Facturación Electrónica SUNAT."))
        if self.state != 'posted':
            raise UserError(self.env._("Valida (publica) el comprobante antes de generar el XML."))
        certificate = self.company_id.l10n_pe_edi_certificate_id
        if not certificate:
            raise UserError(self.env._(
                "Configura y valida un certificado digital en Contabilidad > Configuración > "
                "Facturación Electrónica SUNAT."))

        if not self.l10n_pe_edi_issue_time:
            self.l10n_pe_edi_issue_time = fields.Datetime.context_timestamp(
                self, fields.Datetime.now()).strftime('%H:%M:%S')

        try:
            xml_root = ubl_invoice_builder.build_xml_for_move(self)
            private_key, x509_cert = certificate.get_private_key_and_certificate()
            xml_signer.sign_ubl_document(xml_root, private_key, x509_cert)
            signed_bytes = etree.tostring(xml_root, xml_declaration=True, encoding='UTF-8', standalone=False)
        except UserError:
            raise
        except Exception as e:  # noqa: BLE001
            _logger.exception("Error generando/firmando el XML SUNAT")
            self.write({'l10n_pe_edi_state': 'error', 'l10n_pe_edi_error_message': str(e)})
            raise UserError(self.env._("No se pudo generar/firmar el XML: %s") % e)

        serie, correlativo = self.l10n_pe_edi_series_number()
        ruc = self.company_id.l10n_pe_edi_get_ruc()
        doc_code = self.l10n_latam_document_type_id.code
        file_name = zip_helper.sunat_file_name(ruc, doc_code, serie, correlativo)

        digest_value = xml_signer.get_signature_digest(xml_root)
        qr_data = qr_helper.build_qr_data(
            ruc, doc_code, serie, correlativo, self.amount_tax, self.amount_total, self.invoice_date,
            self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            (self.partner_id.vat or '').replace('PE', ''), digest_value)

        self.write({
            'l10n_pe_edi_state': 'to_send',
            'l10n_pe_edi_xml_file': base64.b64encode(signed_bytes),
            'l10n_pe_edi_xml_filename': file_name,
            'l10n_pe_edi_hash': digest_value,
            'l10n_pe_edi_qr_data': qr_data,
            'l10n_pe_edi_qr_image': qr_helper.build_qr_png_base64(qr_data),
            'l10n_pe_edi_error_message': False,
        })
        self.env['pe.edi.log'].create_log(self, 'generate', True, 'XML generado y firmado: %s' % file_name)
        return True

    # ------------------------------------------------------------------
    # Sending to SUNAT
    # ------------------------------------------------------------------
    def action_l10n_pe_edi_generate_and_send(self):
        for move in self:
            if move.l10n_pe_edi_state not in ('to_send', 'error', 'rejected'):
                move._l10n_pe_edi_generate_and_sign()
            elif not move.l10n_pe_edi_xml_file:
                move._l10n_pe_edi_generate_and_sign()
            move._l10n_pe_edi_send()
        return True

    def action_l10n_pe_edi_send(self):
        for move in self:
            move._l10n_pe_edi_send()
        return True

    def _l10n_pe_edi_send(self):
        self.ensure_one()
        if not self.l10n_pe_edi_xml_file:
            raise UserError(self.env._("Genera y firma el XML antes de enviarlo."))
        company = self.company_id
        if not company.l10n_pe_edi_sol_user or not company.l10n_pe_edi_sol_password:
            raise UserError(self.env._(
                "Configura el usuario y clave SOL en Contabilidad > Configuración > Facturación "
                "Electrónica SUNAT."))

        xml_bytes = base64.b64decode(self.l10n_pe_edi_xml_file)
        inner_name = self.l10n_pe_edi_xml_filename
        zip_bytes = zip_helper.zip_single_file(inner_name, xml_bytes)
        endpoint = company.l10n_pe_edi_get_bill_service_url()
        ruc = company.l10n_pe_edi_get_ruc()

        try:
            cdr_zip = sunat_soap_client.send_bill(
                endpoint, ruc, company.l10n_pe_edi_sol_user, company.l10n_pe_edi_sol_password,
                inner_name.replace('.xml', '.zip'), zip_bytes)
        except SunatSoapError as e:
            self.write({'l10n_pe_edi_state': 'error', 'l10n_pe_edi_error_message': e.fault_string})
            self.env['pe.edi.log'].create_log(self, 'send', False, '%s: %s' % (e.fault_code, e.fault_string))
            raise UserError(self.env._("SUNAT rechazó el envío: %s") % e.fault_string)
        except Exception as e:  # noqa: BLE001
            _logger.exception("Error de comunicación con SUNAT")
            self.write({'l10n_pe_edi_state': 'error', 'l10n_pe_edi_error_message': str(e)})
            self.env['pe.edi.log'].create_log(self, 'send', False, str(e))
            raise UserError(self.env._("No se pudo conectar con SUNAT: %s") % e)

        cdr = cdr_parser.parse_cdr_zip(cdr_zip)
        cdr_filename = inner_name.replace('.xml', '-CDR.zip')
        state = 'accepted' if cdr['accepted'] else 'rejected'
        self.write({
            'l10n_pe_edi_state': state,
            'l10n_pe_edi_cdr_file': base64.b64encode(cdr_zip),
            'l10n_pe_edi_cdr_filename': cdr_filename,
            'l10n_pe_edi_cdr_code': cdr['code'],
            'l10n_pe_edi_cdr_description': cdr['description'],
            'l10n_pe_edi_error_message': False if cdr['accepted'] else cdr['description'],
        })
        self.env['pe.edi.log'].create_log(
            self, 'send', cdr['accepted'], 'CDR %s: %s' % (cdr['code'], cdr['description']))
        if not cdr['accepted']:
            raise UserError(self.env._("SUNAT rechazó el comprobante (%s): %s") % (cdr['code'], cdr['description']))
        return True

    def action_l10n_pe_edi_download_xml(self):
        return self._l10n_pe_edi_download('l10n_pe_edi_xml_file', 'l10n_pe_edi_xml_filename')

    def action_l10n_pe_edi_download_cdr(self):
        return self._l10n_pe_edi_download('l10n_pe_edi_cdr_file', 'l10n_pe_edi_cdr_filename')

    def _l10n_pe_edi_download(self, field_name, filename_field):
        self.ensure_one()
        if not self[field_name]:
            raise UserError(self.env._("No hay archivo disponible todavía."))
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'), ('res_id', '=', self.id), ('res_field', '=', field_name),
        ], limit=1)
        if not attachment:
            raise UserError(self.env._("No se encontró el archivo adjunto."))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
