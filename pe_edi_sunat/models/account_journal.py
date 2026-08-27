# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_pe_edi_series = fields.Char(
        string="Serie SUNAT", size=4,
        help="Serie de 4 caracteres autorizada por SUNAT para este punto de emisión "
             "(ej: F001 para facturas, B001 para boletas). Debe coincidir con la serie "
             "registrada/autorizada en SUNAT para este establecimiento.")

    @api.constrains('l10n_pe_edi_series')
    def _check_l10n_pe_edi_series(self):
        for journal in self:
            series = journal.l10n_pe_edi_series
            if series and (len(series) != 4 or not series.isalnum()):
                raise ValidationError(self.env._(
                    "La serie SUNAT '%s' debe tener exactamente 4 caracteres alfanuméricos.") % series)
