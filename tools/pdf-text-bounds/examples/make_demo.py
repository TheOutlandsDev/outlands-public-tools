"""Generate original tiny PDF fixtures. No document library or real content needed."""
from pathlib import Path
import argparse
import io
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pdf_bounds as bounds


def make_pdf(*, text='Fictional inside', x=20, y=50, size=12, pages=1,
             media=(0, 0, 200, 100), crop=None, rotation=0, empty=False):
    """Small authored PDF 1.4 using a standard Base14 Helvetica font."""
    if not text.isascii():
        raise ValueError('Fixture text must be ASCII')
    literal = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    content = b'' if empty else f'BT /F1 {size} Tf {x} {y} Td ({literal}) Tj ET\n'.encode('ascii')
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids = []
    box = ' '.join(map(str, media))
    crop_text = '' if crop is None else ' /CropBox [' + ' '.join(map(str, crop)) + ']'
    for _index in range(pages):
        page_id = len(objects) + 1; stream_id = page_id + 1; kids.append(page_id)
        objects.append((f'<< /Type /Page /Parent 2 0 R /MediaBox [{box}]{crop_text} /Rotate {rotation}'
                        f' /Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>').encode('ascii'))
        objects.append(f'<< /Length {len(content)} >>\nstream\n'.encode('ascii') + content + b'endstream')
    objects[1] = ('<< /Type /Pages /Kids [' + ' '.join(f'{n} 0 R' for n in kids) + f'] /Count {pages} >>').encode('ascii')
    output = io.BytesIO(); output.write(b'%PDF-1.4\n% Original fictional fixture\n'); offsets = [0]
    for index, value in enumerate(objects, 1):
        offsets.append(output.tell()); output.write(f'{index} 0 obj\n'.encode('ascii') + value + b'\nendobj\n')
    start = output.tell(); output.write(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode('ascii'))
    for offset in offsets[1:]:
        output.write(f'{offset:010d} 00000 n \n'.encode('ascii'))
    output.write(f'trailer\n<< /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{start}\n%%EOF\n'.encode('ascii'))
    return output.getvalue()


def create(destination):
    target = bounds.local_path(destination)
    bounds.no_links(target.parent)
    bounds.require(not target.exists() and not target.is_symlink(), 'OUTPUT_EXISTS')
    fixtures = {'inside.pdf': make_pdf(), 'outside.pdf': make_pdf(text='EDGE', x=198),
                'rotated.pdf': make_pdf(text='Fictional rotated', rotation=90),
                'crop.pdf': make_pdf(text='Crop edge', x=5, crop=(20, 10, 180, 90)),
                'nonzero-origin.pdf': make_pdf(text='Offset box', x=30, y=70, media=(10, 20, 210, 120)),
                'empty.pdf': make_pdf(empty=True)}
    target.mkdir(mode=0o700, exist_ok=False)
    for name, data in fixtures.items():
        bounds.exclusive_write(target / name, data)
    return {'status': 'FICTIONAL_PDFS_CREATED', 'files': sorted(fixtures),
            'contains_real_documents': False, 'outside_and_crop_are_intentional_negative_fixtures': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    try:
        print(json.dumps(create(parser.parse_args().destination), sort_keys=True))
    except (bounds.BoundsError, OSError, ValueError):
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'FRESH_TRUSTED_DESTINATION_REQUIRED'}))
        raise SystemExit(2)
