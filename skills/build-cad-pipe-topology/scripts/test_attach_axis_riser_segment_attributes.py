import copy,unittest
from test_native_axis_riser_DN_scopes import fixture
from native_axis_riser_DN_scopes import attribute
from attach_axis_riser_segment_attributes import append,ROOT,implementation_hashes


def data():
    doc,local,evidence,sp,policy=fixture();scope=attribute(doc,local,evidence,sp,policy,'S','G');parent=copy.deepcopy(local)
    parent['pairedJunctionCrossViewAttributeFusion']={'history':'kept'}
    for i,e in enumerate(parent['edges']):e['cross_view_attributes']={'existing':i,'unknown_length':None}
    return parent,local,scope


class Tests(unittest.TestCase):
    def test_only_native_vertical_segments_receive_DN_all_local_fields_and_plan_values_preserved(self):
        parent,local,scope=data();before=copy.deepcopy(parent);out,audit=append(parent,local,scope,'a'*64,'b'*64)
        self.assertEqual(parent,before);self.assertEqual(out['nodes'],parent['nodes']);self.assertEqual(len(out['edges']),len(parent['edges']))
        self.assertEqual(audit['added_segment_attributes'],4);self.assertFalse(audit['related_prior_HIL_confirmation_inherited'])
        for old,new in zip(parent['edges'],out['edges']):
            self.assertEqual({k:v for k,v in new.items() if k!='axis_riser_attributes'},old)
            if old['edge_id'].endswith('F'):self.assertNotIn('axis_riser_attributes',new)
            else:
                row=new['axis_riser_attributes'][0];self.assertEqual(row['nominal_mm'],450);self.assertIsNone(row['whole_edge_nominal_mm']);self.assertIsNone(row['physical_length_mm'])
                self.assertEqual(row['scope_points'],old['attribute_paths'][0][row['segment_index']:row['segment_index']+2])
        self.assertFalse(out['metadata']['hil_ready']);self.assertFalse(out[ROOT]['human_accepted'])
    def test_changed_geometry_nodes_system_or_source_cannot_reuse_DN_scope(self):
        for case in ['points','nodes','system','source','component','identity']:
            parent,local,scope=data()
            if case=='points':parent['edges'][0]['attribute_paths'][0][0][0]+=1
            elif case=='nodes':parent['nodes'][0]['x']+=1
            elif case=='system':parent['edges'][0]['system']='return'
            elif case=='source':parent['metadata']['source_sha256']='different'
            elif case=='component':parent['edges'][0]['equipment_inventory']=[dict(name='invented')]
            else:parent['edges'][0]['edge_id']='different'
            with self.subTest(case=case),self.assertRaises(ValueError):append(parent,local,scope,'a'*64,'b'*64)
    def test_unknown_DN_whole_edge_claim_false_HIL_scope_change_or_bad_lineage_block(self):
        for case in ['zero','bool','nan','unknown','length','whole','HIL','segment','path','lineage','floor','duplicate']:
            parent,local,scope=data();row=scope['records'][0]
            if case=='zero':row['nominal_mm']=0
            elif case=='bool':row['nominal_mm']=True
            elif case=='nan':row['nominal_mm']=float('nan')
            elif case=='unknown':row['status']='unknown'
            elif case=='length':row['physical_length_mm']=0
            elif case=='whole':row['whole_local_edge_DN_assigned']=True
            elif case=='HIL':scope['human_accepted']=True
            elif case=='segment':row['segment_index']=0 if row['segment_index'] else 1
            elif case=='path':row['scope_paths'][0][0][0]+=1
            elif case=='lineage':row['lineage'][0]['evidence'][0]['edge_path'][-1]='OTHER'
            elif case=='floor':scope['through_contracts'][0]['segments'][0]['floor_pair']=[1,3]
            else:scope['records'].append(copy.deepcopy(row))
            with self.subTest(case=case),self.assertRaises(ValueError):append(parent,local,scope,'a'*64,'b'*64)
    def test_double_application_is_rejected_and_dependency_closure_is_complete(self):
        parent,local,scope=data();out,_=append(parent,local,scope,'a'*64,'b'*64)
        with self.assertRaisesRegex(ValueError,'already present'):append(out,local,scope,'a'*64,'b'*64)
        hashes=implementation_hashes()
        for f in ['attach_axis_riser_segment_attributes.py','native_axis_riser_DN_scopes.py','compose_refined_paired_plan_attributes.py','checked_plan_DN_scope_attributes.py']:
            self.assertIn(f,hashes)


if __name__=='__main__':unittest.main()
