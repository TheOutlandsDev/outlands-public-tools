import copy
import unittest
import toolkit as t
import relational_core as c

def col(name='id',type='text',nullable=False): return dict(name=name,type=type,nullable=nullable)
def table(name='items',cols=None,pk=None,fks=None):
    return dict(name=name,columns=cols or [col()],primary_key=['id'] if pk is None else pk,foreign_keys=fks or [])
def fk(name='item_ref',columns=None,target='items',references=None,policy='skip_any'):
    return dict(name=name,columns=columns or ['item_id'],table=target,references=references or ['id'],null_policy=policy)
def dataset():
    return dict(schema=dict(tables=[table(),table('entries',[col('entry_id','integer'),col('item_id',nullable=True)],['entry_id'],[fk()])]),
                tables=[dict(name='items',rows=[['a'],['b']]),dict(name='entries',rows=[[1,'a'],[2,None]])])

class Common(unittest.TestCase):
    def test_schema_valid_foreign_reference(self):
        self.assertEqual(c.schema(dataset()['schema']),dataset()['schema'])

    def test_schema_unknown_fields_and_types(self):
        for changes in ({'extra':0},{'columns':[]},{'columns':[dict(col(),type='real')]},{'columns':[dict(col(),nullable=1)]}):
            value=dict(tables=[dict(table(),**changes)])
            with self.assertRaises(t.Rejected): c.schema(value)

    def test_duplicate_tables_columns_and_constraints(self):
        for kind in ('tables','columns','constraints'):
            value=dataset()['schema']
            if kind=='tables': value['tables']*=2
            elif kind=='columns': value['tables'][0]['columns']*=2
            else: value['tables'][1]['foreign_keys']*=2
            with self.assertRaises(t.Rejected): c.schema(value)

    def test_primary_key_must_exist_be_unique_and_nonnullable(self):
        for pk in (['missing'],['id','id'],[True]):
            with self.assertRaises(t.Rejected): c.schema(dict(tables=[table(pk=pk)]))
        with self.assertRaises(t.Rejected): c.schema(dict(tables=[table(cols=[col(nullable=True)])]))

    def test_foreign_reference_must_bind_exact_primary_key(self):
        for change in ({'table':'missing'},{'references':['other']},{'columns':['missing']},{'null_policy':'guess'}):
            value=dataset()['schema']; value['tables'][1]['foreign_keys'][0].update(change)
            with self.assertRaises(t.Rejected): c.schema(value)

    def test_reference_type_mismatch(self):
        value=dataset()['schema']; value['tables'][1]['columns'][1]['type']='integer'
        with self.assertRaisesRegex(t.Rejected,'REFERENCE_TYPE_MISMATCH'): c.schema(value)

    def test_self_references_and_cycles_are_declarations(self):
        value=dict(tables=[table(cols=[col(),col('parent',nullable=True)],fks=[fk(columns=['parent'])])])
        self.assertEqual(c.schema(value),value)

    def test_scalar_types_refuse_boolean_numeric_coercion(self):
        for value,spec in [(True,col(type='integer')),(1,col(type='boolean')),(1,col(type='decimal')),(False,col())]:
            with self.assertRaises(t.Rejected): c.scalar(value,spec)

    def test_integer_and_decimal_limits(self):
        self.assertEqual(c.scalar(-10**12,col(type='integer')),-10**12)
        self.assertEqual(c.scalar('1000000000000.000000',col(type='decimal')),'1000000000000')
        for value in ('1e3','+1','01','1.0000001','1000000000000.1',' NaN','-1000000000001'):
            with self.assertRaises(t.Rejected): c.scalar(value,col(type='decimal'))
        from decimal import localcontext
        with localcontext() as ctx:
            ctx.prec=1
            self.assertEqual(c.scalar('999999999999.123456',col(type='decimal')),'999999999999.123456')
            with self.assertRaises(t.Rejected): c.scalar('1000000000000.1',col(type='decimal'))

    def test_decimal_normalization_and_exact_typed_keys(self):
        spec=col(type='decimal'); self.assertEqual(c.scalar('-0.00',spec),'0'); self.assertEqual(c.scalar('1.230000',spec),'1.23')
        self.assertEqual(c.key([c.scalar('1.00',spec)],[0]),c.key([c.scalar('1',spec)],[0]))
        self.assertNotEqual(c.key([True],[0]),c.key([1],[0]))

    def test_text_and_null_policy(self):
        self.assertEqual(c.scalar('A\U0001f331\n',col()),'A\U0001f331\n')
        self.assertIsNone(c.scalar(None,col(nullable=True)))
        for value in (None,'x\x00','x\x85','x'*257):
            with self.assertRaises(t.Rejected): c.scalar(value,col())

    def test_rows_are_not_deduplicated(self):
        rows,counts,issues=c.rows([['a'],['a']], [col()],'items')
        self.assertEqual(len(rows),2); self.assertEqual(counts,dict(input_rows=2,accepted_rows=2,rejected_rows=0)); self.assertFalse(issues)

    def test_all_rows_accounted_without_value_echo(self):
        rows,counts,issues=c.rows([['a'],None,[],[1],[None]], [col()],'items')
        self.assertEqual(counts,dict(input_rows=5,accepted_rows=1,rejected_rows=4)); self.assertEqual(len(issues),4)
        self.assertEqual([r['row'] for r in issues],[2,3,4,5])

    def test_dataset_table_coverage(self):
        for mutate in ('missing','duplicate','unknown'):
            value=dataset()
            if mutate=='missing': value['tables'].pop()
            elif mutate=='duplicate': value['tables'][1]=copy.deepcopy(value['tables'][0])
            else: value['tables'][1]['name']='unknown'
            with self.assertRaises(t.Rejected): c.dataset(value)

    def test_global_row_limit(self):
        value=dataset(); value['tables'][0]['rows']=[['a']]*1000; value['tables'][1]['rows']=[[1,'a']]
        with self.assertRaisesRegex(t.Rejected,'TOTAL_ROW_LIMIT'): c.dataset(value)
        with self.assertRaises(t.Rejected): c.rows([['a']]*1001,[col()],'items')

    def test_schema_bounds(self):
        for value in (dict(tables=[]),dict(tables=[table('t'+str(i)) for i in range(9)]),
                      dict(tables=[table(cols=[col('c'+str(i)) for i in range(17)],pk=[])])):
            with self.assertRaises(t.Rejected): c.schema(value)

    def test_empty_tables_preserve_zero_accounting(self):
        value=dataset()
        for row in value['tables']: row['rows']=[]
        _,rows,counts,issues=c.dataset(value)
        self.assertFalse(issues); self.assertEqual(sum(r['input_rows'] for r in counts.values()),0)

    def test_name_lists_refuse_ambiguity(self):
        for value in (None,['a','a'],['a',{}],[],['a','b','c','d','e']):
            with self.assertRaises(t.Rejected): c.names(value)
