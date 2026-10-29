"""Small bounded notification primitives; no network or environment access."""
import re
import unicodedata
import toolkit as t


def text(value, maximum=4096, multiline=False):
    t.require(type(value) is str and len(value) <= maximum, 'TEXT_INVALID')
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise t.Rejected('TEXT_INVALID') from None
    t.require(all((multiline and c in '\n\t') or
                  (unicodedata.category(c)[0] != 'C' and c not in '\u2028\u2029')
                  for c in value), 'TEXT_CONTROL_FORBIDDEN')
    return value


def address(value):
    text(value, 254)
    t.require(value.count('@') == 1, 'ADDRESS_INVALID')
    local, domain = value.split('@')
    t.require(1 <= len(local) <= 64 and re.fullmatch(r'[A-Za-z0-9!#$%&\x27*+/=?^_`{|}~.-]+', local)
              and not local.startswith('.') and not local.endswith('.') and '..' not in local,
              'ADDRESS_INVALID')
    labels = domain.split('.')
    t.require(2 <= len(labels) <= 16 and len(domain) <= 253 and all(
        re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', p) for p in labels)
        and re.fullmatch('[A-Za-z]{2,63}', labels[-1]), 'ADDRESS_INVALID')
    return local + '@' + domain.lower()


def filename(value):
    text(value, 80)
    t.require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', value) and
              '..' not in value and not value.endswith('.') and
              value.split('.')[0].upper() not in {'CON','PRN','AUX','NUL',
                  *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))},
              'FILENAME_INVALID')
    return value
