import unittest
import toolkit as t
import material_core as c

def lot():return dict(id='motor-lot-a',item_id='blower-motor',unit='pieces',quantity=4)
def alias():return dict(id='motor-label',target_id='motor-lot-a')

class Common(unittest.TestCase):
    def test_lot_exact_fields_symbolic_identifiers_and_types(self):
        for update in ({'id':'UPPER'},{'quantity':True},{'quantity':-1},{'quantity':10**12+1},{'unit':{}},{'extra':0}):
            with self.assertRaises(t.Rejected):c.lot(dict(lot(),**update))
        self.assertEqual(c.lot(dict(lot(),quantity=0))[1]['quantity'],0)

    def test_alias_shape_and_target_identifiers(self):
        for value in (None,{},dict(alias(),target_id='../SYNTHETIC_SENTINEL'),dict(alias(),extra=0)):
            with self.assertRaises(t.Rejected):c.alias(value)

    def test_duplicate_snapshot_counts_once(self):
        accepted,counts,issues=c.rows([lot()]*3,c.lot,'lots')
        self.assertEqual(len(accepted),1);self.assertFalse(issues)
        self.assertEqual(counts,dict(input_rows=3,accepted_records=1,duplicate_rows=2,conflict_rows=0,rejected_rows=0))

    def test_conflicts_withhold_all_members(self):
        accepted,counts,issues=c.rows([lot(),lot(),dict(lot(),quantity=5)],c.lot,'lots')
        self.assertFalse(accepted);self.assertEqual(counts['conflict_rows'],3);self.assertEqual(counts['duplicate_rows'],0);self.assertEqual(len(issues),3)

    def test_every_input_row_accounted_for(self):
        _,counts,_=c.rows([lot(),lot(),None,dict(lot(),id='other'),dict(lot(),id='other',quantity=5)],c.lot,'lots')
        self.assertEqual(counts,dict(input_rows=5,accepted_records=1,duplicate_rows=1,conflict_rows=2,rejected_rows=1))

    def test_list_limits(self):
        for value in (None,{},[lot()]*1001):
            with self.assertRaisesRegex(t.Rejected,'ROW_LIMIT'):c.rows(value,c.lot,'lots')

    def test_fixed_diagnostics_omit_rejected_values(self):
        _,_,issues=c.rows([dict(lot(),id='SYNTHETIC_SENTINEL')],c.lot,'lots')
        self.assertEqual(issues,[dict(side='lots',row=1,code='IDENTIFIER_INVALID')])

    def test_empty_missing_collision_and_unit_conflict(self):
        cases=[([],[]),([lot()],[dict(alias(),target_id='missing')]),([lot()],[dict(alias(),id='motor-lot-a')]),
               ([lot(),dict(lot(),id='another',unit='boxes')],[])]
        for lots,aliases in cases:
            a,_,i=c.rows(lots,c.lot,'lots');b,_,j=c.rows(aliases,c.alias,'aliases');i+=j
            self.assertIsNone(c.resolve(a,b,i));self.assertTrue(i)

    def test_shared_target_aliases_do_not_add_inventory(self):
        a=c.rows([lot()],c.lot,'lots')[0];b=c.rows([alias(),dict(alias(),id='another')],c.alias,'aliases')[0]
        issues=[];result=c.resolve(a,b,issues)
        self.assertFalse(issues);self.assertEqual(set(result.values()),{'motor-lot-a'});self.assertEqual(len(result),3)

    def test_topology_diamond_cycle_and_disconnected_nodes(self):
        nodes=['a','b','c','d','unused'];edges=[('a','b'),('a','c'),('b','d'),('c','d')]
        order=c.topology(nodes,edges);self.assertEqual(set(order),set(nodes))
        for a,b in edges:self.assertLess(order.index(a),order.index(b))
        self.assertIsNone(c.topology(nodes,edges+[('d','a')]))

    def test_iterative_thousand_node_chain(self):
        nodes=['node-'+str(i) for i in range(1000)];edges=list(zip(nodes,nodes[1:]))
        self.assertEqual(c.topology(nodes,edges),nodes)

    def test_lot_pin_order_invariance_and_changed_quantity(self):
        a=lot();b=dict(lot(),id='other');aliases=c.rows([alias()],c.alias,'aliases')[0]
        x=c.rows([a,b],c.lot,'lots')[0];y=c.rows([b,a],c.lot,'lots')[0]
        self.assertEqual(c.lot_pin(x,aliases),c.lot_pin(y,aliases))
        z=c.rows([dict(a,quantity=5),b],c.lot,'lots')[0];self.assertNotEqual(c.lot_pin(x,aliases),c.lot_pin(z,aliases))
