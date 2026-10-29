"""Strict bounded EML subset inspection; never render or extract payloads."""
import base64
import binascii
from email import policy
from email.parser import BytesParser
import re
import toolkit as t
from message_core import address, filename, text

ALLOWED = {'from','to','cc','bcc','reply-to','subject','date','message-id','mime-version',
           'content-type','content-transfer-encoding','content-disposition','content-id',
           'x-reference','x-category'}
CONTENT_TYPE = re.compile(r'(text/(?:plain|html)|application/octet-stream|multipart/(?:mixed|alternative))'
                          r'(?:; (charset)=(utf-8|us-ascii)|; (boundary)="([A-Za-z0-9_-]{1,70})")?', re.I)
DISPOSITION = re.compile(r'attachment; filename="([A-Za-z0-9][A-Za-z0-9_.-]{0,79})"', re.I)


def headers(part, root):
    t.require(not part.defects, 'MIME_DEFECT')
    items = list(part.raw_items())
    t.require(1 <= len(items) <= 64, 'HEADER_LIMIT')
    result = {}
    for name, value in items:
        key = name.lower()
        t.require(key in ALLOWED and key not in result, 'HEADER_UNSUPPORTED_OR_DUPLICATE')
        t.require(root or key in {'content-type','content-transfer-encoding','content-disposition','content-id'}, 'PART_HEADER_FORBIDDEN')
        unfolded = re.sub(r'\r\n[ \t]+', ' ', value)
        t.require(len(unfolded) <= 8192 and all(32 <= ord(c) <= 126 for c in unfolded), 'HEADER_INVALID')
        t.require(not getattr(part[name], 'defects', ()), 'HEADER_DEFECT')
        result[key] = unfolded.strip()
    t.require('content-type' in result, 'CONTENT_TYPE_REQUIRED')
    if root:
        t.require({'from','to','subject','mime-version'} <= set(result) and result['mime-version'] == '1.0', 'MESSAGE_HEADERS_REQUIRED')
        address(result['from'])
        all_recipients = set()
        for kind in ('to','cc','bcc'):
            if kind in result:
                entries = result[kind].split(',')
                t.require(1 <= len(entries) <= 32, 'RECIPIENT_LIMIT')
                for entry in entries:
                    normal = address(entry.strip()).casefold()
                    t.require(normal not in all_recipients, 'DUPLICATE_RECIPIENT')
                    all_recipients.add(normal)
        t.require(len(all_recipients) <= 64 and result['to'], 'RECIPIENT_LIMIT')
        if 'reply-to' in result:
            address(result['reply-to'])
        text(result['subject'], 160)
        t.require(bool(result['subject']), 'SUBJECT_EMPTY')
    return result


def inspect(raw):
    t.require(type(raw) is bytes and 0 < len(raw) <= 2 * 1024 * 1024, 'EML_SIZE_LIMIT')
    t.require(all(x in (9,10,13) or 32 <= x <= 126 for x in raw) and
              b'\n' not in raw.replace(b'\r\n', b'') and b'\r' not in raw.replace(b'\r\n', b''), 'EML_7BIT_CRLF_REQUIRED')
    lines = raw.split(b'\r\n')
    t.require(all(len(line) <= 998 for line in lines), 'EML_LINE_LIMIT')
    t.require(b'\r\n\r\n' in raw and len(raw.split(b'\r\n\r\n',1)[0]) <= 65536, 'HEADER_LIMIT')
    try:
        message = BytesParser(policy=policy.default).parsebytes(raw)
        pending, result, total, names = [(message,0)], [], 0, set()
        while pending:
            part, depth = pending.pop()
            t.require(depth <= 8 and len(result) + len(pending) < 32, 'MIME_STRUCTURE_LIMIT')
            h = headers(part, depth == 0)
            match = CONTENT_TYPE.fullmatch(h['content-type'])
            t.require(match is not None, 'CONTENT_TYPE_UNSUPPORTED')
            media = match[1].lower()
            t.require(media == part.get_content_type(), 'CONTENT_TYPE_AMBIGUOUS')
            row = dict(part=len(result)+1, depth=depth, media_type=media)
            if media.startswith('multipart/'):
                t.require(match[5] is not None and match[2] is None and part.is_multipart() and
                          'content-transfer-encoding' not in h and 'content-disposition' not in h,
                          'MULTIPART_INVALID')
                t.require(not (part.preamble or '').strip() and not (part.epilogue or '').strip(), 'MIME_EXTRA_CONTENT')
                children = part.get_payload()
                t.require(type(children) is list and 1 <= len(children) <= 16, 'MIME_STRUCTURE_LIMIT')
                row['children'] = len(children)
                pending.extend((child,depth+1) for child in reversed(children))
            else:
                t.require(not part.is_multipart() and match[5] is None, 'LEAF_INVALID')
                encoding = h.get('content-transfer-encoding', '7bit').lower()
                t.require(encoding in ('7bit','base64'), 'TRANSFER_ENCODING_UNSUPPORTED')
                payload = part.get_payload(decode=False)
                t.require(type(payload) is str, 'PAYLOAD_INVALID')
                encoded = payload.encode('ascii')
                if encoding == 'base64':
                    compact = encoded.replace(b'\r\n', b'')
                    decoded = base64.b64decode(compact, validate=True)
                    t.require(base64.b64encode(decoded) == compact, 'BASE64_NONCANONICAL')
                else:
                    decoded = encoded
                total += len(decoded)
                t.require(total <= 2 * 1024 * 1024, 'DECODED_LIMIT')
                if 'content-disposition' in h:
                    disposition = DISPOSITION.fullmatch(h['content-disposition'])
                    t.require(disposition is not None, 'DISPOSITION_UNSUPPORTED')
                    name = filename(disposition[1])
                    t.require(name.casefold() not in names, 'DUPLICATE_ATTACHMENT')
                    names.add(name.casefold()); row['attachment'] = True
                else:
                    t.require(media.startswith('text/'), 'ATTACHMENT_DISPOSITION_REQUIRED')
                    row['attachment'] = False
                if media.startswith('text/'):
                    t.require(match[2] is not None, 'CHARSET_REQUIRED')
                    content = decoded.decode(match[3].lower())
                    # Text is inspected only, never HTML-rendered. Normalize CRLF for control checks.
                    text(content.replace('\r\n','\n'), 2 * 1024 * 1024, multiline=True)
                else:
                    t.require(match[2] is None and encoding == 'base64', 'BINARY_BASE64_REQUIRED')
                row.update(bytes=len(decoded), sha256=t.digest(decoded))
            result.append(row)
        return dict(status='PASS', format='outlands-mime-summary-v1', input_sha256=t.digest(raw),
                    parts=result, decoded_bytes=total, attachment_count=len(names),
                    bodies_rendered=False, files_extracted=False, real_delivery_verified=False)
    except t.Rejected:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError, binascii.Error, IndexError):
        raise t.Rejected('MIME_INVALID') from None


def main(argv=None):
    p = t.Parser(description='Inspect the strict CRLF/7-bit MIME subset; never render bodies.')
    p.add_argument('--input', required=True)
    p.add_argument('--out')
    return t.run(p, lambda a: inspect(t.read(a.input, 2 * 1024 * 1024)), argv)


if __name__ == '__main__':
    raise SystemExit(main())
