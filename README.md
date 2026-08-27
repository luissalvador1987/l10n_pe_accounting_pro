# Contabilidad Perú Avanzada (SUNAT Pro) — Odoo 18

Módulos de localización peruana para **Odoo 18.0** (Community o Enterprise):

| Módulo | Descripción | Licencia |
|---|---|---|
| [`l10n_pe_accounting_pro`](./l10n_pe_accounting_pro) | Contabilidad avanzada: PLE, detracciones, retenciones/percepciones de IGV, activos fijos con depreciación dual NIIF/SUNAT, cierre contable asistido, estados financieros NIIF y ayuda de exportación PLAME/T-Registro. | OPL-1 (de pago) |
| [`pe_edi_sunat`](./pe_edi_sunat) | Facturación electrónica peruana con conexión directa a SUNAT (sin OSE/PSE): firma digital, envío SOAP, CDR, QR/RIDE y Guías de Remisión Electrónica. | LGPL-3 (gratuito) |

`l10n_pe_accounting_pro` **depende de** `pe_edi_sunat` — instala ambos módulos para que todo funcione.

## Requisitos

- Odoo **18.0** (probado sobre Community).
- Localización `l10n_pe` (incluida de fábrica en Odoo).
- Librerías Python para `pe_edi_sunat`: `cryptography`, `pyOpenSSL`, `lxml`, `qrcode` (ya vienen con la instalación estándar de Odoo).

## Instalación

1. Copia ambas carpetas de módulo (`pe_edi_sunat` y `l10n_pe_accounting_pro`) a tu carpeta de `addons` personalizada.
2. Reinicia el servidor de Odoo y actualiza la lista de aplicaciones.
3. Instala primero `pe_edi_sunat` (o deja que se instale automáticamente como dependencia) y luego `l10n_pe_accounting_pro`.
4. Configura tu régimen tributario, agente de retención/percepción y cuentas contables en **Contabilidad Perú > Configuración > Ajustes**.

## ¿Qué incluye `l10n_pe_accounting_pro`?

- **PLE** (Registro de Compras / Registro de Ventas e Ingresos): se genera solo al contabilizar cada comprobante, exportable al formato TXT clásico.
- **Detracciones (SPOT)**: catálogo de bienes/servicios (Anexos 1/2/3), cálculo automático, control de la constancia de depósito.
- **Retenciones y Percepciones de IGV**: emitidas y sufridas, con comprobantes numerados y asientos conciliados automáticamente.
- **Activos fijos con depreciación dual NIIF/SUNAT**: cronograma contable y tributario en paralelo, con impuesto a la renta diferido calculado.
- **Cierre contable asistido**: provisión de CTS/gratificaciones/vacaciones, ajuste por diferencia de cambio.
- **Estados Financieros NIIF**: Situación Financiera, Resultados, y una versión base de Flujo de Efectivo y Cambios en el Patrimonio.
- **PLAME/T-Registro**: censo de trabajadores y exportación por periodo.

Ficha completa con capturas: [`l10n_pe_accounting_pro/static/description/index.html`](./l10n_pe_accounting_pro/static/description/index.html)

### Notas importantes de honestidad técnica

- **SIRE**: genera el TXT clásico de PLE como respaldo interno; no se conecta al API de SIRE (que SUNAT usa desde 2024 para la mayoría de contribuyentes).
- **DAOT**: no se incluye — fue derogada desde el ejercicio 2018.
- **PLAME**: verifica la estructura vigente publicada por SUNAT/MTPE antes de usar el archivo exportado en producción.
- Los porcentajes de detracción/retención/percepción deben verificarse contra la norma vigente para tu caso.

## ¿Qué incluye `pe_edi_sunat`?

- Configuración y validación de certificado digital (.pfx/.p12).
- Generación de XML UBL 2.1 firmado (XMLDSig, RSA-SHA256, C14N).
- Envío SOAP a `billService` (Factura/Boleta/Notas) con usuario y clave SOL.
- Recepción de la CDR, QR y RIDE en PDF.
- Guías de Remisión Electrónica (GRE) vía API REST/OAuth2 de SUNAT.

El flujo de Factura/Boleta/Notas fue probado contra el ambiente Beta real de SUNAT. El flujo de GRE se construyó siguiendo la documentación pública pero no se probó en vivo por falta de credenciales; confirma la URL vigente en el Manual del Programador antes de usarlo en Producción.

## Licencia

- `l10n_pe_accounting_pro` — [Odoo Proprietary License v1.0 (OPL-1)](./l10n_pe_accounting_pro/LICENSE). Requiere una licencia válida para su uso (ver [Odoo Apps](https://apps.odoo.com)).
- `pe_edi_sunat` — [LGPL-3](./pe_edi_sunat/LICENSE).

## Soporte

luissalvador1987@gmail.com
