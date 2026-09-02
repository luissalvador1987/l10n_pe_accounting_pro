{
    'name': "Perú - Facturación Electrónica SUNAT desde el Punto de Venta",
    'summary': "Emite Boleta o Factura Electrónica SUNAT automáticamente al cobrar en el POS, "
               "reutilizando la conexión directa de pe_edi_sunat.",
    'description': """
Extiende ``pe_edi_sunat`` para que cada venta del Punto de Venta quede, sin pasos manuales, con un
comprobante electrónico válido ante SUNAT — tal como exige la normativa peruana (toda venta necesita
Boleta o Factura, no solo las facturadas a pedido del cliente):

* Al cerrar/cobrar una orden de POS en una compañía con país fiscal Perú, el módulo fuerza la creación
  de la factura interna de Odoo (``account.move``) que el propio POS ya sabe generar, eligiendo
  automáticamente **Boleta** (cliente sin RUC, incluido "sin cliente" usando un cliente genérico
  configurable) o **Factura** (cliente con RUC) y el diario/serie SUNAT correcto para cada caso.
* Reutiliza al 100% el motor de firma y envío ya probado en vivo de ``pe_edi_sunat``
  (``_l10n_pe_edi_generate_and_sign`` / ``_l10n_pe_edi_send``): ningún código de firma o SOAP nuevo,
  un solo camino de envío a SUNAT para todo Odoo, facturado desde back-office o desde el POS.
* Envío automático a SUNAT apenas se cobra el ticket (configurable por Punto de Venta). Si SUNAT o
  Internet no responden en ese momento —algo real en un local con caja rápida—, el error se registra
  en el log técnico de ``pe_edi_sunat`` y la venta **no se bloquea ni se pierde**: queda en estado
  "Por enviar" con un botón "Reintentar envío SUNAT" en la orden para reenviarla apenas se resuelva.
* Cliente genérico configurable por Punto de Venta para Boletas cuando el comprador no se identifica
  (uso habitual y válido ante SUNAT para Boleta de venta al público).
* Código QR y número de serie-correlativo SUNAT en el ticket impreso del POS, en el mismo punto de
  extensión que usa Odoo para otras localizaciones fiscales (``pos-receipt-order-data``), una vez que
  SUNAT aceptó el comprobante.
* Botón de reintento y estado SUNAT visibles directamente en el formulario de la orden de POS, sin
  tener que ir a Contabilidad a buscar la factura generada.

Configuración: Punto de Venta > Configuración > (sección "Facturación Electrónica SUNAT", visible solo
si la compañía tiene Perú como país fiscal) — diario para Boleta, diario para Factura, cliente genérico
y si el envío a SUNAT debe hacerse automáticamente.

Honestidad técnica: este módulo no reemplaza ni duplica la lógica de firma/SOAP de ``pe_edi_sunat``, y
tampoco implementa el Resumen Diario de Boletas (igual que su dependencia, cada Boleta se envía
individualmente a SUNAT, 100% válido y sin la complejidad adicional de un resumen agrupado). El envío
a SUNAT ocurre de forma síncrona en el mismo request que cierra la venta (igual que "Facturar" en el
POS estándar de Odoo); en una conexión muy lenta esto puede demorar unos segundos el cierre del ticket.
    """,
    'version': '18.0.1.0.0',
    'author': "Designweblp",
    'maintainer': "Designweblp",
    'category': 'Accounting/Localizations',
    'website': "https://github.com/luissalvador1987/l10n_pe_accounting_pro",
    'support': "luissalvador1987@gmail.com",
    'license': 'OPL-1',
    'price': 100.0,
    'currency': 'USD',
    'images': ['static/description/banner.png'],
    'depends': ['point_of_sale', 'pe_edi_sunat'],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pe_pos_edi_sunat/static/src/js/**/*',
            'pe_pos_edi_sunat/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
