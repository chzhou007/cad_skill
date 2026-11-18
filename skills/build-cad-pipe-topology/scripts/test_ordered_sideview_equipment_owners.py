import copy,unittest
from ordered_sideview_equipment_owners import solve_order

def fixture(reverse=False):
    # First two pairs both project into the second body; 3 independently proved
    # later owners fix the full 5-by-5 row without using nearest-body costs.
    sign=-1 if reverse else 1
    pairs=[dict(pair_id='P'+str(i),station=sign*x,misleading_nearest_owner='EQ1'if i<2 else'EQ'+str(i),DN=80)for i,x in enumerate([1400,1900,4400,6900,9400])]
    bodies=[dict(equipment_id='EQ'+str(i),station=sign*x,DN=250)for i,x in enumerate([0,2500,5000,7500,10000])]
    return pairs,bodies,{'P2':'EQ2','P3':'EQ3','P4':'EQ4'}
class Tests(unittest.TestCase):
    def test_complete_row_resolves_colliding_projections_and_retains_fixed_owners(self):
        for reverse in(False,True):
            args=fixture(reverse);before=copy.deepcopy(args);r=solve_order(*args)
            self.assertEqual(r['mapping'],{'P'+str(i):'EQ'+str(i)for i in range(5)});self.assertEqual(args,before);self.assertFalse(r['DN_used']);self.assertFalse(r['nearest_body_used']);self.assertFalse(r['equipment_label_numbers_used'])
    def test_missing_or_extra_pair_or_body_does_not_manufacture_a_match(self):
        for kind in('pair','body','extra'):
            a=fixture()
            if kind=='pair':a[0].pop(0)
            if kind=='body':a[1].pop(0)
            if kind=='extra':a[0].append(dict(pair_id='EXTRA',station=99999))
            with self.assertRaises(ValueError):solve_order(*a)
    def test_independent_order_conflict_is_preserved_instead_of_remapping_control(self):
        a=fixture();a[2]['P2']='EQ3';a[2]['P3']='EQ2'
        with self.assertRaisesRegex(ValueError,'contradicts'):solve_order(*a)
    def test_duplicate_stations_or_identifiers_and_insufficient_controls_fail(self):
        for kind in('station','id','control','minimum'):
            a=fixture()
            if kind=='station':a[0][0]['station']=a[0][1]['station']
            if kind=='id':a[1][0]['equipment_id']=a[1][1]['equipment_id']
            if kind=='control':a[2].pop('P2')
            with self.assertRaises(ValueError):solve_order(*a,minimum_controls=True if kind=='minimum'else 3)
    def test_input_iteration_and_label_number_order_cannot_choose_owner(self):
        a=fixture();a[0].reverse();a[1].reverse();a[0][0]['DN']=0
        self.assertEqual(solve_order(*a)['mapping']['P0'],'EQ0')
if __name__=='__main__':unittest.main()
