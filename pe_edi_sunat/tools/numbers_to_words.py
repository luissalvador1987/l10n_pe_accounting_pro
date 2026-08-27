# -*- coding: utf-8 -*-
"""Spanish number-to-words for the mandatory 'SON ... SOLES' note SUNAT
requires on Peruvian invoices. Supports amounts up to 999,999,999.99.
"""

_UNITS = ['', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
_TEENS = ['DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISEIS', 'DIECISIETE',
          'DIECIOCHO', 'DIECINUEVE']
_TENS = ['', '', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
_HUNDREDS = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS',
             'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']

CURRENCY_NAMES = {
    'PEN': 'SOLES',
    'USD': 'DOLARES AMERICANOS',
    'EUR': 'EUROS',
}


def _three_digits_to_words(n):
    if n == 0:
        return ''
    if n == 100:
        return 'CIEN'
    hundred, rest = divmod(n, 100)
    words = []
    if hundred:
        words.append(_HUNDREDS[hundred])
    if rest:
        if rest < 10:
            words.append(_UNITS[rest])
        elif rest < 20:
            words.append(_TEENS[rest - 10])
        else:
            ten, unit = divmod(rest, 10)
            if ten == 2 and unit:
                words.append('VEINTI' + _UNITS[unit])
            else:
                tens_word = _TENS[ten]
                if unit:
                    words.append('%s Y %s' % (tens_word, _UNITS[unit]))
                else:
                    words.append(tens_word)
    return ' '.join(words)


def _integer_to_words(n):
    if n == 0:
        return 'CERO'
    parts = []
    millions, remainder = divmod(n, 1_000_000)
    thousands, units = divmod(remainder, 1000)

    if millions:
        if millions == 1:
            parts.append('UN MILLON')
        else:
            parts.append('%s MILLONES' % _three_digits_to_words(millions))
    if thousands:
        if thousands == 1:
            parts.append('MIL')
        else:
            parts.append('%s MIL' % _three_digits_to_words(thousands))
    if units:
        parts.append(_three_digits_to_words(units))
    return ' '.join(p for p in parts if p)


def amount_to_words(amount, currency_code='PEN'):
    """e.g. amount_to_words(200) -> 'SON DOSCIENTOS CON 00/100 SOLES'"""
    amount = round(float(amount or 0), 2)
    integer_part = int(amount)
    cents = round((amount - integer_part) * 100)
    if cents == 100:  # floating point edge case
        integer_part += 1
        cents = 0
    currency_name = CURRENCY_NAMES.get(currency_code, currency_code)
    return 'SON %s CON %02d/100 %s' % (_integer_to_words(integer_part), cents, currency_name)
