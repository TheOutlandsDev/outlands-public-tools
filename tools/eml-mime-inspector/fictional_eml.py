"""Create a fixed invented message outside source, new-file-only. No mailbox access."""
import base64
import toolkit as t


def sample():
    lines = ['From: robot@example.invalid','To: reviewer@example.invalid','Subject: Fictional sample',
             'MIME-Version: 1.0','Content-Type: multipart/mixed; boundary="fictional_boundary"','',
             '--fictional_boundary','Content-Type: text/plain; charset=utf-8',
             'Content-Transfer-Encoding: base64','',base64.b64encode(b'Invented notice.\n').decode('ascii'),
             '--fictional_boundary','Content-Type: application/octet-stream',
             'Content-Disposition: attachment; filename="sample.txt"',
             'Content-Transfer-Encoding: base64','',base64.b64encode(b'sample\n').decode('ascii'),
             '--fictional_boundary--','']
    return '\r\n'.join(lines).encode('ascii')


def main(argv=None):
    p = t.Parser(description='Create a fixed invented CRLF EML using a new external path.')
    p.add_argument('--out', required=True)
    def operation(a):
        t.write_new(a.out,sample())
        a.out = None
        return dict(status='PASS', fictional_message_written=True)
    return t.run(p, operation, argv)


if __name__ == '__main__':
    raise SystemExit(main())
