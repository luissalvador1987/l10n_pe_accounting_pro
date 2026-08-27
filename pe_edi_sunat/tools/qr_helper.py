# -*- coding: utf-8 -*-
"""QR code for the printed representation (RIDE), per SUNAT's pipe-separated
data format: RUC|TipoDoc|Serie|Correlativo|IGV|Total|Fecha|TipoDocReceptor|
NumDocReceptor|HashDigest."""
import base64
import io

import qrcode


def build_qr_data(ruc, doc_type_code, serie, correlativo, igv, total, issue_date,
                   receiver_doc_type, receiver_doc_number, digest_value):
    fields = [
        ruc or '', doc_type_code or '', serie or '', correlativo or '',
        '%.2f' % (igv or 0.0), '%.2f' % (total or 0.0),
        issue_date.isoformat() if hasattr(issue_date, 'isoformat') else (issue_date or ''),
        receiver_doc_type or '', receiver_doc_number or '', digest_value or '',
    ]
    return '|'.join(fields)


def build_qr_png_base64(data):
    img = qrcode.make(data, border=1)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()
