# -*- coding: utf-8 -*-
"""Builds the UBL 2.1 DespatchAdvice XML for a Guía de Remisión Electrónica
(GRE) — Remitente only (motivo/modalidad propios del remitente).

This structure is a best-effort reconstruction from the public GRE technical
documentation and has *not* been validated against a live SUNAT response the
way the Factura/Boleta builder has (SUNAT's GRE test endpoints require
credentials this environment doesn't have). Treat the element nesting here
as a solid starting point, and confirm it against the current "Manual del
Programador - Guía de Remisión Electrónica" before relying on it in
Producción.
"""
from .ubl_invoice_builder import _add_ubl_extensions, _cac, _cbc, _root, _uom_code

NS = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2",
    'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    'ds': "http://www.w3.org/2000/09/xmldsig#",
    'ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    'sac': "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
}


def _add_party(root, tag, company_or_partner, ruc_or_doc, scheme_id, name):
    party_wrap = _cac(root, tag)
    party = _cac(party_wrap, 'Party')
    party_id = _cac(party, 'PartyIdentification')
    _cbc(party_id, 'ID', ruc_or_doc, schemeID=scheme_id, schemeName='Documento de Identidad',
         schemeAgencyName='PE:SUNAT', schemeURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    legal_entity = _cac(party, 'PartyLegalEntity')
    _cbc(legal_entity, 'RegistrationName', name or '-')
    return party_wrap


def build_despatch_xml(despatch):
    """``despatch`` is a `pe.edi.despatch` record."""
    root = _root('DespatchAdvice', NS)
    _add_ubl_extensions(root)
    _cbc(root, 'UBLVersionID', '2.1')
    _cbc(root, 'CustomizationID', '2.0')
    _cbc(root, 'ID', '%s-%s' % (despatch.series, str(despatch.correlativo).zfill(8)))
    _cbc(root, 'IssueDate', despatch.issue_date.isoformat())
    _cbc(root, 'DespatchAdviceTypeCode', '09', listID='1001', listAgencyName='PE:SUNAT',
         listName='Tipo de GRE', listURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01')

    company = despatch.company_id
    ruc = company.l10n_pe_edi_get_ruc()
    signature = _cac(root, 'Signature')
    _cbc(signature, 'ID', 'IDSignSUNAT')
    signatory = _cac(signature, 'SignatoryParty')
    party_id = _cac(signatory, 'PartyIdentification')
    _cbc(party_id, 'ID', ruc)
    party_name = _cac(signatory, 'PartyName')
    _cbc(party_name, 'Name', company.name)
    attachment = _cac(signature, 'DigitalSignatureAttachment')
    external_ref = _cac(attachment, 'ExternalReference')
    _cbc(external_ref, 'URI', '#SignSUNAT')

    _add_party(root, 'DespatchSupplierParty', company, ruc, '6', company.name)
    partner = despatch.partner_id
    id_type = partner.l10n_latam_identification_type_id
    _add_party(root, 'DeliveryCustomerParty', partner, (partner.vat or '').replace('PE', '') or '-',
               id_type.l10n_pe_vat_code if id_type else '-', partner.name)

    shipment = _cac(root, 'Shipment')
    _cbc(shipment, 'ID', '1')
    _cbc(shipment, 'HandlingCode', despatch.motivo_traslado, listAgencyName='PE:SUNAT',
         listName='Motivo de traslado', listURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo20')
    _cbc(shipment, 'GrossWeightMeasure', '%.2f' % despatch.peso_bruto_total, unitCode='KGM')

    stage = _cac(shipment, 'ShipmentStage')
    _cbc(stage, 'TransportModeCode', despatch.modalidad_traslado, listAgencyName='PE:SUNAT',
         listName='Modalidad de traslado')
    transit = _cac(stage, 'TransitPeriod')
    _cbc(transit, 'StartDate', despatch.fecha_traslado.isoformat())
    if despatch.vehiculo_placa:
        transport_means = _cac(stage, 'TransportMeans')
        road = _cac(transport_means, 'RoadTransport')
        _cbc(road, 'LicensePlateID', despatch.vehiculo_placa)
    if despatch.conductor_numero_doc:
        driver = _cac(stage, 'DriverPerson')
        _cbc(driver, 'ID', despatch.conductor_numero_doc, schemeID='1')
        _cbc(driver, 'FirstName', despatch.conductor_nombre or '-')

    delivery = _cac(shipment, 'Delivery')
    delivery_address = _cac(delivery, 'DeliveryAddress')
    if despatch.punto_llegada_ubigeo:
        _cbc(delivery_address, 'ID', despatch.punto_llegada_ubigeo)
    if despatch.punto_llegada_direccion:
        line = _cac(delivery_address, 'AddressLine')
        _cbc(line, 'Line', despatch.punto_llegada_direccion)
    despatch_wrap = _cac(delivery, 'Despatch')
    despatch_address = _cac(despatch_wrap, 'DespatchAddress')
    if despatch.punto_partida_ubigeo:
        _cbc(despatch_address, 'ID', despatch.punto_partida_ubigeo)
    if despatch.punto_partida_direccion:
        line = _cac(despatch_address, 'AddressLine')
        _cbc(line, 'Line', despatch.punto_partida_direccion)

    for idx, line in enumerate(despatch.line_ids, start=1):
        despatch_line = _cac(root, 'DespatchLine')
        _cbc(despatch_line, 'ID', idx)
        _cbc(despatch_line, 'DeliveredQuantity', '%.10g' % line.quantity, unitCode=_uom_code(line.product_uom_id))
        item = _cac(despatch_line, 'Item')
        _cbc(item, 'Description', line.name or (line.product_id.name if line.product_id else '-'))

    return root
