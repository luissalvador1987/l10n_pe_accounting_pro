{
    'name': "Perú - Facturación Electrónica SUNAT (Conexión Directa)",
    'summary': "Facturación electrónica peruana con conexión directa a SUNAT: firma digital, envío SOAP, "
               "CDR, QR/RIDE y Guías de Remisión Electrónica (GRE).",
    'description': """
Emite Facturas, Boletas, Notas de Crédito y Notas de Débito electrónicas y las envía directamente a los
servicios web de SUNAT (billService), sin depender de un OSE/PSE intermediario. Incluye:

* Configuración del certificado digital (.pfx/.p12): carga, validación de vigencia y datos del titular.
* Generación de XML UBL 2.1 firmado digitalmente (XMLDSig, RSA-SHA256, C14N) según el formato de SUNAT.
* Envío por SOAP a billService (Factura/Boleta/Notas) con usuario y clave SOL (WS-Security).
* Recepción y almacenamiento de la CDR (Constancia de Recepción), con estado de aceptación/rechazo.
* Código QR y representación impresa (RIDE) en PDF.
* Guías de Remisión Electrónica (GRE) vía la API REST/OAuth2 de SUNAT.
* Registro técnico (log) de cada comunicación con SUNAT para trazabilidad y soporte.

Boletas se envían individualmente (misma vía que Factura), lo cual es 100% válido ante SUNAT y evita la
complejidad adicional del Resumen Diario; por eso el Resumen Diario de Boletas y la Comunicación de Baja
NO están incluidos en esta versión (para anular un comprobante ya aceptado, emite una Nota de Crédito).

Requiere las librerías Python cryptography, pyOpenSSL, lxml y qrcode (incluidas de fábrica en Odoo).

Importante: el flujo de Factura/Boleta/Notas fue probado en vivo contra el ambiente Beta real de SUNAT
(firma, envío SOAP y CDR de aceptación confirmados). El flujo de Guías de Remisión (GRE) está construido
siguiendo la documentación pública de SUNAT pero no pudo probarse en vivo por falta de credenciales
Client ID/Secret; confirma con el Manual del Programador vigente la URL exacta de envío antes de usarlo
en Producción.
    """,
    'version': '18.0.1.0.0',
    'author': "Designweblp",
    'maintainer': "Designweblp",
    'category': 'Accounting/Localizations',
     'support': "luissalvador1987@gmail.com",
    'license': 'OPL-1',
    'price': 100.0,
    'currency': 'EUR',
    'depends': ['l10n_pe', 'l10n_latam_invoice_document', 'account_debit_note', 'account', 'mail'],
    'external_dependencies': {
        'python': ['cryptography', 'OpenSSL', 'lxml', 'qrcode'],
    },
    'data': [
        'security/pe_edi_groups.xml',
        'security/ir.model.access.csv',
        'views/pe_edi_certificate_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/pe_edi_despatch_views.xml',
        'views/pe_edi_log_views.xml',
        'views/pe_edi_menus.xml',
        'report/pe_edi_invoice_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
