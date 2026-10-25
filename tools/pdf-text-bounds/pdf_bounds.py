"""Inspect supported text geometry in trusted local PDFs; never render or edit them."""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import logging
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading
import unicodedata
from importlib.metadata import version, PackageNotFoundError

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 500
MAX_CHARS = 500_000
MAX_FINDINGS = 5_000
MAX_WORKER_BYTES = 4 * 1024 * 1024
MAX_STDERR_BYTES = 65_536
MAX_REPORT_BYTES = 8 * 1024 * 1024
PINS = {'pdfplumber': '0.11.10', 'pdfminer.six': '20260107', 'Pillow': '13.0.0',
        'pypdfium2': '5.14.0', 'cryptography': '50.0.2', 'charset-normalizer': '3.5.2',
        'cffi': '2.1.1', 'pycparser': '3.12'}


class BoundsError(Exception):
    """A fixed code; no upstream exception or input-derived message."""


def require(condition, code):
    if not condition:
        raise BoundsError(code)


def options(box='media', tolerance=1.0, max_pages=100, max_chars=100_000, timeout=20.0):
    require(type(box) is str and box in ('media', 'crop'), 'INVALID_BOX')
    require(type(tolerance) in (float, int) and math.isfinite(tolerance) and 0 <= tolerance <= 72,
            'INVALID_TOLERANCE')
    require(type(max_pages) is int and 1 <= max_pages <= MAX_PAGES, 'INVALID_PAGE_LIMIT')
    require(type(max_chars) is int and 1 <= max_chars <= MAX_CHARS, 'INVALID_CHARACTER_LIMIT')
    require(type(timeout) in (float, int) and math.isfinite(timeout) and 0.1 <= timeout <= 120,
            'INVALID_TIMEOUT')
    return {'box': box, 'tolerance': float(tolerance), 'max_pages': max_pages,
            'max_chars': max_chars, 'timeout': float(timeout)}


def local_path(value):
    raw = str(value)
    path = Path(value)
    require(path.is_absolute() and '..' not in path.parts and not raw.startswith(('\\\\', '//')),
            'LOCAL_ABSOLUTE_PATH_REQUIRED')
    require(not any(unicodedata.category(c).startswith('C') for c in raw), 'INVALID_LOCAL_PATH')
    if os.name == 'nt':
        require(':' not in raw[2:], 'DEVICE_OR_STREAM_PATH_REJECTED')
    return path


def is_link(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def no_links(path):
    for item in reversed((path, *path.parents)):
        require(not is_link(item.lstat()), 'LINKED_PATH_REJECTED')


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_snapshot(value):
    path = local_path(value)
    require(path.suffix.lower() == '.pdf', 'PDF_EXTENSION_REQUIRED')
    no_links(path)
    expected = path.lstat()
    require(stat.S_ISREG(expected.st_mode), 'REGULAR_INPUT_REQUIRED')
    require(0 < expected.st_size <= MAX_BYTES, 'INPUT_BYTE_LIMIT')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and not is_link(before), 'REGULAR_INPUT_REQUIRED')
        require(identity(expected) == identity(before), 'INPUT_CHANGED')
        data = bytearray()
        while True:
            block = os.read(fd, min(65_536, MAX_BYTES + 1 - len(data)))
            if not block:
                break
            data.extend(block)
            require(len(data) <= MAX_BYTES, 'INPUT_BYTE_LIMIT')
        after = os.fstat(fd)
        require(len(data) == before.st_size and identity(before) == identity(after)
                and before.st_ctime_ns == after.st_ctime_ns
                and identity(after) == identity(path.lstat()), 'INPUT_CHANGED')
        return bytes(data)
    finally:
        os.close(fd)


def dependency_versions():
    try:
        installed = {name: version(name) for name in PINS}
    except PackageNotFoundError:
        raise BoundsError('DEPENDENCIES_REQUIRED') from None
    require(installed == PINS, 'DEPENDENCY_VERSION_MISMATCH')
    return installed


def rect(value, *, allow_zero=False):
    require(isinstance(value, (tuple, list)) and len(value) == 4, 'UNSUPPORTED_GEOMETRY')
    require(all(type(n) in (int, float) and math.isfinite(n) and abs(n) <= 1_000_000_000 for n in value),
            'UNSUPPORTED_GEOMETRY')
    result = tuple(float(n) for n in value)
    require((result[0] <= result[2] and result[1] <= result[3]) if allow_zero else
            (result[0] < result[2] and result[1] < result[3]), 'UNSUPPORTED_GEOMETRY')
    return result


