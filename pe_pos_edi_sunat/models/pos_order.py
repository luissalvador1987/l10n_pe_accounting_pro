# -*- coding: utf-8 -*-
import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_pe_edi_state = fields.Selection(related='account_move.l10n_pe_edi_state', string="Estado SUNAT")
    l10n_pe_edi_error_message = fields.Text(related='account_move.l10n_pe_edi_error_message')
    l10n_pe_edi_qr_image = fields.Binary(related='account_move.l10n_pe_edi_qr_image')
    l10n_pe_edi_document_number = fields.Char(
        related='account_move.l10n_latam_document_number', string="Nº comprobante SUNAT")

    # ------------------------------------------------------------------
    # Force a Boleta/Factura for every Peru order, not only invoiced ones
    # ------------------------------------------------------------------
    def _l10n_pe_edi_pos_is_applicable(self):
        self.ensure_one()
        return bool(
            self.company_id.account_fiscal_country_id.code == 'PE'
            and not self.account_move
            and (self.config_id.l10n_pe_edi_boleta_journal_id or self.config_id.l10n_pe_edi_factura_journal_id)
        )

    def _l10n_pe_edi_prepare_for_invoice(self):
        """Make sure the order has everything ``_generate_pos_order_invoice`` needs
        (a partner, and ``to_invoice=True``) so the native POS flow that already
        knows how to build an account.move runs for this order too — SUNAT requires
        a fiscal document (Boleta or Factura) for every sale, not only the ones a
        customer explicitly asked to be invoiced."""
        self.ensure_one()
        config = self.config_id
        if not self.partner_id:
            if not config.l10n_pe_edi_default_partner_id:
                raise UserError(self.env._(
                    "Configura un 'Cliente genérico para Boleta' en Punto de Venta > Configuración > "
                    "%s (sección Facturación Electrónica SUNAT), o selecciona un cliente en la venta."
                ) % config.name)
            self.partner_id = config.l10n_pe_edi_default_partner_id
        self.to_invoice = True

    def _process_saved_order(self, draft):
        if not draft and self.state != 'cancel' and self._l10n_pe_edi_pos_is_applicable():
            self._l10n_pe_edi_prepare_for_invoice()
        return super()._process_saved_order(draft)

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.company_id.account_fiscal_country_id.code == 'PE':
            config = self.config_id
            is_ruc = self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code == '6'
            journal = config.l10n_pe_edi_factura_journal_id if is_ruc else config.l10n_pe_edi_boleta_journal_id
            if journal:
                vals['journal_id'] = journal.id
        return vals

    def _generate_pos_order_invoice(self):
        result = super()._generate_pos_order_invoice()
        for order in self:
            move = order.account_move
            config = order.config_id
            if (move and move.l10n_pe_edi_is_required and config.l10n_pe_edi_auto_send
                    and move.l10n_pe_edi_state not in ('sent', 'accepted')):
                try:
                    move.action_l10n_pe_edi_generate_and_send()
                except Exception as e:  # noqa: BLE001 — never let a SUNAT hiccup break the checkout
                    _logger.warning(
                        "No se pudo enviar a SUNAT el comprobante de la orden POS %s: %s", order.name, e)
        return result

    def action_l10n_pe_edi_retry_send(self):
        for order in self:
            if not order.account_move:
                raise UserError(self.env._("Esta orden todavía no tiene un comprobante generado."))
            order.account_move.action_l10n_pe_edi_generate_and_send()
        return True
