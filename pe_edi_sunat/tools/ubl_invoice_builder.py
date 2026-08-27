# -*- coding: utf-8 -*-
"""Builds the UBL 2.1 XML for Facturas, Boletas, Notas de Crédito y Notas de
Débito following SUNAT's "Sistema de Emisión Electrónica" customization.

Scope / known approximations (documented rather than silently guessed):
  * Fully covers the standard "Gravado - Operación Onerosa" (18% IGV) case,
    which is what the overwhelming majority of invoices use, and is the
    scenario validated end-to-end against SUNAT's Beta service.
  * Exonerado/Inafecto/Gratuito/Exportación lines are emitted using the
    UN/ECE 5305 category, the SUNAT tributo code and a Catálogo 07 exemption
    reason code inferred from the tributo (each maps to its single most
    common variant); if you have a case that needs a different Catálogo 07
    value (e.g. a specific "gratuito" sub-type), override it per line.
  * Unit of measure codes (Catálogo 03) are inferred from the product UoM's
    name with a small heuristic map, defaulting to "NIU" (unidad); refine
    `UOM_TO_UNECE` if you sell in units it doesn't recognize.
  * Only a single "Contado" payment term is emitted; installment/credit
    terms (`cac:PaymentTerms` per cuota) are not generated yet.
"""
from lxml import etree

from .numbers_to_words import amount_to_words

NS = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    'ds': "http://www.w3.org/2000/09/xmldsig#",
    'ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    'qdt': "urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2",
    'sac': "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
    'udt': "urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2",
}
NS_CREDIT_NOTE = dict(NS)
NS_CREDIT_NOTE[None] = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
NS_DEBIT_NOTE = dict(NS)
NS_DEBIT_NOTE[None] = "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2"

CAC = NS['cac']
CBC = NS['cbc']
EXT = NS['ext']

UOM_TO_UNECE = {
    'unit': 'NIU', 'unidad': 'NIU', 'units': 'NIU', 'u': 'NIU',
    'kg': 'KGM', 'kilogram': 'KGM', 'kilogramo': 'KGM', 'kilogramos': 'KGM',
    'g': 'GRM', 'gram': 'GRM',
    'l': 'LTR', 'liter': 'LTR', 'litro': 'LTR', 'litros': 'LTR',
    'm': 'MTR', 'meter': 'MTR', 'metro': 'MTR',
    'm2': 'MTK', 'm²': 'MTK',
    'm3': 'MTQ', 'm³': 'MTQ',
    'box': 'BX', 'caja': 'BX',
    'dozen': 'DZN', 'docena': 'DZN',
    'hour': 'HUR', 'hora': 'HUR',
    'day': 'DAY', 'dia': 'DAY', 'día': 'DAY',
    'service': 'ZZ', 'servicio': 'ZZ',
}


def _uom_code(uom):
    if not uom:
        return 'NIU'
    return UOM_TO_UNECE.get((uom.name or '').strip().lower(), 'NIU')


def _sub(parent, tag, text=None, **attrs):
    el = etree.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    for key, value in attrs.items():
        el.set(key, str(value))
    return el


def _cbc(parent, name, text=None, **attrs):
    return _sub(parent, '{%s}%s' % (CBC, name), text, **attrs)


def _cac(parent, name):
    return _sub(parent, '{%s}%s' % (CAC, name))


def _root(root_tag, nsmap):
    return etree.Element('{%s}%s' % (nsmap[None], root_tag), nsmap={
        k or None: v for k, v in nsmap.items()
    })


def _add_ubl_extensions(root):
    """Adds the (empty) placeholder the signer will fill in later."""
    ublextensions = _sub(root, '{%s}UBLExtensions' % EXT)
    ublextension = _sub(ublextensions, '{%s}UBLExtension' % EXT)
    _sub(ublextension, '{%s}ExtensionContent' % EXT)
    return ublextensions


def _add_signature_block(root, ruc, legal_name):
    signature = _cac(root, 'Signature')
    _cbc(signature, 'ID', 'IDSignSUNAT')
    signatory = _cac(signature, 'SignatoryParty')
    party_id = _cac(signatory, 'PartyIdentification')
    _cbc(party_id, 'ID', ruc)
    party_name = _cac(signatory, 'PartyName')
    _cbc(party_name, 'Name', legal_name)
    attachment = _cac(signature, 'DigitalSignatureAttachment')
    external_ref = _cac(attachment, 'ExternalReference')
    _cbc(external_ref, 'URI', '#SignSUNAT')


