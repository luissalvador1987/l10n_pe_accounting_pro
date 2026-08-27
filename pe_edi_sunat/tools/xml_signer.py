# -*- coding: utf-8 -*-
"""Enveloped XML-DSig signing for SUNAT UBL 2.1 documents.

SUNAT expects a `<ds:Signature>` nested inside
`ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent` (not as a plain
child of the document root, unlike a "textbook" enveloped signature), using
RSA-SHA256 and *inclusive* C14N (`REC-xml-c14n-20010315`, not exclusive
c14n). The `<ds:SignedInfo>` is built and canonicalized *in place* inside the
real document tree — not as a standalone fragment — because inclusive C14N
pulls in every namespace declared on its ancestors (cac:, cbc:, sac:, the
default UBL namespace, ...). Canonicalizing a detached copy of SignedInfo
would silently produce different bytes than what a verifier computes from
the embedded node, and the signature would fail SUNAT's validation.
"""
import base64
import hashlib

from lxml import etree
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

DS_NS = "http://www.w3.org/2000/09/xmldsig#"
EXT_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"

C14N_ALGO = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
RSA_SHA256_ALGO = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
SHA256_ALGO = "http://www.w3.org/2001/04/xmlenc#sha256"
ENVELOPED_ALGO = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"


def _c14n(node):
    return etree.tostring(node, method='c14n', exclusive=False, with_comments=False)


def sign_ubl_document(xml_root, private_key, certificate, signature_id="SignSUNAT"):
    """Mutates ``xml_root`` in place, inserting a full ds:Signature inside its
    ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent placeholder
    (which must already exist, empty, in the tree). Returns ``xml_root``.
    """
    ext_content = xml_root.find(
        './/{%s}UBLExtensions/{%s}UBLExtension/{%s}ExtensionContent' % (EXT_NS, EXT_NS, EXT_NS))
    if ext_content is None:
        raise ValueError("El documento no tiene un ext:ExtensionContent donde insertar la firma.")

    # 1. Digest of the whole document *before* the signature exists — this is
    #    exactly what the enveloped-signature transform yields once the
    #    (not-yet-inserted) ds:Signature is stripped back out.
    document_digest = base64.b64encode(hashlib.sha256(_c14n(xml_root)).digest()).decode()

    # 2. Build the ds:Signature skeleton *in place* so SignedInfo inherits the
    #    real ancestor namespace context when canonicalized.
    nsmap = {'ds': DS_NS}
    signature_el = etree.SubElement(ext_content, '{%s}Signature' % DS_NS, nsmap=nsmap)
    signature_el.set('Id', signature_id)

    signed_info_el = etree.SubElement(signature_el, '{%s}SignedInfo' % DS_NS)
    c14n_method = etree.SubElement(signed_info_el, '{%s}CanonicalizationMethod' % DS_NS)
    c14n_method.set('Algorithm', C14N_ALGO)
    sig_method = etree.SubElement(signed_info_el, '{%s}SignatureMethod' % DS_NS)
    sig_method.set('Algorithm', RSA_SHA256_ALGO)

    reference_el = etree.SubElement(signed_info_el, '{%s}Reference' % DS_NS)
    reference_el.set('URI', '')
    transforms_el = etree.SubElement(reference_el, '{%s}Transforms' % DS_NS)
    transform_el = etree.SubElement(transforms_el, '{%s}Transform' % DS_NS)
    transform_el.set('Algorithm', ENVELOPED_ALGO)
    digest_method = etree.SubElement(reference_el, '{%s}DigestMethod' % DS_NS)
    digest_method.set('Algorithm', SHA256_ALGO)
    digest_value_el = etree.SubElement(reference_el, '{%s}DigestValue' % DS_NS)
    digest_value_el.text = document_digest

    # 3. Canonicalize SignedInfo *as embedded* (inherits ancestor namespaces),
    #    then sign those exact bytes.
    signed_info_c14n = _c14n(signed_info_el)
    signature_bytes = private_key.sign(signed_info_c14n, padding.PKCS1v15(), hashes.SHA256())
    signature_value_b64 = base64.b64encode(signature_bytes).decode()

    signature_value_el = etree.SubElement(signature_el, '{%s}SignatureValue' % DS_NS)
    signature_value_el.text = signature_value_b64

    key_info_el = etree.SubElement(signature_el, '{%s}KeyInfo' % DS_NS)
    x509_data_el = etree.SubElement(key_info_el, '{%s}X509Data' % DS_NS)
    x509_cert_el = etree.SubElement(x509_data_el, '{%s}X509Certificate' % DS_NS)
    x509_cert_el.text = base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode()

    return xml_root


def get_signature_digest(xml_root):
    """Return the base64 DigestValue stored under the ds:Signature, used for
    the printed representation / traceability (not required by SUNAT, but a
    useful cross-check field)."""
    node = xml_root.find('.//{%s}DigestValue' % DS_NS)
    return node.text if node is not None else False
