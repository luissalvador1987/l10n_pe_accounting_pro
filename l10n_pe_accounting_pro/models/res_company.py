# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_tax_regime = fields.Selection([
        ('general', 'Régimen General'),
        ('mype', 'Régimen MYPE Tributario (RMT)'),
        ('rer', 'Régimen Especial de Renta (RER)'),
        ('nrus', 'Nuevo RUS'),
    ], string="Régimen tributario", default='general', required=True)
    l10n_pe_income_tax_rate = fields.Float(
        string="Tasa de Impuesto a la Renta (%)", default=29.5,
        help="Tasa usada para calcular el impuesto a la renta diferido por la diferencia temporal "
             "entre la depreciación contable (NIIF) y la tributaria (SUNAT).")

    # ------------------------------------------------------------------
    # Detracciones
    # ------------------------------------------------------------------
    l10n_pe_detraction_bank_account_id = fields.Many2one(
        'res.partner.bank', string="Cuenta de detracciones (Banco de la Nación)",
        help="Cuenta corriente en el Banco de la Nación donde el cliente debe depositar las "
             "detracciones a tu favor. Se imprime/muestra en los comprobantes sujetos a SPOT.")

    # ------------------------------------------------------------------
    # Retenciones / Percepciones de IGV
    # ------------------------------------------------------------------
    l10n_pe_is_retention_agent = fields.Boolean(
        string="Es Agente de Retención de IGV",
        help="Marca esta empresa como Agente de Retención designado por SUNAT (R.S. 037-2002). Al "
             "pagarle a un proveedor no excluido, se retendrá automáticamente el 3% y se emitirá el "
             "comprobante de retención correspondiente.")
    l10n_pe_retention_rate = fields.Float(string="Tasa de retención (%)", default=3.0)
    l10n_pe_retention_min_amount = fields.Monetary(
        string="Monto mínimo para retener", default=700.0, currency_field='currency_id',
        help="Por debajo de este importe (S/ 700 por comprobante, salvo excepciones) no corresponde "
             "retener.")
    l10n_pe_retention_sequence_id = fields.Many2one(
        'ir.sequence', string="Secuencia de comprobantes de retención", copy=False)
    l10n_pe_retention_payable_account_id = fields.Many2one(
        'account.account', string="Cuenta IGV Retenciones por Pagar (401.75)",
        help="Pasivo donde se acumulan las retenciones que TÚ le haces a tus proveedores, pendientes "
             "de rendir a SUNAT (PDT 617).")
    l10n_pe_retention_receivable_account_id = fields.Many2one(
        'account.account', string="Cuenta IGV Retenido por Terceros (1693)",
        help="Activo/crédito fiscal donde se registran las retenciones que TUS CLIENTES te han hecho "
             "a ti, aplicables contra tu IGV por pagar del periodo (PDT 621).")

    l10n_pe_is_perception_agent = fields.Boolean(
        string="Es Agente de Percepción de IGV",
        help="Marca esta empresa como Agente de Percepción designado por SUNAT (R.S. 058-2006, "
             "Régimen de Percepciones - Venta Interna). Al venderle a un cliente no excluido, se "
             "adicionará automáticamente el porcentaje de percepción al comprobante.")
    l10n_pe_perception_rate = fields.Float(
        string="Tasa de percepción (%)", default=2.0,
        help="2% tasa general; 1% si el cliente tiene la condición de domicilio fiscal habido y está "
             "afecto en el Régimen General y en las últimas 12 cuotas fue \"buen contribuyente\" o "
             "agente de retención (verifícalo caso por caso); 0.5% cuando la operación se realiza a "
             "través de un medio de pago y el importe está sujeto a bancarización.")
    l10n_pe_perception_sequence_id = fields.Many2one(
        'ir.sequence', string="Secuencia de comprobantes de percepción", copy=False)
    l10n_pe_perception_payable_account_id = fields.Many2one(
        'account.account', string="Cuenta IGV Percepciones por Pagar",
        help="Pasivo donde se acumula lo que TÚ le percibes a tus clientes, pendiente de rendir a "
             "SUNAT (PDT 621 - casilla de percepciones efectuadas).")
    l10n_pe_perception_receivable_account_id = fields.Many2one(
        'account.account', string="Cuenta IGV Percepciones por Aplicar",
        help="Activo/crédito fiscal donde se registra lo que TUS PROVEEDORES te han percibido a ti, "
             "aplicable contra tu IGV por pagar del periodo.")

    # ------------------------------------------------------------------
    # PLE / SIRE
    # ------------------------------------------------------------------
    l10n_pe_sire_since_period = fields.Char(
        string="Obligado a SIRE desde (AAAAMM)",
        help="Periodo desde el cual SUNAT te obliga a usar SIRE en vez del PLE clásico para el "
             "Registro de Ventas (RVIE) y/o Compras (RCE). Puramente informativo: este módulo no "
             "envía nada al API de SIRE, solo genera el TXT clásico de PLE.")

    @api.model
    def _l10n_pe_accounting_get_next_retention_sequence(self):
        self.ensure_one()
        if not self.l10n_pe_retention_sequence_id:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'Comprobante de Retención - %s' % self.name,
                'code': 'l10n_pe_accounting.retention.%s' % self.id,
                'prefix': 'R001-', 'padding': 8, 'company_id': self.id,
            })
            self.l10n_pe_retention_sequence_id = seq
        return self.l10n_pe_retention_sequence_id.next_by_id()

    @api.model
    def _l10n_pe_accounting_get_next_perception_sequence(self):
        self.ensure_one()
        if not self.l10n_pe_perception_sequence_id:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'Comprobante de Percepción - %s' % self.name,
                'code': 'l10n_pe_accounting.perception.%s' % self.id,
                'prefix': 'P001-', 'padding': 8, 'company_id': self.id,
            })
            self.l10n_pe_perception_sequence_id = seq
        return self.l10n_pe_perception_sequence_id.next_by_id()
