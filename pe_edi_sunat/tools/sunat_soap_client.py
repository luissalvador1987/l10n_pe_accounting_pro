# -*- coding: utf-8 -*-
"""Raw SOAP client for SUNAT's `billService` (Factura/Boleta/Notas).

SUNAT's own WSDL hosting turns out to be unreliable for dynamic, WSDL-driven
clients (empirically: fetching `billService?wsdl` and then its imported
`billService?ns1.wsdl` in the same HTTP session gets the *second* request
rejected with a bare nginx 401 — a session/anti-scraping quirk of their beta
server, not a real authentication error). Every mainstream Peru e-invoicing
library sidesteps this by building the SOAP envelope by hand instead of
depending on runtime WSDL introspection, which is what this module does too.
The envelope shape, endpoint, SOAPAction headers and WS-Security UsernameToken
format below were confirmed against the real SUNAT Beta service.
"""
import base64
import logging

import requests
from lxml import etree

_logger = logging.getLogger(__name__)

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
WSSE_NS = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
SERVICE_NS = "http://service.sunat.gob.pe"
PASSWORD_TEXT_TYPE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-username-token-profile-1.0#PasswordText"

BETA_URL = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService"
PRODUCTION_URL = "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService"


class SunatSoapError(Exception):
    def __init__(self, fault_code, fault_string):
        self.fault_code = fault_code
        self.fault_string = fault_string
        super().__init__("%s: %s" % (fault_code, fault_string))


def get_endpoint(environment):
    return BETA_URL if environment == 'beta' else PRODUCTION_URL


def _build_envelope(ruc, sol_username, sol_password, body_xml):
    username = "%s%s" % (ruc, sol_username)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="%s" xmlns:ser="%s" xmlns:wsse="%s">'
        '<soapenv:Header>'
        '<wsse:Security soapenv:mustUnderstand="1">'
        '<wsse:UsernameToken>'
        '<wsse:Username>%s</wsse:Username>'
        '<wsse:Password Type="%s">%s</wsse:Password>'
        '</wsse:UsernameToken>'
        '</wsse:Security>'
        '</soapenv:Header>'
        '<soapenv:Body>%s</soapenv:Body>'
        '</soapenv:Envelope>'
    ) % (SOAP_NS, SERVICE_NS, WSSE_NS, username, PASSWORD_TEXT_TYPE, sol_password, body_xml)


def _post(endpoint, envelope, soap_action, timeout=45):
    try:
        response = requests.post(
            endpoint,
            data=envelope.encode('utf-8'),
            headers={'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': soap_action},
            timeout=timeout,
        )
    except requests.exceptions.RequestException as e:
        raise SunatSoapError('CONNECTION_ERROR', str(e))
    return response.text


def _parse_response(response_text, response_local_name, value_local_name):
    try:
        root = etree.fromstring(response_text.encode('utf-8'))
    except etree.XMLSyntaxError as e:
        raise SunatSoapError('INVALID_RESPONSE', 'No se pudo interpretar la respuesta de SUNAT: %s' % e)

    fault = root.find('.//{%s}Fault' % SOAP_NS)
    if fault is not None:
        fault_code = fault.findtext('faultcode') or 'UNKNOWN'
        fault_string = fault.findtext('faultstring') or 'Error desconocido de SUNAT'
        raise SunatSoapError(fault_code, fault_string)

    response_node = root.find('.//{%s}%s' % (SERVICE_NS, response_local_name))
    if response_node is None:
        # some SUNAT responses omit the namespace on the wrapper node
        response_node = next((el for el in root.iter() if etree.QName(el).localname == response_local_name), None)
    if response_node is None:
        raise SunatSoapError('EMPTY_RESPONSE', 'SUNAT no devolvió %s' % response_local_name)

    value_node = next((el for el in response_node.iter() if etree.QName(el).localname == value_local_name), None)
    if value_node is None or not value_node.text:
        return None
    return base64.b64decode(value_node.text)


def send_bill(endpoint, ruc, sol_username, sol_password, file_name, zip_bytes, timeout=60):
    """POSTs one signed document (as a zip) to SUNAT. Returns the CDR zip bytes."""
    body = (
        '<ser:sendBill>'
        '<fileName>%s</fileName>'
        '<contentFile>%s</contentFile>'
        '</ser:sendBill>'
    ) % (file_name, base64.b64encode(zip_bytes).decode())
    envelope = _build_envelope(ruc, sol_username, sol_password, body)
    response_text = _post(endpoint, envelope, 'urn:sendBill', timeout=timeout)
    return _parse_response(response_text, 'sendBillResponse', 'applicationResponse')


def send_summary(endpoint, ruc, sol_username, sol_password, file_name, zip_bytes, timeout=60):
    """POSTs a Resumen Diario / Comunicación de Baja. Returns the ticket string."""
    body = (
        '<ser:sendSummary>'
        '<fileName>%s</fileName>'
        '<contentFile>%s</contentFile>'
        '</ser:sendSummary>'
    ) % (file_name, base64.b64encode(zip_bytes).decode())
    envelope = _build_envelope(ruc, sol_username, sol_password, body)
    response_text = _post(endpoint, envelope, 'urn:sendSummary', timeout=timeout)
    try:
        root = etree.fromstring(response_text.encode('utf-8'))
    except etree.XMLSyntaxError as e:
        raise SunatSoapError('INVALID_RESPONSE', str(e))
    fault = root.find('.//{%s}Fault' % SOAP_NS)
    if fault is not None:
        raise SunatSoapError(fault.findtext('faultcode') or 'UNKNOWN', fault.findtext('faultstring') or '')
    ticket_node = next((el for el in root.iter() if etree.QName(el).localname == 'ticket'), None)
    if ticket_node is None:
        raise SunatSoapError('NO_TICKET', 'SUNAT no devolvió un ticket.')
    return ticket_node.text


def get_status(endpoint, ruc, sol_username, sol_password, ticket, timeout=30):
    """Polls the status of a ticket obtained from sendSummary. Returns
    (status_code, cdr_zip_bytes_or_None)."""
    body = '<ser:getStatus><ticket>%s</ticket></ser:getStatus>' % ticket
    envelope = _build_envelope(ruc, sol_username, sol_password, body)
    response_text = _post(endpoint, envelope, 'urn:getStatus', timeout=timeout)
    try:
        root = etree.fromstring(response_text.encode('utf-8'))
    except etree.XMLSyntaxError as e:
        raise SunatSoapError('INVALID_RESPONSE', str(e))
    fault = root.find('.//{%s}Fault' % SOAP_NS)
    if fault is not None:
        raise SunatSoapError(fault.findtext('faultcode') or 'UNKNOWN', fault.findtext('faultstring') or '')

    status_code_node = next((el for el in root.iter() if etree.QName(el).localname == 'statusCode'), None)
    content_node = next((el for el in root.iter() if etree.QName(el).localname == 'content'), None)
    status_code = status_code_node.text if status_code_node is not None else None
    cdr_bytes = base64.b64decode(content_node.text) if content_node is not None and content_node.text else None
    return status_code, cdr_bytes
