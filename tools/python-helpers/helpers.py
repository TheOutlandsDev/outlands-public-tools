"""Small JSON and structured redaction helpers. No arbitrary command runner."""
from __future__ import annotations
import json
from pathlib import Path

SENSITIVE_KEYS=frozenset({'password','api_key','authorization','secret','token',
                          'access_token','refresh_token','secret_key','private_key'})

class HelperError(ValueError):pass

def load_json_object(path, max_bytes=1024*1024):
    """Load one bounded UTF-8 JSON object. Error messages omit paths and values.

    The caller selects a trusted input. This is not a filesystem sandbox.
    """
    if type(max_bytes) is not int or not 0<max_bytes<=16*1024*1024:raise HelperError('INVALID_LIMIT')
    try:
        with Path(path).open('rb') as handle:data=handle.read(max_bytes+1)
        if len(data)>max_bytes:raise HelperError('INPUT_TOO_LARGE')
        result=json.loads(data.decode('utf-8-sig'),parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        if not isinstance(result,dict):raise HelperError('OBJECT_REQUIRED')
        return result
    except (OSError,UnicodeError,ValueError,RecursionError):
        raise HelperError('JSON_OBJECT_LOAD_FAILED') from None

def redact_structure(value, *, max_depth=32):
    """Copy JSON-like data and redact values under selected sensitive keys.

    Case and dash/underscore variants are normalized. Text inside ordinary
    fields, unknown key names and identifying metadata are not anonymized.
    """
    if type(max_depth) is not int or not 1<=max_depth<=128:raise HelperError('INVALID_DEPTH')
    def visit(item,depth):
        if depth>max_depth:raise HelperError('DEPTH_LIMIT')
        if isinstance(item,dict):
            result={}
            for key,entry in item.items():
                if not isinstance(key,str):raise HelperError('STRING_KEYS_REQUIRED')
                result[key]='<redacted>' if key.casefold().replace('-','_') in SENSITIVE_KEYS else visit(entry,depth+1)
            return result
        if isinstance(item,list):return [visit(entry,depth+1) for entry in item]
        if item is None or type(item) in (str,int,float,bool):return item
        raise HelperError('JSON_TYPES_REQUIRED')
    return visit(value,0)
