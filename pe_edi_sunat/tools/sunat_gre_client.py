# -*- coding: utf-8 -*-
"""OAuth2 REST client for SUNAT's Guía de Remisión Electrónica (GRE) API.

The token endpoint below was confirmed live (its response carries the
`X-ServiceName: tecnologia-seguridad-controlacceso-clientessol-oauth2`
header, i.e. it really is SUNAT's client-credentials security service). The
GRE *submission* endpoint could not be confirmed the same way from this
environment (it needs a real client_id/secret to exercise meaningfully) —
`res.company.l10n_pe_edi_gre_submission_url` is kept as a configurable field
for exactly that reason; verify it against the current SUNAT manual.
"""
import base64
import logging

import requests

_logger = logging.getLogger(__name__)

TOKEN_URL = "https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"


class SunatGreError(Exception):
    pass


def get_access_token(client_id, client_secret, ruc, sol_user, sol_password, scope=None, timeout=30):
    """client_credentials-style token request against SUNAT's identity
    service, scoped to the GRE API by default."""
    url = TOKEN_URL.format(client_id=client_id)
    data = {
        'grant_type': 'password',
        'scope': scope or 'https://api-cpe.sunat.gob.pe',
        'client_id': client_id,
        'client_secret': client_secret,
        'username': '%s%s' % (ruc, sol_user),
        'password': sol_password,
    }
    try:
        response = requests.post(url, data=data, timeout=timeout,
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'})
    except requests.exceptions.RequestException as e:
        raise SunatGreError("No se pudo conectar con el servicio de autenticación de SUNAT: %s" % e)
    if response.status_code != 200:
        raise SunatGreError("SUNAT rechazó la solicitud de token (HTTP %s): %s" % (
            response.status_code, response.text[:500]))
    try:
        payload = response.json()
    except ValueError:
        raise SunatGreError("Respuesta de token inesperada: %s" % response.text[:500])
    token = payload.get('access_token')
    if not token:
        raise SunatGreError("La respuesta de SUNAT no incluyó un access_token: %s" % payload)
    return token


def send_despatch(submission_url, access_token, ruc, doc_type_code, series, correlativo, zip_bytes, timeout=60):
    """POSTs the signed+zipped DespatchAdvice. Returns the parsed JSON body
    (typically containing a 'ticket' to poll via `get_status`)."""
    url = "%s/%s-%s-%s-%s" % (submission_url.rstrip('/'), ruc, doc_type_code, series, correlativo)
    payload = {'arc': base64.b64encode(zip_bytes).decode()}
    try:
        response = requests.post(url, json=payload, timeout=timeout, headers={
            'Authorization': 'Bearer %s' % access_token, 'Content-Type': 'application/json',
        })
    except requests.exceptions.RequestException as e:
        raise SunatGreError("No se pudo conectar con la API de GRE de SUNAT: %s" % e)
    if response.status_code not in (200, 201, 202):
        raise SunatGreError("SUNAT rechazó el envío de la guía (HTTP %s): %s" % (
            response.status_code, response.text[:1000]))
    try:
        return response.json()
    except ValueError:
        raise SunatGreError("Respuesta inesperada de la API de GRE: %s" % response.text[:500])


def get_status(status_url, access_token, ruc, doc_type_code, series, correlativo, timeout=30):
    url = "%s/%s-%s-%s-%s" % (status_url.rstrip('/'), ruc, doc_type_code, series, correlativo)
    try:
        response = requests.get(url, timeout=timeout, headers={'Authorization': 'Bearer %s' % access_token})
    except requests.exceptions.RequestException as e:
        raise SunatGreError("No se pudo conectar con la API de GRE de SUNAT: %s" % e)
    if response.status_code != 200:
        raise SunatGreError("SUNAT rechazó la consulta de estado (HTTP %s): %s" % (
            response.status_code, response.text[:1000]))
    try:
        return response.json()
    except ValueError:
        raise SunatGreError("Respuesta inesperada de la API de GRE: %s" % response.text[:500])
