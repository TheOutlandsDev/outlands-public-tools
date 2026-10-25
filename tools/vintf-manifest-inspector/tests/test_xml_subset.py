from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from restricted_xml import parse,decode
from inspection_support import TextError


def read(text):return parse(text.encode(),lambda:None)


class XMLSubsetTests(unittest.TestCase):
    def test_balanced_nodes_attributes_and_preorder_positions(self):
        root,positions=read('<r a="one"><child/><other><nested/></other></r>')
        self.assertEqual(root.attrib,{'a':'one'});self.assertEqual([n.tag for n in root.iter()],['r','child','other','nested'])
        self.assertEqual([positions[id(n)] for n in root.iter()],[1,2,3,4])

    def test_quotes_greater_than_and_once_only_reference_decoding(self):
        root,_=read('<r a=\'one &quot; &gt; two\' b="&amp;lt;">&lt;text&gt;<c/>tail&amp;</r>')
        self.assertEqual(root.attrib['a'],'one " > two');self.assertEqual(root.attrib['b'],'&lt;')
        self.assertEqual(root.text,'<text>');self.assertEqual(root.children[0].tail,'tail&')

    def test_numeric_references_and_literal_attribute_whitespace(self):
        root,_=read('<r a="a\tb\nc&#x9;d">&#65;&#x42;&#x1F600;</r>')
        self.assertEqual(root.attrib['a'],'a b c\td');self.assertEqual(root.text,'AB\U0001f600')

    def test_comments_preserve_text_and_tails(self):
        root,_=read('<!-- before --><r>a<!-- ignored -->b<c/>c<!-- ignored -->d</r><!-- after -->')
        self.assertEqual(root.text,'ab');self.assertEqual(root.children[0].tail,'cd')

    def test_xml_declaration_supported_order(self):
        for declaration in ('<?xml version="1.0"?>','<?xml version="1.0" encoding="UTF-8"?>','<?xml version="1.0" standalone="yes"?>','<?xml version="1.0" encoding="UTF-8" standalone="no"?>'):
            self.assertEqual(read(declaration+'<r/>')[0].tag,'r')

    def test_malformed_declarations(self):
        for text in (' <?xml version="1.0"?><r/>','<?XML version="1.0"?><r/>','<?xml encoding="UTF-8" version="1.0"?><r/>','<?xml version="1.1"?><r/>','<?xml version="&#49;.0"?><r/>','<?xml?><r/>','<r/><?xml version="1.0"?>'):
            with self.assertRaises(TextError,msg=text):read(text)

    def test_processing_instructions_are_observed_only(self):
        events=[];root,_=parse(b'<?fiction any data?><r><?other data?></r>',lambda:events.append('observed'))
        self.assertEqual(root.tag,'r');self.assertEqual(events,['observed','observed'])

    def test_duplicate_missing_unquoted_and_unseparated_attributes(self):
        for text in ('<r a="1" a="2"/>','<r a/>','<r a=one/>','<r a="one"b="two"/>','<r a "one"/>','<r a="unterminated/>','<r a="raw<value"/>'):
            with self.assertRaises(TextError,msg=text):read(text)

    def test_unbalanced_multiple_and_malformed_tags(self):
        for text in ('','<a>','<a></b>','<a/><b/>','<a></a></a>','< a/>','<a/ >','<a></a extra>','<a<bad/>','outside<a/>','<a/>outside','&#x20;<a/>','<a/>]]>'):
            with self.assertRaises(TextError,msg=text):read(text)

    def test_declarations_cdata_and_invalid_comments_refused(self):
        for text in ('<!DOCTYPE r><r/>','<!ENTITY x "y"><r/>','<r><![CDATA[x]]></r>','<r><!-- a--b --></r>','<r><!-- trailing- ---></r>','<r><!-- unterminated</r>'):
            with self.assertRaises(TextError,msg=text):read(text)

    def test_unknown_unterminated_surrogate_and_control_references(self):
        for text in ('&unknown;','&amp','&#0;','&#xD800;','&#x110000;','&#13;','&#x202E;','&#x2028;','&#xFFFF;','&#-1;','&#X41;'):
            with self.assertRaises(TextError,msg=text):decode(text)

    def test_text_accumulation_bound_across_comment_fragments(self):
        text='<r>'+('\n'+('a'*100)+'<!-- x -->')*100+'</r>'
        with self.assertRaisesRegex(TextError,'XML_TEXT_LIMIT'):read(text)

    def test_depth_and_element_counts_before_unbounded_tree(self):
        with self.assertRaisesRegex(TextError,'XML_STRUCTURE_LIMIT'):read('<a>'*33+'</a>'*33)
        with self.assertRaisesRegex(TextError,'XML_STRUCTURE_LIMIT'):read('<r>\n'+'\n'.join('<a/>' for _i in range(8001))+'\n</r>')

    def test_attribute_name_and_value_bounds(self):
        with self.assertRaises(TextError):read('<r '+('a'*257)+'="v"/>')
        with self.assertRaisesRegex(TextError,'XML_ATTRIBUTE_LIMIT'):read('<r a="'+('a'*1025)+'"/>')
        with self.assertRaisesRegex(TextError,'XML_ATTRIBUTE_LIMIT'):read('<r '+' '.join(f'a{i}="v"' for i in range(17))+'/>')


if __name__=='__main__':unittest.main()
