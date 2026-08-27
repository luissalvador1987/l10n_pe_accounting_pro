# -*- coding: utf-8 -*-
"""Parses the CDR (Constancia de Recepción) ZIP SUNAT returns for every
document sent. The CDR is itself a UBL ApplicationResponse; SUNAT's
convention for `cbc:ResponseCode` is: 0 = aceptado, 4000-4999 = aceptado con
observaciones, anything else = rechazado.
"""
import io
import zipfile

from lxml import etree


def parse_cdr_zip(zip_bytes):
    result = {'code': None, 'description': None, 'notes': [], 'accepted': False, 'xml_name': None}
    if not zip_bytes:
        result['description'] = 'SUNAT no devolvió una CDR.'
        return result

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        result['description'] = 'La respuesta de SUNAT no es un archivo ZIP válido.'
        return result

    xml_name = next((n for n in zf.namelist() if n.lower().endswith('.xml')), None)
    if not xml_name:
        result['description'] = 'El ZIP de respuesta de SUNAT no contiene un XML.'
        return result
    result['xml_name'] = xml_name

    try:
        root = etree.fromstring(zf.read(xml_name))
    except etree.XMLSyntaxError as e:
        result['description'] = 'No se pudo interpretar la CDR: %s' % e
        return result

    def find_text(local_name):
        node = next((el for el in root.iter() if etree.QName(el).localname == local_name), None)
        return node.text if node is not None else None

    code = find_text('ResponseCode')
    result['code'] = code
    result['description'] = find_text('Description')
    result['notes'] = [el.text for el in root.iter() if etree.QName(el).localname == 'Note' and el.text]

    if code is not None and code.isdigit():
        code_int = int(code)
        result['accepted'] = code_int == 0 or 4000 <= code_int <= 4999
    return result