def inspect_snapshot(data, selected):
    """Trusted-byte worker core. Use inspect() for the public process/time boundary."""
    require(type(data) is bytes and 0 < len(data) <= MAX_BYTES, 'INPUT_BYTE_LIMIT')
    require(data.startswith(b'%PDF-') and data.rstrip().endswith(b'%%EOF'), 'UNSUPPORTED_PDF_ENVELOPE')
    selected = options(**selected)
    libraries = dependency_versions()
    import pdfplumber
    from pdfplumber.page import Page
    from pdfplumber.utils.exceptions import PdfminerException
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfdocument import PDFPasswordIncorrect
    pages, findings, count, empty_pages = [], [], 0, 0
    # Manage the external byte stream and each Page ourselves. The pinned PDF.close
    # implementation rebuilds its eager .pages list, which would defeat page caps.
    with io.BytesIO(data) as stream:
        try:
            document = pdfplumber.open(stream, password='', strict_metadata=True)
        except PDFPasswordIncorrect:
            raise BoundsError('ENCRYPTED_PDF_UNSUPPORTED') from None
        except PdfminerException as error:
            if error.args and isinstance(error.args[0], PDFPasswordIncorrect):
                raise BoundsError('ENCRYPTED_PDF_UNSUPPORTED') from None
            raise BoundsError('PDF_PARSE_OR_GEOMETRY_ERROR') from None
        require(not document.doc.encryption, 'ENCRYPTED_PDF_UNSUPPORTED')
        # Avoid PDF.pages, which eagerly materializes every page before a cap.
        for number, page_object in enumerate(PDFPage.create_pages(document.doc), 1):
            require(number <= selected['max_pages'], 'PAGE_LIMIT')
            page = Page(document, page_object, page_number=number)
            try:
                require(type(page.rotation) is int and page.rotation in (0, 90, 180, 270), 'UNSUPPORTED_ROTATION')
                media = rect(page.mediabox)
                crop = rect(page.cropbox)
                effective_crop = rect((max(media[0], crop[0]), max(media[1], crop[1]),
                                       min(media[2], crop[2]), min(media[3], crop[3])))
                boundary = media if selected['box'] == 'media' else effective_crop
                # Do not crop Page before reading chars: cropping clips boxes and
                # could erase the very out-of-bounds evidence being inspected.
                chars = page.chars
                require(type(chars) is list and count + len(chars) <= selected['max_chars'], 'CHARACTER_LIMIT')
                page_findings = 0
                for index, char in enumerate(chars, 1):
                    bounds = rect([char.get(k) for k in ('x0', 'top', 'x1', 'bottom')], allow_zero=True)
                    tolerance = selected['tolerance']
                    sides = [side for side, outside in (
                        ('left', bounds[0] < boundary[0] - tolerance),
                        ('top', bounds[1] < boundary[1] - tolerance),
                        ('right', bounds[2] > boundary[2] + tolerance),
                        ('bottom', bounds[3] > boundary[3] + tolerance)) if outside]
                    if sides:
                        require(len(findings) < MAX_FINDINGS, 'FINDING_LIMIT')
                        findings.append({'page': number, 'character_index': index,
                                         'bbox': list(bounds), 'outside': sides})
                        page_findings += 1
                count += len(chars)
                empty_pages += not chars
                pages.append({'page': number, 'rotation': page.rotation, 'media_box': list(media),
                              'declared_crop_box': list(crop), 'effective_crop_box': list(effective_crop),
                              'selected_boundary': list(boundary), 'characters_observed': len(chars),
                              'outside_characters': page_findings})
            finally:
                page.close()
    require(pages, 'NO_PAGES')
    coverage = ['PAGES_WITH_NO_TEXT_OBSERVED'] if empty_pages else []
    status = 'BOUNDS_FINDINGS' if findings else 'REVIEW_REQUIRED' if coverage else 'NO_GEOMETRY_FINDINGS'
    return {'schema_version': 1, 'tool': 'pdf-text-bounds', 'status': status,
            'pdf_sha256': hashlib.sha256(data).hexdigest(), 'pdf_bytes': len(data),
            'coordinate_space': 'pdfplumber_rotated_x0_top_x1_bottom',
            'box': selected['box'], 'tolerance_points': selected['tolerance'],
            'page_count': len(pages), 'characters_observed': count,
            'outside_characters': len(findings), 'pages_without_text': empty_pages,
            'coverage_issues': coverage, 'pages': pages, 'findings': findings,
            'libraries': libraries, 'limits': {'max_pages': selected['max_pages'],
            'max_chars': selected['max_chars'], 'max_findings': MAX_FINDINGS, 'max_pdf_bytes': MAX_BYTES},
            'interpretation': 'Observed text geometry only. No text content, images, shapes, fonts, clipping paths, render quality, malware status or printing correctness was validated.'}


