"""Check declared message envelopes. No attachment reads or address lookups."""
import toolkit as t
from message_core import text, address, filename


def check(raw, include_values=False):
    t.require(type(include_values) is bool, 'OPTION_INVALID')
    value = t.decode(raw)
    t.fields(value, {'format','sender','to','cc','bcc','reply_to','subject','headers','attachments'})
    t.require(value['format'] == 'outlands-message-envelope-v1', 'ENVELOPE_FORMAT_INVALID')
    sender = address(value['sender'])
    reply = None if value['reply_to'] is None else address(value['reply_to'])
    groups, seen = {}, set()
    for kind in ('to','cc','bcc'):
        items = value[kind]
        t.require(type(items) is list and len(items) <= 32, 'RECIPIENT_LIMIT')
        groups[kind] = []
        for item in items:
            normalized = address(item)
            t.require(normalized.casefold() not in seen, 'DUPLICATE_RECIPIENT')
            seen.add(normalized.casefold()); groups[kind].append(normalized)
    t.require(1 <= len(seen) <= 64, 'RECIPIENT_LIMIT')
    subject = text(value['subject'], 160)
    t.require(bool(subject.strip()), 'SUBJECT_EMPTY')
    headers = value['headers']
    t.require(type(headers) is dict and set(headers) <= {'X-Reference','X-Category'}, 'HEADER_FORBIDDEN')
    for header in headers.values():
        t.require(bool(text(header, 160).strip()), 'HEADER_EMPTY')
    attachments, names, total = value['attachments'], set(), 0
    t.require(type(attachments) is list and len(attachments) <= 16, 'ATTACHMENT_LIMIT')
    for item in attachments:
        t.fields(item, {'name','media_type','bytes','sha256'})
        name = filename(item['name'])
        t.require(name.casefold() not in names, 'DUPLICATE_ATTACHMENT')
        names.add(name.casefold())
        t.require(item['media_type'] in ('text/plain','text/csv','application/json','application/pdf','application/octet-stream'), 'MEDIA_TYPE_INVALID')
        total += t.integer(item['bytes'], 16 * 1024 * 1024)
        t.sha(item['sha256'])
    t.require(total <= 32 * 1024 * 1024, 'ATTACHMENT_TOTAL_LIMIT')
    result = {'status':'PASS','format':'outlands-envelope-review-v1','input_sha256':t.digest(raw),
              'recipient_counts':{k:len(v) for k,v in groups.items()},'attachment_count':len(attachments),
              'declared_attachment_bytes':total, 'attachment_bytes_verified':False,
              'address_deliverability_verified':False, 'network_used':False}
    if include_values:
        result['values'] = dict(sender=sender, reply_to=reply, subject=subject, headers=headers,
                                attachments=attachments, **groups)
    return result


def main(argv=None):
    p = t.Parser(description='Check declared envelopes; default report omits addresses and names.')
    p.add_argument('--input', required=True)
    p.add_argument('--include-values', action='store_true')
    p.add_argument('--out')
    return t.run(p, lambda a: check(t.read(a.input), a.include_values), argv)


if __name__ == '__main__':
    raise SystemExit(main())
