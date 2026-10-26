"""Generate tiny fictional, non-bootable v3/v4 metadata fixtures. MIT."""
from __future__ import annotations
import os
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser, TextError, canonical_directory, cli_error, local_path


def boot_fixture(version=4):
    data = bytearray(16384 if version == 4 else 12288)
    data[:8] = b'ANDROID!'
    struct.pack_into('<IIII', data, 8, 11, 7, 0, 1584 if version == 4 else 1580)
    struct.pack_into('<I', data, 40, version)
    data[44:61] = b'fictional-example'
    if version == 4: struct.pack_into('<I', data, 1580, 9)
    data[4096:4107] = b'notakernel!'
    data[8192:8199] = b'notcpio'
    if version == 4: data[12288:12297] = b'unsigned!'
    return bytes(data)


def vendor_fixture(version=4):
    data = bytearray(20480 if version == 4 else 12288)
    data[:8] = b'VNDRBOOT'
    struct.pack_into('<II', data, 8, version, 4096)
    struct.pack_into('<I', data, 24, 12)
    data[28:45] = b'fictional-example'
    data[2080:2087] = b'orchard'
    struct.pack_into('<II', data, 2096, 2128 if version == 4 else 2112, 5)
    data[4096:4108] = b'not-a-ramdsk'
    data[8192:8197] = b'nodtb'
    if version == 4:
        struct.pack_into('<IIII', data, 2112, 216, 2, 108, 6)
        struct.pack_into('<III', data, 12288, 5, 0, 1)
        data[12300:12307] = b'orchard'
        struct.pack_into('<III', data, 12396, 7, 5, 3)
        data[12408:12413] = b'grove'
        data[16384:16390] = b'demo=1'
    return bytes(data)


def generate(value):
    target = local_path(value); parent = canonical_directory(target.parent)
    if target.exists() or target.is_symlink(): raise TextError('OUTPUT_EXISTS')
    target = parent/target.name
    files = {'boot-v3.img': boot_fixture(3), 'boot-v4.img': boot_fixture(4),
             'vendor-v3.img': vendor_fixture(3), 'vendor-v4.img': vendor_fixture(4),
             'truncated-vendor.img': vendor_fixture(4)[:12300]}
    legacy = bytearray(4096); legacy[:8] = b'ANDROID!'; struct.pack_into('<I', legacy, 40, 2)
    files['unsupported-legacy.img'] = bytes(legacy)
    target.mkdir(mode=0o700, exist_ok=False)
    for name, data in files.items():
        fd = os.open(target/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
        with os.fdopen(fd, 'wb') as stream: stream.write(data)
    return len(files)


def main():
    parser = Parser(description=__doc__); parser.add_argument('--output', required=True)
    try:
        args = parser.parse_args(); count = generate(args.output)
        print('Generated fictional metadata fixtures: '+str(count)); return 0
    except (TextError, OSError, ValueError) as error: return cli_error(error)


if __name__ == '__main__': raise SystemExit(main())