def _worker_guard(event, args):
    if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn')) or event in (
            'os.system', 'os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.chmod', 'os.utime'):
        raise PermissionError('worker operation refused')
    if event == 'open':
        mode, flags = args[1], args[2]
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            raise PermissionError('worker write refused')


def worker(args):
    logging.disable(logging.CRITICAL)
    try:
        require(len(args) == 5, 'WORKER_PROTOCOL')
        selected = options(args[0], float(args[1]), int(args[2]), int(args[3]), float(args[4]))
        data = sys.stdin.buffer.read(MAX_BYTES + 1)
        sys.addaudithook(_worker_guard)
        response = {'report': inspect_snapshot(data, selected)}
    except BoundsError as error:
        response = {'error': str(error)}
    except Exception:
        response = {'error': 'PDF_PARSE_OR_GEOMETRY_ERROR'}
    payload = (json.dumps(response, allow_nan=False, ensure_ascii=True, separators=(',', ':')) + '\n').encode('utf-8')
    if len(payload) > MAX_WORKER_BYTES:
        payload = b'{"error":"WORKER_OUTPUT_LIMIT"}\n'
    sys.stdout.buffer.write(payload)
    return 0


def run_worker(data, selected, *, command=None):
    command = command or [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--_worker',
                          selected['box'], str(selected['tolerance']), str(selected['max_pages']),
                          str(selected['max_chars']), str(selected['timeout'])]
    environment = os.environ.copy()
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=environment, shell=False)
    stdout, stderr, exceeded = bytearray(), bytearray(), threading.Event()
    def read(pipe, target, maximum):
        try:
            while True:
                block = pipe.read(65_536)
                if not block:
                    break
                if len(target) + len(block) > maximum:
                    exceeded.set(); process.kill(); break
                target.extend(block)
        finally:
            pipe.close()
    def write():
        try:
            process.stdin.write(data)
        except (BrokenPipeError, OSError):
            pass
        finally:
            process.stdin.close()
    threads = [threading.Thread(target=read, args=(process.stdout, stdout, MAX_WORKER_BYTES), daemon=True),
               threading.Thread(target=read, args=(process.stderr, stderr, MAX_STDERR_BYTES), daemon=True),
               threading.Thread(target=write, daemon=True)]
    for thread in threads:
        thread.start()
    try:
        process.wait(timeout=selected['timeout'])
    except subprocess.TimeoutExpired:
        process.kill(); process.wait()
        raise BoundsError('WORKER_TIMEOUT') from None
    finally:
        if process.poll() is None:
            process.kill(); process.wait()
        for thread in threads:
            thread.join(timeout=5)
    require(not any(thread.is_alive() for thread in threads), 'WORKER_PIPE_FAILURE')
    require(not exceeded.is_set(), 'WORKER_OUTPUT_LIMIT')
    require(process.returncode == 0 and not stderr, 'WORKER_FAILED')
    try:
        response = json.loads(stdout.decode('utf-8'))
    except (ValueError, UnicodeError):
        raise BoundsError('WORKER_PROTOCOL') from None
    require(type(response) is dict, 'WORKER_PROTOCOL')
    if set(response) == {'error'}:
        require(type(response['error']) is str and response['error'] in {
            'INPUT_BYTE_LIMIT', 'UNSUPPORTED_PDF_ENVELOPE', 'DEPENDENCIES_REQUIRED', 'DEPENDENCY_VERSION_MISMATCH',
            'UNSUPPORTED_GEOMETRY', 'UNSUPPORTED_ROTATION', 'ENCRYPTED_PDF_UNSUPPORTED', 'PAGE_LIMIT',
            'CHARACTER_LIMIT', 'FINDING_LIMIT', 'NO_PAGES', 'PDF_PARSE_OR_GEOMETRY_ERROR', 'WORKER_OUTPUT_LIMIT'}, 'WORKER_PROTOCOL')
        raise BoundsError(response['error'])
    require(set(response) == {'report'} and type(response['report']) is dict
            and response['report'].get('tool') == 'pdf-text-bounds', 'WORKER_PROTOCOL')
    return response['report']


