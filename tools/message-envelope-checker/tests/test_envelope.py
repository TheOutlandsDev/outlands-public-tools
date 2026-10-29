import copy
import json
from pathlib import Path
import unittest
import envelope
from message_core import address
import toolkit as t


class Envelopes(unittest.TestCase):
    def setUp(self):
        self.value=json.loads((Path(__file__).absolute().parents[1]/'examples/envelope.json').read_text(encoding='utf-8'))

    def call(self,values=False):
        return envelope.check(t.encode(self.value),values)

    def refused(self,code=None):
        with self.assertRaises(t.Rejected) as caught: self.call()
        if code: self.assertEqual(str(caught.exception),code)

    def test_fictional_summary(self):
        result=self.call(); self.assertEqual(result['recipient_counts'],dict(to=1,cc=0,bcc=0))
        self.assertEqual(result['declared_attachment_bytes'],7)
        self.assertFalse(result['attachment_bytes_verified'])
        self.assertFalse(result['address_deliverability_verified'])

    def test_default_omits_addresses_names_subject_headers(self):
        self.value['bcc']=['hidden@example.invalid']
        result=self.call(); encoded=json.dumps(result)
        for value in ('hidden@','reviewer@','sample.txt','Fictional review','X-Category'):
            self.assertNotIn(value,encoded)
        self.assertEqual(result['recipient_counts']['bcc'],1)

    def test_opt_in_values_include_normalized_domain(self):
        self.value['sender']='Robot@EXAMPLE.INVALID'
        self.assertEqual(self.call(True)['values']['sender'],'Robot@example.invalid')

    def test_header_injection_all_address_fields(self):
        for field in ('sender','reply_to','to','cc','bcc'):
            original=copy.deepcopy(self.value)
            self.value[field]=['user@example.invalid\r\nBcc: x@example.invalid'] if field in ('to','cc','bcc') else 'user@example.invalid\r\nBcc: x@example.invalid'
            with self.subTest(field=field): self.refused()
            self.value=original

    def test_subject_and_extension_header_controls(self):
        self.value['subject']='sample\nBcc: other@example.invalid'; self.refused('TEXT_CONTROL_FORBIDDEN')
        self.value['subject']='sample'; self.value['headers']['X-Category']='sample\r\nextra'; self.refused()

    def test_only_declared_extension_headers(self):
        for key in ('Authorization','Bcc','Received','x-category','Content-Type'):
            self.value['headers']={key:'sample'}
            with self.subTest(key=key): self.refused('HEADER_FORBIDDEN')

    def test_display_name_comments_groups_quoted_and_idn_refused(self):
        for value in ('Sample <a@example.invalid>','a(comment)@example.invalid','Group:a@example.invalid;','"a b"@example.invalid','a@café.invalid','a@[127.0.0.1]','a@localhost','a..b@example.invalid'):
            self.value['sender']=value
            with self.subTest(value=value): self.refused()

    def test_domain_syntax_and_local_dots(self):
        for value in ('.a@example.invalid','a.@example.invalid'):
            with self.subTest(value=value),self.assertRaises(t.Rejected): address(value)
        for domain in ('-example.invalid','example-.invalid','example.12','ex_ample.invalid','a'*64+'.invalid'):
            with self.subTest(domain=domain),self.assertRaises(t.Rejected): address('a@'+domain)

    def test_duplicate_across_groups_case_insensitive(self):
        self.value['bcc']=['REVIEWER@EXAMPLE.INVALID']; self.refused('DUPLICATE_RECIPIENT')

    def test_no_recipient(self):
        self.value['to']=[]; self.refused('RECIPIENT_LIMIT')

    def test_per_group_and_total_recipient_limits(self):
        self.value['to']=[f'r{i}@example.invalid' for i in range(33)]; self.refused()
        for index,key in enumerate(('to','cc','bcc')):
            self.value[key]=[f'r{index}_{i}@example.invalid' for i in range(22)]
        self.refused('RECIPIENT_LIMIT')

    def test_attachment_traversal_reserved_and_alias_names(self):
        for name in ('../file.txt','a/b.txt','a\\b.txt','CON.txt','LPT1.txt','a.txt.','a:secret','a..txt'):
            self.value['attachments'][0]['name']=name
            with self.subTest(name=name): self.refused('FILENAME_INVALID')

    def test_duplicate_attachment_name(self):
        second=copy.deepcopy(self.value['attachments'][0]); second['name']='SAMPLE.TXT'
        self.value['attachments'].append(second); self.refused('DUPLICATE_ATTACHMENT')

    def test_attachment_size_integer_and_hash(self):
        for value in (True,-1,16*1024*1024+1):
            self.value['attachments'][0]['bytes']=value; self.refused('INTEGER_INVALID')
        self.value['attachments'][0]['bytes']=7; self.value['attachments'][0]['sha256']='bad'; self.refused('HASH_INVALID')

    def test_attachment_total_and_count_limits(self):
        sample=self.value['attachments'][0]
        self.value['attachments']=[dict(sample,name=f'sample{i}.txt',bytes=16*1024*1024) for i in range(3)]
        self.refused('ATTACHMENT_TOTAL_LIMIT')
        self.value['attachments']=[dict(sample,name=f'sample{i}.txt') for i in range(17)]; self.refused('ATTACHMENT_LIMIT')

    def test_unsupported_attachment_type(self):
        self.value['attachments'][0]['media_type']='text/html'; self.refused('MEDIA_TYPE_INVALID')

    def test_empty_attachments_and_reply_address(self):
        self.value['attachments']=[]; self.value['reply_to']='reply@example.invalid'
        self.assertEqual(self.call()['attachment_count'],0)

    def test_unknown_field_and_invalid_format(self):
        self.value['format']='other'; self.refused('ENVELOPE_FORMAT_INVALID')
        self.value['format']='outlands-message-envelope-v1'; self.value['path']='sample'; self.refused('FIELDS_INVALID')

    def test_invalid_include_values(self):
        with self.assertRaises(t.Rejected): self.call(1)

    def test_deterministic_immutable_and_exact_pin(self):
        before=copy.deepcopy(self.value); result=self.call()
        self.assertEqual(result,self.call()); self.assertEqual(self.value,before)
        self.assertEqual(result['input_sha256'],t.digest(t.encode(self.value)))
