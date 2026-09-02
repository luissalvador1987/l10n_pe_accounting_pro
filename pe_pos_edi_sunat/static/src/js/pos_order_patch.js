/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        result.l10n_pe_edi_state = this.l10n_pe_edi_state;
        result.l10n_pe_edi_document_number = this.l10n_pe_edi_document_number;
        result.l10n_pe_edi_qr_image = this.l10n_pe_edi_qr_image;
        return result;
    },
});
