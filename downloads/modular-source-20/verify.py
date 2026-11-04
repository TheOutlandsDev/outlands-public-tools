"""Inspect exact ZIP bytes, fixed archive metadata, and nested source manifests."""
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

from build import DATE, digest, plan


def verify_archive(raw, value):
    if type(raw) is not bytes or len(raw) > 6_000_000:
        raise ValueError('ARCHIVE_SIZE_REFUSED')
    prefix = 'outlands-modular-tools-20-' + value['version'] + '/'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if archive.comment or len(names) != len(set(names)) or len(names) != value['expected_source_files'] + 2:
            raise ValueError('ARCHIVE_MEMBERS_REFUSED')
        files = {}
        for info in archive.infolist():
            name = info.filename
            if (not name.startswith(prefix) or name.endswith('/') or '\\' in name
                    or not name.isascii() or ':' in name
                    or any(part in ('.', '..', '.git', '__pycache__', 'node_modules')
                           for part in PurePosixPath(name).parts)):
                raise ValueError('ARCHIVE_PATH_REFUSED')
            if (info.date_time != DATE or info.compress_type != zipfile.ZIP_STORED
                    or info.create_system != 3 or info.external_attr != 0o100644 << 16
                    or info.extra or info.comment or info.flag_bits):
                raise ValueError('ARCHIVE_METADATA_REFUSED')
            body = archive.read(info)
            if len(body) != info.file_size or len(body) > 100_000:
                raise ValueError('ARCHIVE_FILE_REFUSED')
            files[name[len(prefix):]] = body
        if archive.testzip() is not None:
            raise ValueError('ARCHIVE_CRC_REFUSED')
    manifest = json.loads(files.pop('MANIFEST.json'))
    if (manifest['format'] != 'outlands-modular-source-manifest-v1'
            or manifest['version'] != value['version']
            or manifest['tools'] != [row['id'] for row in value['tools']]
            or set(manifest['files']) != set(files)
            or sum(map(len, files.values())) > 5_000_000):
        raise ValueError('ARCHIVE_MANIFEST_REFUSED')
    for name, pin in manifest['files'].items():
        if pin != {'bytes': len(files[name]), 'sha256': digest(files[name])}:
            raise ValueError('ARCHIVE_PIN_MISMATCH')
    if set(name.split('/')[1] for name in files if name.startswith('tools/')) != {row['id'] for row in value['tools']}:
        raise ValueError('TOOL_SET_REFUSED')
    for row in value['tools']:
        prefix = 'tools/' + row['id'] + '/'
        if prefix + row['entry'] not in files:
            raise ValueError('TOOL_ENTRY_MISSING')
        nested = json.loads(files[prefix + 'SOURCE-MANIFEST.json'])
        expected = {name.removeprefix(prefix) for name in files if name.startswith(prefix)} - {'SOURCE-MANIFEST.json'}
        if nested['format'] != 'outlands-source-pins-v1' or set(nested['files']) != expected:
            raise ValueError('NESTED_MANIFEST_REFUSED')
        for name, pin in nested['files'].items():
            body = files[prefix + name]
            if pin != {'bytes': len(body), 'sha256': digest(body)}:
                raise ValueError('NESTED_PIN_MISMATCH')
    if digest(raw) != value['expected_zip_sha256']:
        raise ValueError('ARCHIVE_REVISION_MISMATCH')
    return {'status': 'PASS', 'sha256': digest(raw), 'tools': len(value['tools']),
            'source_files': value['expected_source_files'], 'archive_members': len(names),
            'fixed_synthetic_zip_metadata': True, 'private_instance_included': False}


def verify(archive_path, checksum_path):
    value = plan()
    archive_path = Path(archive_path)
    checksum_path = Path(checksum_path)
    expected_name = 'outlands-modular-tools-20-' + value['version'] + '.zip'
    if archive_path.name != expected_name or checksum_path.name != 'SHA256SUMS.txt':
        raise ValueError('ASSET_NAME_REFUSED')
    raw = archive_path.read_bytes()
    result = verify_archive(raw, value)
    expected_line = result['sha256'] + '  ' + expected_name + '\n'
    if checksum_path.read_text(encoding='ascii') != expected_line:
        raise ValueError('CHECKSUM_FILE_REFUSED')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--checksums', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.checksums), sort_keys=True))
