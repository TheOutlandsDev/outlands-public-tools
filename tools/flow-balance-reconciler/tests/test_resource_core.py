import copy
import unittest
import toolkit as t
import resource_core as c

def resource(): return dict(id='resource-a',capacity=2,capabilities=['move','inspect'],availability=[dict(start=0,end=20)])
def task(): return dict(id='task-a',start=0,end=6,units=1,required_capabilities=['move'])

class Common(unittest.TestCase):
    def test_half_open_interval_bounds(self):
        self.assertEqual(c.interval(0,10),dict(start=0,end=10))
        for a,b in [(0,0),(2,1),(True,2),(-1,2),(0,10**9+1)]:
            with self.assertRaises(t.Rejected): c.interval(a,b)

    def test_resource_normalizes_tags_and_adjacent_intervals(self):
        value=resource(); value['availability']=[dict(start=5,end=10),dict(start=0,end=5)]
        row=c.resource(value)[1]
        self.assertEqual(row['capabilities'],['inspect','move']); self.assertEqual(row['availability'],[dict(start=0,end=10)])

    def test_overlapping_availability_is_refused(self):
        value=resource(); value['availability']=[dict(start=0,end=10),dict(start=5,end=15)]
        with self.assertRaisesRegex(t.Rejected,'AVAILABILITY_OVERLAP'): c.resource(value)

    def test_resource_exact_shape_capacity_and_tags(self):
        for change in ({'capacity':True},{'capacity':0},{'capacity':1000001},{'capabilities':['move','move']},
                       {'id':'UPPER'},{'availability':None},{'extra':0}):
            with self.assertRaises(t.Rejected): c.resource(dict(resource(),**change))

    def test_availability_gap_is_not_covered(self):
        value=resource(); value['availability']=[dict(start=0,end=5),dict(start=7,end=10)]
        row=c.resource(value)[1]; self.assertTrue(c.covered(row,0,5)); self.assertFalse(c.covered(row,4,8))

    def test_empty_availability_and_capabilities_are_explicit(self):
        value=resource(); value.update(availability=[],capabilities=[]); row=c.resource(value)[1]
        self.assertFalse(c.covered(row,0,1)); self.assertEqual(row['capabilities'],[])

    def test_task_exact_types_and_positive_units(self):
        for change in ({'units':True},{'units':0},{'end':0},{'required_capabilities':['move',{}]}):
            with self.assertRaises(t.Rejected): c.task(dict(task(),**change))

    def test_row_duplicates_count_once(self):
        a=resource(); accepted,counts,issues=c.rows([a,a,a],c.resource,'resources')
        self.assertEqual(len(accepted),1); self.assertFalse(issues)
        self.assertEqual(counts,dict(input_rows=3,accepted_records=1,duplicate_rows=2,conflict_rows=0,rejected_rows=0))

    def test_conflicting_group_withholds_every_member(self):
        a=resource(); accepted,counts,issues=c.rows([a,a,dict(a,capacity=3)],c.resource,'resources')
        self.assertFalse(accepted); self.assertEqual(counts['conflict_rows'],3); self.assertEqual(counts['duplicate_rows'],0)
        self.assertEqual(len(issues),3)

    def test_normalized_equivalent_resources_are_duplicates(self):
        a=resource(); b=copy.deepcopy(a); b['capabilities'].reverse(); b['availability']=[dict(start=0,end=10),dict(start=10,end=20)]
        _,counts,issues=c.rows([a,b],c.resource,'resources'); self.assertFalse(issues); self.assertEqual(counts['duplicate_rows'],1)

    def test_all_rows_accounted(self):
        a=resource(); _,counts,issues=c.rows([a,a,None,{},dict(a,id='other'),dict(a,id='other',capacity=3)],c.resource,'resources')
        self.assertEqual(counts,dict(input_rows=6,accepted_records=1,duplicate_rows=1,conflict_rows=2,rejected_rows=2))
        self.assertEqual(len(issues),4)

    def test_lists_and_resource_limits(self):
        for value in ([resource()]*1001,None,{}):
            with self.assertRaises(t.Rejected): c.rows(value,c.resource,'resources')
        for change in ({'capabilities':['cap'+str(i) for i in range(33)]},{'availability':[dict(start=i*2,end=i*2+1) for i in range(33)]}):
            with self.assertRaises(t.Rejected): c.resource(dict(resource(),**change))

    def test_resource_pin_is_order_invariant(self):
        a=resource(); b=dict(resource(),id='other')
        self.assertEqual(c.resource_pin(c.rows([a,b],c.resource,'resources')[0]),c.resource_pin(c.rows([b,a],c.resource,'resources')[0]))

    def test_fixed_diagnostics_do_not_echo_values(self):
        _,_,issues=c.rows([dict(resource(),id='SYNTHETIC_SENTINEL')],c.resource,'resources')
        self.assertEqual(issues,[dict(side='resources',row=1,code='IDENTIFIER_INVALID')])
