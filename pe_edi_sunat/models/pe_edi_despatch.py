# -*- coding: utf-8 -*-
import base64
import logging

from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools import qr_helper, sunat_gre_client, ubl_despatch_builder, xml_signer, zip_helper

_logger = logging.getLogger(__name__)

MOTIVO_TRASLADO = [
    ('01', 'Venta'), ('02', 'Compra'), ('04', 'Traslado entre establecimientos de la misma empresa'),
    ('08', 'Importación'), ('09', 'Exportación'), ('13', 'Otros'),
    ('14', 'Venta sujeta a confirmación del comprador'), ('18', 'Traslado emisor itinerante CP'),
    ('19', 'Traslado a zona primaria'),
]
MODALIDAD_TRASLADO = [('01', 'Transporte público'), ('02', 'Transporte privado')]


class PeEdiDespatch(models.Model):
    _name = 'pe.edi.despatch'
    _description = 'Guía de Remisión Electrónica (Remitente)'
    _order = 'id desc'
    _inherit = ['mail.thread']

    name = fields.Char(compute='_compute_name', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    series = fields.Char(default='T001', required=True, size=4)
    correlativo = fields.Integer(readonly=True, copy=False)
    partner_id = fields.Many2one('res.partner', string="Destinatario", required=True)
    picking_id = fields.Many2one('stock.picking', string="Albarán de origen",
                                  help="Opcional: solo si el módulo de Inventario está instalado.")

    issue_date = fields.Date(default=fields.Date.context_today, required=True)
    motivo_traslado = fields.Selection(MOTIVO_TRASLADO, required=True, default='01')
    modalidad_traslado = fields.Selection(MODALIDAD_TRASLADO, required=True, default='02')
    fecha_traslado = fields.Date(required=True, default=fields.Date.context_today)
    peso_bruto_total = fields.Float(required=True, digits=(12, 2))

    punto_partida_ubigeo = fields.Char(size=6)
    punto_partida_direccion = fields.Char()
    punto_llegada_ubigeo = fields.Char(size=6)
    punto_llegada_direccion = fields.Char()

    vehiculo_placa = fields.Char(string="Placa del vehículo")
    conductor_numero_doc = fields.Char(string="Doc. del conductor")
    conductor_nombre = fields.Char(string="Nombre del conductor")

    line_ids = fields.One2many('pe.edi.despatch.line', 'despatch_id')

    state = fields.Selection([
        ('draft', 'Borrador'), ('generated', 'XML generado'), ('sent', 'Enviado'),
        ('accepted', 'Aceptado'), ('rejected', 'Rechazado'), ('error', 'Error'),
    ], default='draft', copy=False, tracking=True)
    xml_file = fields.Binary(copy=False, attachment=True)
    xml_filename = fields.Char(copy=False)
    ticket = fields.Char(copy=False)
    error_message = fields.Text(copy=False)
    qr_image = fields.Binary(copy=False, attachment=True)

    @api.depends('series', 'correlativo')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s-%s' % (rec.series, str(rec.correlativo).zfill(8)) if rec.correlativo else rec.series

    def action_generate_xml(self):
        for despatch in self:
            despatch._generate_xml()
        return True

    def _generate_xml(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(self.env._("Agrega al menos una línea de mercadería."))
        certificate = self.company_id.l10n_pe_edi_certificate_id
        if not certificate:
            raise UserError(self.env._("Configura un certificado digital para la empresa."))
        if not self.correlativo:
            last = self.search([
                ('company_id', '=', self.company_id.id), ('series', '=', self.series),
            ], order='correlativo desc', limit=1)
            self.correlativo = (last.correlativo or 0) + 1

        try:
            xml_root = ubl_despatch_builder.build_despatch_xml(self)
            private_key, x509_cert = certificate.get_private_key_and_certificate()
            xml_signer.sign_ubl_document(xml_root, private_key, x509_cert)
            signed_bytes = etree.tostring(xml_root, xml_declaration=True, encoding='UTF-8', standalone=False)
        except UserError:
            raise
        except Exception as e:  # noqa: BLE001
            _logger.exception("Error generando/firmando la Guía de Remisión")
            self.write({'state': 'error', 'error_message': str(e)})
            raise UserError(self.env._("No se pudo generar/firmar la guía: %s") % e)

        ruc = self.company_id.l10n_pe_edi_get_ruc()
        file_name = zip_helper.sunat_file_name(ruc, '09', self.series, str(self.correlativo).zfill(8))
        qr_data = qr_helper.build_qr_data(
            ruc, '09', self.series, str(self.correlativo).zfill(8), 0.0, 0.0, self.issue_date,
            self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            (self.partner_id.vat or '').replace('PE', ''), xml_signer.get_signature_digest(xml_root))
        self.write({
            'state': 'generated',
            'xml_file': base64.b64encode(signed_bytes),
            'xml_filename': file_name,
            'qr_image': qr_helper.build_qr_png_base64(qr_data),
            'error_message': False,
        })
        self.env['pe.edi.log'].create_log(self, 'gre', True, 'XML de guía generado: %s' % file_name)
        return True

    def action_send(self):
        for despatch in self:
            despatch._send()
        return True

    def _send(self):
        self.ensure_one()
        if not self.xml_file:
            self._generate_xml()
        company = self.company_id
        if not (company.l10n_pe_edi_gre_client_id and company.l10n_pe_edi_gre_client_secret):
            raise UserError(self.env._(
                "Configura Client ID/Secret de GRE en Contabilidad > Configuración > Facturación "
                "Electrónica SUNAT."))
        ruc = company.l10n_pe_edi_get_ruc()
        zip_bytes = zip_helper.zip_single_file(self.xml_filename, base64.b64decode(self.xml_file))
        try:
            token = sunat_gre_client.get_access_token(
                company.l10n_pe_edi_gre_client_id, company.l10n_pe_edi_gre_client_secret, ruc,
                company.l10n_pe_edi_sol_user, company.l10n_pe_edi_sol_password)
            result = sunat_gre_client.send_despatch(
                company.l10n_pe_edi_gre_submission_url, token, ruc, '09', self.series,
                str(self.correlativo).zfill(8), zip_bytes)
        except sunat_gre_client.SunatGreError as e:
            self.write({'state': 'error', 'error_message': str(e)})
            self.env['pe.edi.log'].create_log(self, 'gre', False, str(e))
            raise UserError(str(e))
        ticket = result.get('numTicket') or result.get('ticket')
        self.write({'state': 'sent', 'ticket': ticket, 'error_message': False})
        self.env['pe.edi.log'].create_log(self, 'gre', True, 'Enviado, ticket=%s' % ticket)
        return True

    def action_l10n_pe_edi_download_xml(self):
        self.ensure_one()
        if not self.xml_file:
            raise UserError(self.env._("No hay archivo disponible todavía."))
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'pe.edi.despatch'), ('res_id', '=', self.id), ('res_field', '=', 'xml_file'),
        ], limit=1)
        if not attachment:
            raise UserError(self.env._("No se encontró el archivo adjunto."))
        return {'type': 'ir.actions.act_url', 'url': '/web/content/%d?download=true' % attachment.id, 'target': 'self'}

    def action_check_status(self):
        for despatch in self:
            despatch._check_status()
        return True

    def _check_status(self):
        self.ensure_one()
        if not self.ticket:
            raise UserError(self.env._("Esta guía todavía no tiene un ticket de SUNAT."))
        company = self.company_id
        ruc = company.l10n_pe_edi_get_ruc()
        try:
            token = sunat_gre_client.get_access_token(
                company.l10n_pe_edi_gre_client_id, company.l10n_pe_edi_gre_client_secret, ruc,
                company.l10n_pe_edi_sol_user, company.l10n_pe_edi_sol_password)
            result = sunat_gre_client.get_status(
                company.l10n_pe_edi_gre_submission_url, token, ruc, '09', self.series,
                str(self.correlativo).zfill(8))
        except sunat_gre_client.SunatGreError as e:
            self.write({'error_message': str(e)})
            raise UserError(str(e))
        status_code = str(result.get('codRespuesta') or result.get('statusCode') or '')
        self.write({
            'state': 'accepted' if status_code == '0' else 'rejected' if status_code else self.state,
            'error_message': result.get('descRespuesta') or result.get('message'),
        })
        self.env['pe.edi.log'].create_log(self, 'gre', True, 'Estado: %s' % result)
        return True


class PeEdiDespatchLine(models.Model):
    _name = 'pe.edi.despatch.line'
    _description = 'Línea de Guía de Remisión'

    despatch_id = fields.Many2one('pe.edi.despatch', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product')
    name = fields.Char(string="Descripción", required=True)
    quantity = fields.Float(required=True, default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string="UdM")
