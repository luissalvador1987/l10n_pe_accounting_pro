# -*- coding: utf-8 -*-
import io
import zipfile


def sunat_file_name(ruc, doc_type_code, serie, correlativo, extension='xml'):
    return "%s-%s-%s-%s.%s" % (ruc, doc_type_code, serie, correlativo, extension)


def zip_single_file(inner_file_name, content_bytes):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_file_name, content_bytes)
    return buf.getvalue()
