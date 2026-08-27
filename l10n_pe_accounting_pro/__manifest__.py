{
    'name': "Perú - Contabilidad Avanzada (SUNAT Pro)",
    'summary': "Contabilidad peruana avanzada: PLE, detracciones, retenciones/percepciones de IGV, "
               "activos fijos con depreciación dual NIIF/SUNAT, cierre contable asistido, "
               "estados financieros NIIF y ayuda de exportación PLAME/T-Registro.",
    'description': """
Contabilidad Avanzada para Perú
================================

Este módulo se apoya en la localización estándar (``l10n_pe``, plan contable PCGE) y en el módulo de
facturación electrónica ya instalado (``pe_edi_sunat``) para agregar todo lo que un estudio contable
peruano necesita día a día y que ni la localización base de Odoo ni la mayoría de módulos de terceros
cubren completo:

* **Registro de Compras y Registro de Ventas e Ingresos (PLE)**: libro auxiliar que se completa solo
  al validar cada factura/boleta de compra o venta, con exportación al formato TXT clásico de PLE
  (delimitado por "|"). Ver la nota importante sobre SIRE más abajo.
* **Detracciones (SPOT)**: catálogo de bienes/servicios sujetos a detracción con sus porcentajes
  (Anexos 1/2/3), cálculo automático sobre el comprobante, registro manual de la constancia de
  depósito y control del importe neto a pagar al proveedor.
* **Retenciones y Percepciones de IGV**: para empresas designadas Agente de Retención (retiene 3% al
  pagarle a sus proveedores) o Agente de Percepción (percibe 0.5%/1%/2% adicional al vender), con
  comprobantes de retención/percepción numerados correlativamente.
* **Activos fijos con depreciación dual NIIF vs. SUNAT**: registro de activos con dos cronogramas
  de depreciación en paralelo -- uno contable (línea recta según la vida útil que definas) y otro
  tributario con las tasas máximas del Art. 22 del Reglamento de la LIR -- calculando automáticamente
  la diferencia temporal (impuesto a la renta diferido) entre ambos.
* **Cierre contable asistido**: asistente de cierre mensual/anual con checklist, provisión de
  CTS/gratificaciones/vacaciones y ajuste por diferencia de cambio de las cuentas en moneda
  extranjera al tipo de cambio de cierre.
* **Estados financieros NIIF**: Estado de Situación Financiera, Estado de Resultados, Estado de
  Flujo de Efectivo (método indirecto) y Estado de Cambios en el Patrimonio, armados sobre los
  grupos de cuentas del PCGE que ya trae ``l10n_pe``.
* **Ayuda de exportación PLAME/T-Registro**: censo básico de trabajadores y agregador de conceptos
  remunerativos por periodo, exportado en la estructura de registro que exige el PDT Planilla
  Electrónica (no reemplaza el PDT, que es un programa aparte de SUNAT/MTPE).

Notas importantes de honestidad técnica (para que sepas exactamente qué automatiza esto y qué no):

* **SIRE**: desde 2024 SUNAT viene migrando el Registro de Ventas e Ingresos (RVIE) y el Registro de
  Compras (RCE) del PLE clásico (archivo TXT que tú generas y guardas) al **SIRE**, un sistema donde
  SUNAT ya pre-completa el registro con la información de tus comprobantes electrónicos y tú solo
  validas/complementas desde el portal o vía su API. Este módulo genera el libro auxiliar y el TXT
  en el formato PLE clásico (útil como respaldo interno, para periodos anteriores a tu fecha de
  obligatoriedad SIRE, o si SUNAT te excluye de SIRE); **no envía nada directamente al API de SIRE**
  — eso requeriría credenciales/certificado adicionales que no se probaron en vivo.
* **DAOT**: la Declaración Anual de Operaciones con Terceros fue **derogada desde el ejercicio 2018**
  (la información ya la tiene SUNAT vía los comprobantes electrónicos y el PLE/SIRE), así que NO se
  incluye como obligación vigente. Si necesitas un reporte anual de operaciones con terceros para
  control interno o auditoría, el Registro de Compras/Ventas de este módulo ya trae los datos para
  armarlo.
* **PLAME**: la estructura exacta del registro cambia de tanto en tanto; confirma la versión vigente
  de la "Estructura de Datos" publicada por SUNAT/MTPE antes de usar el archivo exportado en
  producción.
* **Retenciones/Percepciones**: los porcentajes y exclusiones aplicables (p.ej. quién NO está sujeto)
  siguen reglas específicas de la R.S. 037-2002 y 058-2006/SUNAT; revísalas para tu caso antes de
  activar el cálculo automático en producción.
    """,
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'author': "Designweblp",
    'maintainer': "Designweblp",
    'website': "https://github.com/luissalvador1987/l10n_pe_accounting_pro",
    'support': "luissalvador1987@gmail.com",
    'license': 'OPL-1',
    'price': 100.0,
    'currency': 'EUR',
    'images': ['static/description/banner.png'],
    'depends': ['l10n_pe', 'pe_edi_sunat', 'account', 'mail'],
    'data': [
        'security/l10n_pe_accounting_groups.xml',
        'security/ir.model.access.csv',
        'data/l10n_pe_accounting_detraction_data.xml',
        'data/l10n_pe_accounting_asset_tax_category_data.xml',
        'data/l10n_pe_accounting_financial_report_data.xml',
        'wizards/l10n_pe_accounting_detraction_register_wizard_views.xml',
        'wizards/l10n_pe_accounting_retention_pay_wizard_views.xml',
        'wizards/l10n_pe_accounting_perception_received_wizard_views.xml',
        'wizards/l10n_pe_accounting_ple_export_wizard_views.xml',
        'wizards/l10n_pe_accounting_closing_wizard_views.xml',
        'wizards/l10n_pe_accounting_plame_export_wizard_views.xml',
        'wizards/l10n_pe_accounting_financial_report_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/account_move_views.xml',
        'views/l10n_pe_accounting_detraction_views.xml',
        'views/l10n_pe_accounting_retention_views.xml',
        'views/l10n_pe_accounting_perception_views.xml',
        'views/l10n_pe_accounting_ple_views.xml',
        'views/l10n_pe_accounting_asset_tax_views.xml',
        'views/l10n_pe_accounting_plame_views.xml',
        'views/l10n_pe_accounting_financial_report_views.xml',
        'views/l10n_pe_accounting_menus.xml',
        'report/l10n_pe_accounting_retention_report.xml',
        'report/l10n_pe_accounting_perception_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
