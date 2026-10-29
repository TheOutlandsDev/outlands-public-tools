import copy
import json
from pathlib import Path
import unittest
import render
import toolkit as t


class Rendering(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).absolute().parents[1] / 'examples'
        self.spec = json.loads((root/'template.json').read_text(encoding='utf-8'))
        self.values = json.loads((root/'values.json').read_text(encoding='utf-8'))

    def call(self):
        return render.render(t.encode(self.spec),t.encode(self.values))

    def refused(self,code=None):
        with self.assertRaises(t.Rejected) as caught:
            self.call()
        if code:
            self.assertEqual(str(caught.exception),code)

    def test_exact_fictional_render(self):
        result=self.call()
        self.assertEqual(result['text'],'Fictional review for sample-alpha\nUnits: 7')
        self.assertEqual(result['html'],'<pre>Fictional review for sample-alpha\nUnits: 7</pre>')

    def test_all_markup_in_literal_and_value_escaped(self):
        self.spec['template']='<script>{{record}}</script> & {{units}}'
        self.values['values']['record']='</pre><img src=x onerror="alert(1)">'
        html=self.call()['html']
        self.assertNotIn('<script>',html); self.assertNotIn('<img',html)
        self.assertIn('&lt;/pre&gt;&lt;img',html); self.assertIn('&quot;',html)

    def test_no_recursive_substitution(self):
        self.values['values']['record']='{{units}}'
        self.assertIn('{{units}}',self.call()['text'])

    def test_exact_input_pins(self):
        result=self.call()
        self.assertEqual(result['template_sha256'],t.digest(t.encode(self.spec)))
        self.assertEqual(result['values_sha256'],t.digest(t.encode(self.values)))

    def test_missing_value(self):
        del self.values['values']['units']; self.refused('FIELDS_INVALID')

    def test_extra_value(self):
        self.values['values']['extra']='unused'; self.refused('FIELDS_INVALID')

    def test_duplicate_declaration(self):
        self.spec['variables'].append('record'); self.refused('DUPLICATE_VARIABLE')

    def test_unused_declaration(self):
        self.spec['variables'].append('unused'); self.refused('VARIABLE_DECLARATION_MISMATCH')

    def test_undeclared_placeholder(self):
        self.spec['template']+=' {{missing}}'; self.refused('VARIABLE_DECLARATION_MISMATCH')

    def test_expression_include_attribute_and_malformed_rejected(self):
        for value in ('{{record.upper()}}','{% include file %}','{{record.name}}','{{ record }}','{x}','{{record}'):
            self.spec['template']=value
            with self.subTest(value=value): self.refused('PLACEHOLDER_INVALID')

    def test_empty_template(self):
        self.spec['template']=' \n'; self.refused('TEMPLATE_EMPTY')

    def test_nonstring_values(self):
        for value in (7,True,None,[],{}):
            self.values['values']['units']=value
            with self.subTest(value=value): self.refused('TEXT_INVALID')

    def test_controls_bidi_and_surrogates_refused(self):
        for value in ('a\x00b','a\rb','\u202e','\u0085','\ud800','\u2028'):
            self.values['values']['record']=value
            with self.subTest(value=repr(value)): self.refused()

    def test_unicode_tab_and_newline_preserved(self):
        self.values['values']['record']='Invented café\talpha\nnext'
        self.assertIn('café\talpha\nnext',self.call()['text'])

    def test_value_length_limit(self):
        self.values['values']['units']='x'*2049; self.refused('TEXT_INVALID')

    def test_repetition_limit(self):
        self.spec['template']='{{record}}'*129+'{{units}}'; self.refused('PLACEHOLDER_INVALID')

    def test_rendered_byte_limit(self):
        self.spec['template']='{{record}}'*33+'{{units}}'
        self.values['values']['record']='x'*2048; self.refused('RENDER_LIMIT')

    def test_constant_literal_template(self):
        self.spec.update(template='Invented constant',variables=[]); self.values['values']={}
        self.assertEqual(self.call()['text'],'Invented constant')

    def test_wrong_format_and_unknown_fields(self):
        self.spec['format']='other'; self.refused('TEMPLATE_FORMAT_INVALID')
        self.spec['format']='outlands-message-template-v1'; self.spec['include']='file'; self.refused('FIELDS_INVALID')

    def test_deterministic_without_mutating_inputs(self):
        before=copy.deepcopy((self.spec,self.values)); self.assertEqual(self.call(),self.call())
        self.assertEqual(before,(self.spec,self.values))
