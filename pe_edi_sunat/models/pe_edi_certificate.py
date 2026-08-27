# -*- coding: utf-8 -*-
import base64
import logging
from datetime import datetime, timezone

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID
except ImportError:  # pragma: no cover - always available on a standard Odoo install
    pkcs12 = None
    NameOID = None


class PeEdiCertificate(models.Model):
    _name = 'pe.edi.certificate'
    _description = 'Certificado Digital SUNAT'
    _order = 'id desc'

    name = fields.Char(required=True, default="Certificado digital")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    pfx_file = fields.Binary(string="Archivo .pfx/.p12", required=True, attachment=True)
    pfx_filename = fields.Char(string="Nombre del archivo")
    password = fields.Char(string="Contraseña", help="Contraseña del archivo .pfx. Solo puede verla el "
                            "grupo Administrador de Facturación Electrónica.")

    is_test = fields.Boolean(
        string="Es de prueba (autofirmado)", default=True,
        help="Márcalo si es un certificado autofirmado usado solo para el ambiente Beta de SUNAT. "
             "Para Producción, SUNAT exige un certificado digital vigente emitido por una entidad "
             "certificadora autorizada (RENIEC, etc.).")

    state = fields.Selection([
        ('draft', 'Sin validar'),
        ('valid', 'Vigente'),
        ('expired', 'Vencido'),
        ('error', 'Error'),
    ], default='draft', readonly=True, copy=False)
    error_message = fields.Text(readonly=True, copy=False)

    date_start = fields.Datetime(string="Válido desde", readonly=True, copy=False)
    date_end = fields.Datetime(string="Válido hasta", readonly=True, copy=False)
    subject_cn = fields.Char(string="Titular (CN)", readonly=True, copy=False)
    issuer_cn = fields.Char(string="Emisor (CN)", readonly=True, copy=False)
    serial_number = fields.Char(string="Número de serie", readonly=True, copy=False)

    def action_validate(self):
        for cert in self:
            try:
                private_key, certificate, _extra = cert._load_pkcs12()
                if certificate is None:
                    raise UserError(self.env._(
                        "El archivo no contiene un certificado. Verifica el archivo y la contraseña."))
                not_before = cert._cert_datetime(certificate, 'before')
                not_after = cert._cert_datetime(certificate, 'after')
                subject_cn = cert._get_cn(certificate.subject) or str(certificate.subject)
                issuer_cn = cert._get_cn(certificate.issuer) or str(certificate.issuer)
                now = fields.Datetime.now().replace(tzinfo=timezone.utc)
                state = 'valid' if not_before <= now <= not_after else 'expired'
                cert.write({
                    'state': state,
                    'error_message': False,
                    'date_start': not_before.replace(tzinfo=None),
                    'date_end': not_after.replace(tzinfo=None),
                    'subject_cn': subject_cn,
                    'issuer_cn': issuer_cn,
                    'serial_number': str(certificate.serial_number),
                })
            except Exception as e:  # noqa: BLE001
                _logger.exception("Error validando certificado digital SUNAT")
                cert.write({'state': 'error', 'error_message': str(e)})
        return True

    def _load_pkcs12(self):
        """Return (private_key, certificate, additional_certificates) from the
        stored .pfx, decrypted with the stored password."""
        self.ensure_one()
        if pkcs12 is None:
            raise UserError(self.env._(
                "La librería 'cryptography' no está disponible en este servidor Odoo."))
        if not self.pfx_file:
            raise UserError(self.env._("Carga primero el archivo .pfx/.p12."))
        raw = base64.b64decode(self.pfx_file)
        password_bytes = self.password.encode() if self.password else None
        try:
            return pkcs12.load_key_and_certificates(raw, password_bytes)
        except Exception as e:  # noqa: BLE001
            raise UserError(self.env._(
                "No se pudo abrir el certificado: verifica que el archivo y la contraseña sean correctos "
                "(%s)") % e)

    def get_private_key_and_certificate(self):
        """Public accessor used by the XML signer."""
        self.ensure_one()
        private_key, certificate, _extra = self._load_pkcs12()
        if not private_key or not certificate:
            raise UserError(self.env._(
                "El certificado '%s' no tiene una llave privada o un certificado válidos.") % self.name)
        return private_key, certificate

    @staticmethod
    def _get_cn(name):
        if NameOID is None:
            return None
        attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
        return attrs[0].value if attrs else None

    @staticmethod
    def _cert_datetime(certificate, which):
        # cryptography >= 42 exposes *_utc properties (tz-aware); older
        # versions only expose the naive ones. Support both.
        attr = 'not_valid_%s_utc' % which
        if hasattr(certificate, attr):
            return getattr(certificate, attr)
        naive = getattr(certificate, 'not_valid_%s' % which)
        return naive.replace(tzinfo=timezone.utc)