def render_html(report):
    esc = lambda x: html.escape(str(x), quote=True)
    rows = ''.join('<tr><td>' + esc(row['page']) + '</td><td>' + esc(row['character_index'])
                   + '</td><td>' + esc(row['bbox']) + '</td><td>' + esc(', '.join(row['outside']))
                   + '</td></tr>' for row in report['findings'])
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; style-src &apos;unsafe-inline&apos;">'
            '<title>PDF Text Bounds Report</title><style>body{font:16px system-ui;margin:2rem;max-width:80rem}'
            'table{border-collapse:collapse}td,th{border:1px solid #777;padding:.6rem;text-align:left;overflow-wrap:anywhere}</style>'
            '<h1>PDF Text Bounds Report</h1><p>Status: <strong>' + esc(report['status']) + '</strong></p><p>'
            + esc(report['interpretation']) + '</p><p>Selected box: ' + esc(report['box']) + '; tolerance: '
            + esc(report['tolerance_points']) + ' points. Pages: ' + esc(report['page_count'])
            + '; characters: ' + esc(report['characters_observed']) + '; outside: ' + esc(report['outside_characters'])
            + '.</p><p>Coverage issues: ' + esc(', '.join(report['coverage_issues']) or 'none in supported text geometry')
            + '</p><p>No character text, source paths, document metadata or fonts are included.</p>'
            '<table><thead><tr><th>Page</th><th>Character index</th><th>Observed box</th><th>Outside sides</th></tr></thead>'
            '<tbody>' + rows + '</tbody></table></html>\n')


def exclusive_write(path, data):
    no_links(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(data)


def write_report(report, value):
    output = local_path(value)
    no_links(output.parent)
    require(stat.S_ISDIR(output.parent.lstat().st_mode), 'OUTPUT_PARENT_REQUIRED')
    require(not output.exists() and not output.is_symlink(), 'OUTPUT_EXISTS')
    payloads = {'report.json': (json.dumps(report, allow_nan=False, ensure_ascii=True, indent=2) + '\n').encode('utf-8'),
                'report.html': render_html(report).encode('utf-8')}
    require(all(len(data) <= MAX_REPORT_BYTES for data in payloads.values()), 'REPORT_BYTE_LIMIT')
    manifest = {'schema_version': 1, 'files': [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                                             for name, data in sorted(payloads.items())]}
    output.mkdir(mode=0o700, exist_ok=False)
    for name, data in payloads.items():
        exclusive_write(output / name, data)
    exclusive_write(output / 'MANIFEST.json', (json.dumps(manifest, indent=2) + '\n').encode('utf-8'))


def inspect(value, output, **kwargs):
    selected = options(**kwargs)
    data = read_snapshot(value)
    dependency_versions()
    report = run_worker(data, selected)
    require(report.get('pdf_sha256') == hashlib.sha256(data).hexdigest(), 'WORKER_PROTOCOL')
    write_report(report, output)
    return report


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise BoundsError('ARGUMENTS_INVALID')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--pdf', type=Path, required=True)
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--box', default='media')
        parser.add_argument('--tolerance', type=float, default=1.0)
        parser.add_argument('--max-pages', type=int, default=100)
        parser.add_argument('--max-chars', type=int, default=100_000)
        parser.add_argument('--timeout', type=float, default=20.0)
        args = parser.parse_args(argv)
        report = inspect(args.pdf, args.output, box=args.box, tolerance=args.tolerance,
                         max_pages=args.max_pages, max_chars=args.max_chars, timeout=args.timeout)
        print(json.dumps({'status': report['status'], 'page_count': report['page_count'],
                          'characters_observed': report['characters_observed'],
                          'outside_characters': report['outside_characters'],
                          'coverage_issues': report['coverage_issues']}, sort_keys=True))
        return 0 if report['status'] == 'NO_GEOMETRY_FINDINGS' else 1
    except BoundsError as error:
        print(json.dumps({'status': 'INCOMPLETE', 'error': str(error)}, sort_keys=True)); return 2
    except (OSError, ValueError, OverflowError):
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'IO_OR_INPUT_ERROR'}, sort_keys=True)); return 2


if __name__ == '__main__':
    raise SystemExit(worker(sys.argv[2:]) if len(sys.argv) > 1 and sys.argv[1] == '--_worker' else main())
