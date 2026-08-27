# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pe_retention_excluded = fields.Boolean(
        string="Excluir de retención de IGV",
        help="Márcalo si este proveedor NO debe sufrir la retención automática del 3% aunque seamos "
             "Agente de Retención (por ejemplo: el propio proveedor ya es Agente de Percepción, está "
             "en el Nuevo RUS, la operación está exonerada/inafecta, o se le emite un recibo por "
             "honorarios sujeto a retención de renta de 4ta en vez de IGV).")
    l10n_pe_perception_excluded = fields.Boolean(
        string="Excluir de percepción de IGV",
        help="Márcalo si este cliente NO debe sufrir la percepción automática aunque seamos Agente "
             "de Percepción (por ejemplo: el propio cliente es Agente de Retención o de Percepción, "
             "es una entidad del sector público, o la operación está exonerada/inafecta de IGV).")
    l10n_pe_is_withholding_agent = fields.Boolean(
        string="Es Agente de Retención (informativo)",
        help="Marca si este tercero (cliente o proveedor) es, a su vez, Agente de Retención de IGV "
             "designado por SUNAT — útil para decidir exclusiones de percepción/retención cruzadas.")
