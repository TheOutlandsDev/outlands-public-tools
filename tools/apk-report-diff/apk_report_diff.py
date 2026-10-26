"""Compare selected saved AAPT2 badging declarations; no APK access. Original MIT."""
from __future__ import annotations
import json
import re
from inspection_support import (Parser, TextError, bounded_append, cli_error,
                                finish, source_inputs, source_record, text_lines,
                                write_report)

PACKAGE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+')
LIBRARY = re.compile(r'[A-Za-z0-9_.-]{1,256}')
ATTRIBUTE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)='([^'\\]*)'")
QUOTED = re.compile(r"'([^'\\]*)'")
SDK = {'sdkVersion': 'min_sdk', 'targetSdkVersion': 'target_sdk',
       'maxSdkVersion': 'max_sdk'}
LIBRARIES = {'uses-library': 'required', 'uses-library-not-required': 'optional'}
IGNORED = frozenset({'application', 'launchable-activity', 'uses-permission',
    'uses-permission-sdk-23', 'uses-feature', 'uses-implied-feature', 'permission',
    'supports-screens', 'supports-any-density', 'densities', 'locales', 'native-code',
    'alt-native-code', 'compatible-screens', 'supports-gl-texture', 'feature-group',
    'uses-configuration', 'uses-package', 'package-verifier'})
PACKAGE_IGNORED = frozenset({'platformBuildVersionCode', 'platformBuildVersionName',
                           'compileSdkVersion', 'compileSdkVersionCodename'})
FIELDS = ('version_code', 'version_name', 'min_sdk', 'target_sdk', 'max_sdk')


def attributes(value):
    """A strict quoted-attribute subset; no backslash or quote escape inference."""
    result = {}; position = 0
    while position < len(value):
        match = ATTRIBUTE.match(value, position)
        if not match or match[1] in result or len(match[2]) > 1024:
            return None
        result[match[1]] = match[2]; position = match.end()
        if position == len(value): break
        if value[position] not in ' \t': return None
        while position < len(value) and value[position] in ' \t': position += 1
    return result


def parse(data, source):
    result = {'package': None, 'package_rows': 0, 'package_valid': False,
              'values': {}, 'field_rows': {}, 'held_fields': set(), 'libraries': {},
              'library_order': [], 'held_libraries': set(), 'unknown_rows': 0,
              'ignored_rows': 0, 'issues': []}
    def issue(code, line):
        bounded_append(result['issues'], {'code': code, 'source': source, 'line': line})
    for number, raw in text_lines(data):
        line = raw.strip(' \t')
        if not line: continue
        if ':' not in line:
            result['unknown_rows'] += 1; issue('UNSUPPORTED_ROW', number); continue
        key, value = line.split(':', 1); value = value.strip(' \t')
        if key == 'package':
            result['package_rows'] += 1
            if result['package_rows'] > 1:
                result['package_valid'] = False; issue('AMBIGUOUS_PACKAGE_ROWS', number); continue
            attrs = attributes(value)
            if (attrs is None or not {'name', 'versionCode', 'versionName'} <= attrs.keys()
                    or not PACKAGE.fullmatch(attrs.get('name', '')) or len(attrs.get('name','')) > 256
                    or not re.fullmatch(r'[0-9]{1,20}', attrs.get('versionCode', ''))
                    or set(attrs)-{'name','versionCode','versionName'}-PACKAGE_IGNORED):
                issue('UNSUPPORTED_PACKAGE_ROW', number); continue
            result['package'] = attrs['name']; result['package_valid'] = True
            result['values'].update(version_code=attrs['versionCode'], version_name=attrs['versionName'])
        elif key in SDK:
            field = SDK[key]; result['field_rows'][field] = result['field_rows'].get(field, 0)+1
            match = QUOTED.fullmatch(value)
            if result['field_rows'][field] > 1:
                result['held_fields'].add(field); issue('AMBIGUOUS_SDK_ROWS', number)
            elif not match or not re.fullmatch(r'[0-9]{1,10}', match[1]):
                result['held_fields'].add(field); issue('UNSUPPORTED_SDK_ROW', number)
            else: result['values'][field] = match[1]
        elif key in LIBRARIES:
            match = QUOTED.fullmatch(value)
            if not match or not LIBRARY.fullmatch(match[1]):
                prefix = QUOTED.match(value)
                if prefix and LIBRARY.fullmatch(prefix[1]):
                    name = prefix[1]
                    result['held_libraries'].add(name)
                    if name not in result['libraries']:
                        result['libraries'][name] = None; bounded_append(result['library_order'],name)
                    issue('UNSUPPORTED_KNOWN_LIBRARY_ROW',number); continue
                result['unknown_rows'] += 1; issue('UNSUPPORTED_LIBRARY_ROW', number); continue
            name = match[1]
            if name in result['libraries']:
                result['held_libraries'].add(name); issue('AMBIGUOUS_LIBRARY_ROWS', number)
            else:
                result['libraries'][name] = LIBRARIES[key]
                bounded_append(result['library_order'], name)
        elif key in IGNORED or re.fullmatch(r'application-(?:label|icon)(?:-[A-Za-z0-9_-]+)?', key):
            result['ignored_rows'] += 1
        else:
            result['unknown_rows'] += 1; issue('UNSUPPORTED_ROW', number)
    if result['package_rows'] == 0: issue('MISSING_PACKAGE_ROW', 0)
    return result