def _add_address(parent, ubigeo, address_line, district=None, province=None, department=None):
    address = _cac(parent, 'RegistrationAddress')
    if ubigeo:
        _cbc(address, 'ID', ubigeo, schemeAgencyName='PE:INEI', schemeName='Ubigeos')
    _cbc(address, 'AddressTypeCode', '0000')
    if district:
        _cbc(address, 'CitySubdivisionName', district)
    if province:
        _cbc(address, 'CityName', province)
    if department:
        _cbc(address, 'CountrySubentity', department)
    if address_line:
        line = _cac(address, 'AddressLine')
        _cbc(line, 'Line', address_line)
    country = _cac(address, 'Country')
    _cbc(country, 'IdentificationCode', 'PE')


def _add_supplier_party(root, company):
    supplier = _cac(root, 'AccountingSupplierParty')
    party = _cac(supplier, 'Party')
    party_id = _cac(party, 'PartyIdentification')
    _cbc(party_id, 'ID', (company.vat or '').replace('PE', ''), schemeID='6',
         schemeName='Documento de Identidad', schemeAgencyName='PE:SUNAT',
         schemeURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    party_name = _cac(party, 'PartyName')
    _cbc(party_name, 'Name', company.l10n_pe_edi_trade_name or company.name)
    legal_entity = _cac(party, 'PartyLegalEntity')
    _cbc(legal_entity, 'RegistrationName', company.name)
    partner = company.partner_id
    district = partner.l10n_pe_district
    _add_address(
        legal_entity, district.code if district else False, partner.street,
        district=district.name if district else False,
        province=district.city_id.name if district and district.city_id else False,
        department=partner.state_id.name if partner.state_id else False,
    )
    return supplier


def _add_customer_party(root, partner):
    customer = _cac(root, 'AccountingCustomerParty')
    party = _cac(customer, 'Party')
    id_type = partner.l10n_latam_identification_type_id
    scheme_id = id_type.l10n_pe_vat_code if id_type else '-'
    doc_number = (partner.vat or '').replace('PE', '') or '-'
    party_id = _cac(party, 'PartyIdentification')
    _cbc(party_id, 'ID', doc_number, schemeID=scheme_id or '-',
         schemeName='Documento de Identidad', schemeAgencyName='PE:SUNAT',
         schemeURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    legal_entity = _cac(party, 'PartyLegalEntity')
    _cbc(legal_entity, 'RegistrationName', partner.name or '-')
    if scheme_id == '6' and partner.street:
        district = partner.l10n_pe_district
        _add_address(legal_entity, district.code if district else False, partner.street)
    return customer


def _add_payment_terms(root):
    terms = _cac(root, 'PaymentTerms')
    _cbc(terms, 'ID', 'FormaPago')
    _cbc(terms, 'PaymentMeansID', 'Contado')


def _line_tax_info(move, line):
    """Returns (tax, base, tax_amount) for the (single, common case) tax on
    an invoice line — the first IGV-like tax found, or a synthetic
    'unaffected' tuple if the line has no taxes at all."""
    taxes = line.tax_ids
    if not taxes:
        return None, line.price_subtotal, 0.0
    tax = taxes[0]
    tax_amount = line.price_total - line.price_subtotal
    return tax, line.price_subtotal, tax_amount


def _tax_category_and_scheme(tax):
    unece = (tax.l10n_pe_edi_unece_category if tax else False) or 'S'
    tributo = (tax.l10n_pe_edi_tax_code if tax else False) or '9998'
    scheme_name = {
        '1000': 'IGV', '1016': 'IVAP', '2000': 'ISC', '7152': 'ICBPER',
        '9995': 'EXP', '9996': 'GRA', '9997': 'EXO', '9998': 'INA',
    }.get(tributo, 'OTROS')
    tax_type_code = 'VAT' if tributo in ('1000', '1016') else 'FRE' if tributo == '9996' else 'OTH'
    # SUNAT Catálogo 07 (Tipo de Afectación del IGV) — required on every tax
    # category, not just informational. Covers the standard "Gravado -
    # Operación Onerosa" case exactly (confirmed against the real Beta
    # service); the other categories use their most common variant.
    exemption_reason_code = {
        '1000': '10', '1016': '10', '9997': '20', '9998': '30', '9995': '40', '9996': '21',
    }.get(tributo, '30')
    return unece, tributo, scheme_name, tax_type_code, exemption_reason_code


def _add_tax_category(parent, tax, percent=None):
    category = _cac(parent, 'TaxCategory')
    unece, tributo, scheme_name, tax_type_code, exemption_reason_code = _tax_category_and_scheme(tax)
    _cbc(category, 'ID', unece, schemeID='UN/ECE 5305', schemeName='Tax Category Identifier',
         schemeAgencyName='United Nations Economic Commission for Europe')
    if percent is not None:
        _cbc(category, 'Percent', '%.2f' % percent)
    _cbc(category, 'TaxExemptionReasonCode', exemption_reason_code, listAgencyName='PE:SUNAT',
         listName='Afectacion del IGV', listURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07')
    scheme = _cac(category, 'TaxScheme')
    _cbc(scheme, 'ID', tributo, schemeName='Codigo de tributos', schemeAgencyName='PE:SUNAT',
         schemeURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo05')
    _cbc(scheme, 'Name', scheme_name)
    _cbc(scheme, 'TaxTypeCode', tax_type_code)


def _add_line_tax_total(line_el, tax, base, tax_amount, currency):
    tax_total = _cac(line_el, 'TaxTotal')
    _cbc(tax_total, 'TaxAmount', '%.2f' % tax_amount, currencyID=currency)
    subtotal = _cac(tax_total, 'TaxSubtotal')
    _cbc(subtotal, 'TaxableAmount', '%.2f' % base, currencyID=currency)
    _cbc(subtotal, 'TaxAmount', '%.2f' % tax_amount, currencyID=currency)
    _add_tax_category(subtotal, tax, percent=tax.amount if tax else 0.0)


def _add_lines(root, move, line_tag='InvoiceLine', quantity_tag='InvoicedQuantity'):
    currency = move.currency_id.name
    # Odoo 18: regular sellable lines have display_type == 'product' (it's
    # always set, never False); sections/notes/rounding/etc. must be excluded.
    sellable_lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
    for idx, line in enumerate(sellable_lines, start=1):
        line_el = _cac(root, line_tag)
        _cbc(line_el, 'ID', idx)
        uom = _uom_code(line.product_uom_id)
        _cbc(line_el, quantity_tag, '%.10g' % line.quantity, unitCode=uom)
        _cbc(line_el, 'LineExtensionAmount', '%.2f' % line.price_subtotal, currencyID=currency)

        tax, base, tax_amount = _line_tax_info(move, line)
        price_with_tax = (line.price_subtotal + tax_amount) / line.quantity if line.quantity else 0.0
        pricing_ref = _cac(line_el, 'PricingReference')
        alt_price = _cac(pricing_ref, 'AlternativeConditionPrice')
        _cbc(alt_price, 'PriceAmount', '%.2f' % price_with_tax, currencyID=currency)
        _cbc(alt_price, 'PriceTypeCode', '01')

        _add_line_tax_total(line_el, tax, base, tax_amount, currency)

        item = _cac(line_el, 'Item')
        _cbc(item, 'Description', line.name or (line.product_id.name if line.product_id else '-'))
        if line.product_id and line.product_id.barcode:
            sellers_item_id = _cac(item, 'SellersItemIdentification')
            _cbc(sellers_item_id, 'ID', line.product_id.default_code or line.product_id.barcode)

        price = _cac(line_el, 'Price')
        unit_price = line.price_unit if line.quantity == 0 else (line.price_subtotal / line.quantity)
        _cbc(price, 'PriceAmount', '%.2f' % unit_price, currencyID=currency)


def _add_header_tax_total(root, move):
    currency = move.currency_id.name
    tax_total = _cac(root, 'TaxTotal')
    _cbc(tax_total, 'TaxAmount', '%.2f' % move.amount_tax, currencyID=currency)

    groups = {}
    for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
        tax, base, tax_amount = _line_tax_info(move, line)
        key = tax.id if tax else 0
        entry = groups.setdefault(key, {'tax': tax, 'base': 0.0, 'amount': 0.0})
        entry['base'] += base
        entry['amount'] += tax_amount

    for entry in groups.values():
        subtotal = _cac(tax_total, 'TaxSubtotal')
        _cbc(subtotal, 'TaxableAmount', '%.2f' % entry['base'], currencyID=currency)
        _cbc(subtotal, 'TaxAmount', '%.2f' % entry['amount'], currencyID=currency)
        _add_tax_category(subtotal, entry['tax'], percent=entry['tax'].amount if entry['tax'] else 0.0)


def _add_legal_monetary_total(root, move, tag='LegalMonetaryTotal'):
    # Confirmed against SUNAT's real Beta service: Invoice and CreditNote use
    # LegalMonetaryTotal, but DebitNote uses RequestedMonetaryTotal instead.
    currency = move.currency_id.name
    total = _cac(root, tag)
    _cbc(total, 'LineExtensionAmount', '%.2f' % move.amount_untaxed, currencyID=currency)
    _cbc(total, 'TaxInclusiveAmount', '%.2f' % move.amount_total, currencyID=currency)
    _cbc(total, 'PayableAmount', '%.2f' % move.amount_total, currencyID=currency)


def build_invoice_xml(move):
    """Builds a Factura/Boleta (UBL Invoice) document for ``move``."""
    doc_code = move.l10n_latam_document_type_id.code
    root = _root('Invoice', NS)
    _add_ubl_extensions(root)
    _cbc(root, 'UBLVersionID', '2.1')
    _cbc(root, 'CustomizationID', '2.0')
    serie, correlativo = move.l10n_pe_edi_series_number()
    _cbc(root, 'ID', '%s-%s' % (serie, correlativo))
    _cbc(root, 'IssueDate', move.invoice_date.isoformat())
    _cbc(root, 'IssueTime', (move.l10n_pe_edi_issue_time or '00:00:00'))
    _cbc(root, 'InvoiceTypeCode', doc_code, listID='0101',
         listAgencyName='PE:SUNAT', listName='Tipo de Documento',
         listURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01')
    _cbc(root, 'Note', amount_to_words(move.amount_total, move.currency_id.name), languageLocaleID='1000')
    _cbc(root, 'DocumentCurrencyCode', move.currency_id.name)

    _add_signature_block(root, (move.company_id.vat or '').replace('PE', ''), move.company_id.name)
    _add_supplier_party(root, move.company_id)
    _add_customer_party(root, move.partner_id)
    _add_payment_terms(root)
    _add_header_tax_total(root, move)
    _add_legal_monetary_total(root, move)
    _add_lines(root, move, 'InvoiceLine', 'InvoicedQuantity')
    return root


def build_credit_or_debit_note_xml(move):
    """Builds a Nota de Crédito / Nota de Débito (UBL CreditNote/DebitNote)."""
    is_credit = move.l10n_latam_document_type_id.internal_type == 'credit_note'
    nsmap = NS_CREDIT_NOTE if is_credit else NS_DEBIT_NOTE
    root_tag = 'CreditNote' if is_credit else 'DebitNote'
    root = _root(root_tag, nsmap)

    _add_ubl_extensions(root)
    _cbc(root, 'UBLVersionID', '2.1')
    _cbc(root, 'CustomizationID', '2.0')
    serie, correlativo = move.l10n_pe_edi_series_number()
    _cbc(root, 'ID', '%s-%s' % (serie, correlativo))
    _cbc(root, 'IssueDate', move.invoice_date.isoformat())
    _cbc(root, 'IssueTime', (move.l10n_pe_edi_issue_time or '00:00:00'))
    if is_credit:
        # Confirmed against SUNAT's real Beta service: CreditNote expects a
        # CreditNoteTypeCode here, but DebitNote does *not* have an
        # equivalent element in SUNAT's customization — the document type is
        # only carried by the ID prefix / BillingReference for débito notes.
        _cbc(root, 'CreditNoteTypeCode', move.l10n_latam_document_type_id.code, listID='0101',
             listAgencyName='PE:SUNAT', listName='Tipo de Documento',
             listURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01')
    _cbc(root, 'Note', amount_to_words(move.amount_total, move.currency_id.name), languageLocaleID='1000')
    _cbc(root, 'DocumentCurrencyCode', move.currency_id.name)

    origin_move = move.reversed_entry_id or move.debit_origin_id
    origin_serie, origin_correlativo = origin_move.l10n_pe_edi_series_number()
    origin_id = '%s-%s' % (origin_serie, origin_correlativo)

    discrepancy = _cac(root, 'DiscrepancyResponse')
    _cbc(discrepancy, 'ReferenceID', origin_id)
    _cbc(discrepancy, 'ResponseCode', move.l10n_pe_edi_note_reason_code or '01')
    _cbc(discrepancy, 'Description', move.l10n_pe_edi_note_reason_text or move.ref or 'Anulación de la operación')

    billing_ref = _cac(root, 'BillingReference')
    invoice_doc_ref = _cac(billing_ref, 'InvoiceDocumentReference')
    _cbc(invoice_doc_ref, 'ID', origin_id)
    _cbc(invoice_doc_ref, 'DocumentTypeCode', origin_move.l10n_latam_document_type_id.code)

    _add_signature_block(root, (move.company_id.vat or '').replace('PE', ''), move.company_id.name)
    _add_supplier_party(root, move.company_id)
    _add_customer_party(root, move.partner_id)
    _add_header_tax_total(root, move)
    _add_legal_monetary_total(root, move, tag='LegalMonetaryTotal' if is_credit else 'RequestedMonetaryTotal')
    line_tag = 'CreditNoteLine' if is_credit else 'DebitNoteLine'
    quantity_tag = 'CreditedQuantity' if is_credit else 'DebitedQuantity'
    _add_lines(root, move, line_tag, quantity_tag)
    return root


def build_xml_for_move(move):
    internal_type = move.l10n_latam_document_type_id.internal_type
    if internal_type in ('credit_note', 'debit_note'):
        return build_credit_or_debit_note_xml(move)
    return build_invoice_xml(move)
