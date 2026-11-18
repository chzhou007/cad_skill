import copy, unittest
from dataclasses import dataclass
from native_named_axis_columns import resolve
from native_axis_riser_DN_scopes import project
from test_native_axis_riser_DN_scopes import fixture

@dataclass
class Leg:
    system:str
    vent_port:tuple
    junction:tuple

class NamedColumnTests(unittest.TestCase):
    def fixture(self):
        doc,g,ev,_,p=fixture();contracts=project(doc,g,ev,p['corridors'],'S','G')[3];rows=[]
        for i,c in enumerate(contracts):
            x=0 if c['system']=='supply'else 40
            rows.append(dict(status='source_witnessed',text_handle='NAME'+str(i),identifier=c['corridor_id'],system=c['system'],role='axis_source_line',native_evidence=dict(leader=dict(target_point=[x,15,0]),target=dict(source_line_handle=c['through_source_LINE']))))
        names=dict(family='axis',source_sha256='S',graph_sha256='G',records=rows)
        return doc,g,contracts,names
    def read(self,doc,g,c,n,legs=()):return resolve(doc,g,c,n,legs,'S','G')
    def test_exact_direct_LINE_both_services_without_any_vent_leg(self):
        d,g,c,n=self.fixture();before=copy.deepcopy(g);out=self.read(d,g,c,n)
        self.assertEqual(out['counts'],dict(local_axis_names=2,source_checked=2,pending=0,other_roles=0));self.assertEqual(g,before)
        for r in out['records']:
            self.assertEqual(r['basis'],'exact_native_target_LINE_is_checked_through_column');self.assertIsNone(r['inherited_display_leg']);self.assertIsNone(r['physical_length_mm']);self.assertFalse(r['crossview_mapping_confirmed']);self.assertFalse(r['whole_edge_DN_assigned'])
    def test_inherited_display_leg_remains_valid_without_faking_direct_identity(self):
        d,g,c,n=self.fixture();r=n['records'][0];r['role']='axis_source_junction';r['native_evidence']['leader']['target_point']=[0,21,0]
        out=self.read(d,g,c,n,[Leg('supply',(0,22),(0,20))]);self.assertEqual(out['counts']['source_checked'],2)
        self.assertEqual(out['records'][0]['basis'],'inherited_native_display_leg_and_checked_through_column');self.assertIsNotNone(out['records'][0]['inherited_display_leg'])
    def test_wrong_service_direct_identity_or_named_identity_never_maps(self):
        for case in ('service','identity','missing'):
            d,g,c,n=self.fixture();r=n['records'][0]
            if case=='service':r['system']='return'
            elif case=='identity':r['identifier']='other-column'
            else:r['native_evidence']['target']['source_line_handle']='DELETED'
            with self.subTest(case=case):
                out=self.read(d,g,c,n);self.assertEqual(out['counts']['pending'],1);self.assertEqual(out['counts']['source_checked'],1);self.assertEqual(out['crossview_mappings_assigned'],0)
    def test_repeated_names_competing_columns_and_ambiguous_legs_remain_pending(self):
        d,g,c,n=self.fixture();n['records'].append(copy.deepcopy(n['records'][0]));n['records'][-1]['text_handle']='SECOND'
        out=self.read(d,g,c,n);self.assertEqual(out['counts']['source_checked'],1);self.assertEqual(out['counts']['pending'],2)
        d,g,c,n=self.fixture();c.append(copy.deepcopy(c[0]));out=self.read(d,g,c,n);self.assertEqual(out['counts']['pending'],1)
        d,g,c,n=self.fixture();n['records'][0]['role']='axis_source_junction';n['records'][0]['native_evidence']['leader']['target_point']=[0,21,0]
        out=self.read(d,g,c,n,[Leg('supply',(0,22),(0,20))]*2);self.assertEqual(out['counts']['pending'],1)
    def test_external_same_name_keeps_other_role_and_unqualified_labels_stay_visible(self):
        d,g,c,n=self.fixture();r=copy.deepcopy(n['records'][0]);r.update(text_handle='OUT',role='external_axis_port');n['records'].append(r);n['records'].append(dict(status='pending',text_handle='BAD'))
        out=self.read(d,g,c,n);self.assertEqual(out['counts'],dict(local_axis_names=3,source_checked=2,pending=1,other_roles=1));self.assertEqual(out['ignored_roles'][0]['text_handle'],'OUT')
    def test_stale_graph_or_unwitnessed_column_native_geometry_blocks(self):
        d,g,c,n=self.fixture();n['graph_sha256']='OLD'
        with self.assertRaisesRegex(ValueError,'current native axis'):self.read(d,g,c,n)
        d,g,c,n=self.fixture();n['records'][0]['native_evidence']['leader']['target_point']=[5,15,0]
        self.assertEqual(self.read(d,g,c,n)['counts']['pending'],1)

if __name__=='__main__':unittest.main()