def compare(before_data, after_data, details=False):
    before = parse(before_data, 'before'); after = parse(after_data, 'after')
    report = {'schema_version': 1, 'tool': 'APK Metadata Report Diff',
        'scope': 'Selected saved AAPT2 badging text subset; no APK or effective runtime evaluation.',
        'details_included': details,
        'sources': [source_record('before',before_data), source_record('after',after_data)],
        'summaries': {}, 'package_identity': 'unresolved', 'changes': [],
        'held_comparisons': [], 'findings': [], 'coverage_issues': []}
    for label, parsed in [('before',before), ('after',after)]:
        report['summaries'][label] = {'package_rows': parsed['package_rows'],
            'supported_library_identities': len(parsed['libraries']),
            'unidentified_rows': parsed['unknown_rows'], 'ignored_rows': parsed['ignored_rows']}
        for row in parsed['issues']: bounded_append(report['coverage_issues'],row)
    def hold(entity, reason, field=None):
        row = {'entity_id':entity, 'reason':reason}
        if field is not None: row['field'] = field
        bounded_append(report['held_comparisons'], row)
    if not all(p['package_valid'] and p['package_rows']==1 for p in (before,after)):
        hold('package-0001', 'PACKAGE_IDENTITY_UNRESOLVED')
        return finish(report)
    same_package = before['package']==after['package']
    report['package_identity'] = 'same_declared_name' if same_package else 'different_declared_names'
    if details: report['declared_packages'] = {'before':before['package'], 'after':after['package']}
    if not same_package:
        report['findings'].append({'code':'PACKAGE_IDENTITY_CHANGED'})
        hold('package-0001', 'DIFFERENT_PACKAGES_NOT_COMPARED')
        return finish(report)
    def change(entity, field, old, new, identity=None):
        row = {'entity_id': entity, 'field':field, 'before_present':old is not None,
               'after_present':new is not None}
        if details:
            row.update(before=old, after=new)
            if identity is not None: row['declared_identity'] = identity
        bounded_append(report['changes'], row)
    for field in FIELDS:
        if field in before['held_fields'] or field in after['held_fields']:
            hold('package-0001','UNSUPPORTED_OR_AMBIGUOUS_FIELD',field); continue
        old = before['values'].get(field); new = after['values'].get(field)
        if (old is None and before['unknown_rows']) or (new is None and after['unknown_rows']):
            hold('package-0001','UNIDENTIFIED_OPPOSITE_ROWS',field); continue
        if old != new: change('package-0001',field,old,new)
    names = sorted(before['libraries'].keys() | after['libraries'].keys())
    stable_order = True
    for index, name in enumerate(names,1):
        entity = f'library-{index:04d}'
        if name in before['held_libraries'] or name in after['held_libraries']:
            hold(entity,'AMBIGUOUS_LIBRARY_IDENTITY'); stable_order=False; continue
        old = before['libraries'].get(name); new = after['libraries'].get(name)
        if (old is None and before['unknown_rows']) or (new is None and after['unknown_rows']):
            hold(entity,'UNIDENTIFIED_OPPOSITE_ROWS'); stable_order=False; continue
        if old != new: change(entity,'declared_requirement',old,new,name)
    # Relative order of common identities is an observation only, not a resolver.
    common = before['libraries'].keys() & after['libraries'].keys()
    old_order = [name for name in before['library_order'] if name in common]
    new_order = [name for name in after['library_order'] if name in common]
    if before['unknown_rows'] or after['unknown_rows'] or not stable_order:
        hold('library-order','INCOMPLETE_OR_AMBIGUOUS_LIBRARY_ORDER')
    elif old_order != new_order:
        change('library-order','relative_common_order',old_order,new_order)
    if report['changes']: report['findings'].append({'code':'DECLARED_METADATA_CHANGED'})
    return finish(report)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--before',required=True); parser.add_argument('--after',required=True)
    parser.add_argument('--output',required=True); parser.add_argument('--include-details',action='store_true')
    try:
        args = parser.parse_args(argv)
        inputs = source_inputs([args.before,args.after])
        report = compare(inputs[0][1],inputs[1][1],args.include_details)
        write_report(report,args.output,[args.before,args.after])
        print(json.dumps({'status':report['status'], 'changes':len(report['changes']),
            'held_comparisons':len(report['held_comparisons']),
            'coverage_issues':len(report['coverage_issues'])},sort_keys=True))
        return int(report['status']!='NO_SCOPE_FINDINGS')
    except (TextError,OSError,ValueError,RecursionError) as error: return cli_error(error)


if __name__=='__main__': raise SystemExit(main())
