import copy
import hashlib
import unittest
import toolkit as t
import temporal_core as c

def obs(period=1,revision=1,available_at=None,value='12',id=None,series='sample'):
    payload=dict(id=id or f'sample-p{period}-v{revision}',series=series,period=period,revision=revision,
                 available_at=period if available_at is None else available_at,value=value)
    return dict(payload,sha256=hashlib.sha256(t.encode(payload)).hexdigest())
def ref(row): return dict(id=row['id'],sha256=row['sha256'])

class Common(unittest.TestCase):
    def test_exact_observation_pin(self):
        source=obs(); key,row=c.observation(source)
        self.assertEqual(key,('sample',1,1)); self.assertEqual(row,source)

    def test_pin_covers_values_and_timing(self):
        for changes in ({'value':'13'},{'available_at':2},{'revision':2},{'id':'changed'}):
            with self.assertRaisesRegex(t.Rejected,'OBSERVATION_PIN_MISMATCH'): c.observation(dict(obs(),**changes))

    def test_decimal_normalization_matches_canonical_pin(self):
        row=obs(value='1'); row['value']='1.00'
        self.assertEqual(c.observation(row)[1]['value'],'1')
        zero=obs(value='0'); zero['value']='-0.00'; self.assertEqual(c.observation(zero)[1]['value'],'0')

    def test_decimal_limits_do_not_depend_on_caller_context(self):
        from decimal import localcontext
        with localcontext() as context:
            context.prec=1
            self.assertEqual(c.decimal('999999999999.123456'),'999999999999.123456')
            with self.assertRaises(t.Rejected): c.decimal('1000000000000.1')
        for value in ('1e2','+1','01',' 1','1.0000001',True,1,'NaN'):
            with self.assertRaises(t.Rejected): c.decimal(value)

    def test_observation_shape_and_exact_types(self):
        for changes in ({'period':True},{'revision':0},{'available_at':0},{'sha256':'A'*64},{'extra':0}):
            with self.assertRaises(t.Rejected): c.observation(dict(obs(),**changes))

    def test_duplicate_rows_count_once(self):
        row=obs(); accepted,counts,issues=c.rows([row,row,row],c.observation,'observations')
        self.assertEqual(len(accepted),1); self.assertFalse(issues)
        self.assertEqual(counts,dict(input_rows=3,accepted_records=1,duplicate_rows=2,conflict_rows=0,rejected_rows=0))

    def test_conflicts_include_all_repeats(self):
        a=obs(); b=obs(value='13'); accepted,counts,issues=c.rows([a,a,b,obs(2)],c.observation,'observations')
        self.assertEqual(len(accepted),1); self.assertEqual(counts['conflict_rows'],3); self.assertEqual(counts['duplicate_rows'],0)
        self.assertEqual(len(issues),3)

    def test_every_row_accounted(self):
        row=obs(); _,counts,issues=c.rows([row,row,None,{},obs(2),obs(2,value='14')],c.observation,'observations')
        self.assertEqual(counts,dict(input_rows=6,accepted_records=1,duplicate_rows=1,conflict_rows=2,rejected_rows=2))
        self.assertEqual(len(issues),4)

    def test_observation_id_alias_blocked(self):
        issues=c.prepare([obs(id='same'),obs(2,id='same')])[3]
        self.assertEqual([i['code'] for i in issues],['OBSERVATION_ID_ALIAS','OBSERVATION_ID_ALIAS'])

    def test_revision_time_ties_and_reversal(self):
        for later,code in [(3,'REVISION_TIME_TIE'),(2,'REVISION_TIME_REVERSED')]:
            issues=c.prepare([obs(1,1,3),obs(1,2,later)])[3]
            self.assertIn(code,[i['code'] for i in issues])

    def test_asof_cutoff_inclusive_and_future_not_selected(self):
        _,periods,_,issues=c.prepare([obs(1,1,1),obs(1,2,3)]); self.assertFalse(issues)
        self.assertEqual(c.latest(periods,'sample',1,2)['revision'],1)
        self.assertEqual(c.latest(periods,'sample',1,3)['revision'],2)
        with self.assertRaises(t.Rejected): c.latest(periods,'sample',1,0)

    def test_grid_alignment_and_bounds(self):
        self.assertEqual(c.grid(dict(start=10,end=16,step=2))[1],4)
        for value in (dict(start=2,end=1,step=1),dict(start=0,end=3,step=2),dict(start=0,end=1,step=0),
                      dict(start=False,end=1,step=1),dict(start=0,end=1000,step=1)):
            with self.assertRaises(t.Rejected): c.grid(value)

    def test_row_limit_and_shape(self):
        for value in ([obs()]*1001,None,{}):
            with self.assertRaises(t.Rejected): c.rows(value,c.observation,'observations')

    def test_reference_exact_fields(self):
        self.assertEqual(c.reference(ref(obs())),ref(obs()))
        for value in ({},dict(ref(obs()),extra=0),dict(id=True,sha256='0'*64)):
            with self.assertRaises(t.Rejected): c.reference(value)

    def test_fixed_diagnostics_omit_supplied_values(self):
        _,_,issues=c.rows([dict(obs(),id='SYNTHETIC_SENTINEL')],c.observation,'observations')
        self.assertEqual(issues,[dict(side='observations',row=1,code='IDENTIFIER_INVALID')])

    def test_public_reference_omits_value(self):
        self.assertNotIn('value',c.public_reference(obs()))
