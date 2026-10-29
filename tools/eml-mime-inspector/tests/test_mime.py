import base64
import unittest
from fictional_eml import sample
from inspect_eml import inspect
import toolkit as t


class Mime(unittest.TestCase):
    def refused(self,raw):
        with self.assertRaises(t.Rejected): inspect(raw)

    def plain(self,body=b'Invented body.\r\n',kind=b'text/plain; charset=utf-8',extra=b''):
        return (b'From: robot@example.invalid\r\nTo: reviewer@example.invalid\r\nSubject: Fictional\r\nMIME-Version: 1.0\r\nContent-Type: '+kind+b'\r\n'+extra+b'\r\n'+body)

    def test_actual_multipart_decoded_hashes(self):
        result=inspect(sample())
        self.assertEqual(len(result['parts']),3); self.assertEqual(result['attachment_count'],1)
        self.assertEqual(result['parts'][2]['sha256'],t.digest(b'sample\n'))
        self.assertEqual(result['parts'][1]['sha256'],t.digest(b'Invented notice.\n'))
        self.assertFalse(result['bodies_rendered']); self.assertFalse(result['files_extracted'])

    def test_default_omits_all_header_body_and_filename_values(self):
        import json
        encoded=json.dumps(inspect(sample()))
        for value in ('robot@','reviewer@','sample.txt','Invented notice','Fictional sample'):
            self.assertNotIn(value,encoded)

    def test_plain_7bit(self):
        result=inspect(self.plain()); self.assertEqual(result['parts'][0]['bytes'],16)

    def test_utf8_base64_text(self):
        raw=self.plain(base64.b64encode('Invented café'.encode())+b'\r\n',extra=b'Content-Transfer-Encoding: base64\r\n')
        self.assertEqual(inspect(raw)['decoded_bytes'],len('Invented café'.encode()))

    def test_html_is_only_hashed_never_rendered(self):
        raw=self.plain(b'<script>alert(1)</script>',kind=b'text/html; charset=utf-8')
        result=inspect(raw); self.assertFalse(result['bodies_rendered'])
        self.assertEqual(result['parts'][0]['media_type'],'text/html')

    def test_crlf_required(self): self.refused(sample().replace(b'\r\n',b'\n'))

    def test_raw_binary_and_nul_refused(self):
        self.refused(self.plain(b'\xff')); self.refused(self.plain(b'\x00'))

    def test_line_and_input_limits(self):
        self.refused(self.plain(b'a'*999)); self.refused(b'a'*(2*1024*1024+1))

    def test_duplicate_singleton_and_mime_headers(self):
        self.refused(sample().replace(b'Subject: Fictional sample',b'Subject: Fictional sample\r\nsUbJeCt: second'))
        self.refused(sample().replace(b'Content-Type: application/octet-stream',b'Content-Type: application/octet-stream\r\nContent-Type: text/plain'))

    def test_malformed_unknown_and_injected_headers(self):
        for extra in (b'Unknown: value\r\n',b'Bad Header: value\r\n',b'Bcc: reviewer@example.invalid\r\n'):
            self.refused(self.plain(extra=extra))

    def test_display_addresses_and_missing_required_header(self):
        self.refused(sample().replace(b'robot@example.invalid',b'Sample <robot@example.invalid>'))
        self.refused(sample().replace(b'MIME-Version: 1.0\r\n',b''))

    def test_mime_defaults_not_guessed(self):
        self.refused(self.plain().replace(b'Content-Type: text/plain; charset=utf-8\r\n',b''))

    def test_nested_message_and_unsupported_media(self):
        self.refused(self.plain(kind=b'message/rfc822')); self.refused(self.plain(kind=b'image/png'))

    def test_quoted_printable_refused(self):
        self.refused(self.plain(extra=b'Content-Transfer-Encoding: quoted-printable\r\n'))

    def test_invalid_noncanonical_base64(self):
        for payload in (b'%%%=',b'YQ===',b'YR==',b'YQ== trailing',b' YQ==',b'YQ==\t'):
            self.refused(self.plain(payload,extra=b'Content-Transfer-Encoding: base64\r\n'))

    def test_charset_and_invalid_utf8(self):
        self.refused(self.plain(kind=b'text/plain; charset=iso-8859-1'))
        self.refused(self.plain(kind=b'text/plain'))
        self.refused(self.plain(b'/w==',extra=b'Content-Transfer-Encoding: base64\r\n'))

    def test_attachment_traversal_and_parameter_ambiguity(self):
        for name in (b'../sample.txt',b'CON.txt',b'a:stream',b'a..txt'):
            self.refused(sample().replace(b'sample.txt',name))
        self.refused(sample().replace(b'filename="sample.txt"',b"filename*=utf-8''sample.txt"))
        self.refused(sample().replace(b'filename="sample.txt"',b'filename="sample.txt"; filename="other.txt"'))

    def test_binary_requires_attachment_and_base64(self):
        self.refused(sample().replace(b'Content-Disposition: attachment; filename="sample.txt"\r\n',b''))
        self.refused(sample().replace(b'Content-Transfer-Encoding: base64',b'Content-Transfer-Encoding: 7bit'))

    def test_boundary_missing_closing_or_invalid(self):
        self.refused(sample().replace(b'--fictional_boundary--',b''))
        self.refused(sample().replace(b'boundary="fictional_boundary"',b'boundary="bad boundary"'))

    def test_nonempty_preamble_and_epilogue(self):
        self.refused(sample().replace(b'\r\n\r\n--fictional_boundary',b'\r\n\r\nHidden preamble\r\n--fictional_boundary',1))
        self.refused(sample()+b'Hidden epilogue\r\n')

    def test_leaf_with_disguised_extra_header(self):
        self.refused(sample().replace(b'Content-Type: application/octet-stream',b'Subject: child\r\nContent-Type: application/octet-stream'))

    def test_depth_limit(self):
        raw=b'Content-Type: text/plain; charset=utf-8\r\n\r\nFictional'
        for index in range(10):
            boundary=f'b{index}'.encode()
            raw=b'Content-Type: multipart/mixed; boundary="'+boundary+b'"\r\n\r\n--'+boundary+b'\r\n'+raw+b'\r\n--'+boundary+b'--\r\n'
        raw=b'From: robot@example.invalid\r\nTo: reviewer@example.invalid\r\nSubject: Fictional\r\nMIME-Version: 1.0\r\n'+raw
        self.refused(raw)

    def test_many_parts_limit(self):
        raw=self.plain(kind=b'multipart/mixed; boundary="b"',body=(b'--b\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nsample\r\n'*17)+b'--b--\r\n')
        self.refused(raw)

    def test_control_in_decoded_body_refused(self):
        raw=self.plain(base64.b64encode(b'a\x00b'),extra=b'Content-Transfer-Encoding: base64\r\n')
        self.refused(raw)

    def test_deterministic_and_exact_source_pin(self):
        result=inspect(sample()); self.assertEqual(result,inspect(sample()))
        self.assertEqual(result['input_sha256'],t.digest(sample()))

    def test_duplicate_attachment_names_case_insensitive(self):
        attachment=(b'--fictional_boundary\r\nContent-Type: application/octet-stream\r\n'
                    b'Content-Disposition: attachment; filename="SAMPLE.TXT"\r\n'
                    b'Content-Transfer-Encoding: base64\r\n\r\nc2FtcGxlCg==\r\n')
        self.refused(sample().replace(b'--fictional_boundary--',attachment+b'--fictional_boundary--'))

    def test_quoted_or_unbalanced_charset_parameters_refused(self):
        for charset in (b'"utf-8"',b'"utf-8',b'utf-8"'):
            self.refused(self.plain(kind=b'text/plain; charset='+charset))

    def test_controls_in_multipart_surroundings_refused(self):
        self.refused(sample()+b'\x0b\r\n')

    def test_total_part_limit_across_separate_branches(self):
        leaf=b'Content-Type: text/plain; charset=utf-8\r\n\r\nFictional\r\n'
        nested=[]
        for index in range(3):
            boundary=f'b{index}'.encode()
            nested.append(b'--root\r\nContent-Type: multipart/mixed; boundary="'+boundary+
                          b'"\r\n\r\n'+(b'--'+boundary+b'\r\n'+leaf)*10+
                          b'--'+boundary+b'--\r\n')
        raw=self.plain(kind=b'multipart/mixed; boundary="root"',body=b''.join(nested)+b'--root--\r\n')
        self.refused(raw)

    def test_unknown_format_parameters_and_header_length_refused(self):
        self.refused(self.plain(kind=b'text/plain; charset=utf-8; format=flowed'))
        folded=b'X-Reference: '+b'a'*900+b'\r\n'+(b' '+b'a'*900+b'\r\n')*10
        self.refused(self.plain(extra=folded))
