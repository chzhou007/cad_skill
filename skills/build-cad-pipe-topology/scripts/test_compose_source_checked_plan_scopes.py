import copy,unittest
from compose_source_checked_plan_scopes import compose


class PlanScopeCompositionTests(unittest.TestCase):
    def fixture(self):
        base=dict(nodes=[dict(node_id='T',floor=1)],edges=[dict(edge_id=eid,system='supply',start_node_id='T',end_node_id='T',attribute_paths=[[[0,0],[1,0]]]) for eid in ('OLD','A','B')],metadata=dict(hil_ready=False))
        base['edges'][0]['cross_view_attributes']=dict(mapping_id='EXPERT-OLD',whole_edge_physical_length_mm=None)
        scopes=[]
        for scope_id,eid,floor in [('P08','A',1),('P09','B',2)]:
            child=copy.deepcopy(base);edge=next(e for e in child['edges'] if e['edge_id']==eid)
            row=dict(mapping_id='SC-1',kind='equipment_branch',system='supply',plan_edges=['P1'],iso_edges=[eid],plan_horizontal_projection_mm=123)
            edge['cross_view_attributes']=dict(mapping_id='SC-1',mapping_basis='native_source_and_main_branch_order',plan_edges=['P1'],iso_edges=[eid],system='supply',floor=floor,physical_ports_verified=False,human_accepted=False,whole_edge_physical_length_mm=None)
            child['sourceCheckedCrossViewAttributeFusion']=dict(records=[copy.deepcopy(row)],human_accepted=False,expert_confirmation_claimed=False)
            scopes.append(dict(scope_id=scope_id,graph=child,audit=dict(records=[copy.deepcopy(row)]),attribute_run=scope_id,attribute_graph_sha256='G',attribute_receipt_sha256='R'))
        return base,scopes

    def test_different_floor_scopes_namespace_ids_preserve_old_attributes_and_local_graph(self):
        base,scopes=self.fixture();before=copy.deepcopy((base,scopes));out,audit=compose(base,scopes,'a'*64)
        self.assertEqual((base,scopes),before);self.assertEqual(out['nodes'],base['nodes']);self.assertEqual(out['edges'][0],base['edges'][0])
        self.assertEqual([r['mapping_id'] for r in audit['records']],['P08-SC-1','P09-SC-1'])
        for original,edge in zip(base['edges'][1:],out['edges'][1:]):
            self.assertEqual({k:v for k,v in edge.items() if k!='cross_view_attributes'},original)
            self.assertIsNone(edge['cross_view_attributes']['whole_edge_physical_length_mm'])
        self.assertFalse(out['metadata']['hil_ready'])

    def test_overlap_same_parent_changes_and_unrecorded_attributes_rejected(self):
        for kind in ('overlap','geometry','component','node','old_attribute','unrecorded','duplicate_scope','accepted'):
            base,scopes=self.fixture();child=scopes[1]['graph']
            if kind=='overlap':scopes[1]=copy.deepcopy(scopes[0]);scopes[1]['scope_id']='P09'
            elif kind=='geometry':child['edges'][2]['attribute_paths'][0][1]=[2,0]
            elif kind=='component':child['edges'][2]['equipment_inventory']=['new']
            elif kind=='node':child['nodes'][0]['floor']=2
            elif kind=='old_attribute':child['edges'][0]['cross_view_attributes']['whole_edge_physical_length_mm']=0
            elif kind=='unrecorded':child['sourceCheckedCrossViewAttributeFusion']['records']=[];scopes[1]['audit']['records']=[]
            elif kind=='duplicate_scope':scopes[1]['scope_id']=scopes[0]['scope_id']
            else:child['sourceCheckedCrossViewAttributeFusion']['human_accepted']=True
            with self.assertRaises(ValueError):compose(base,scopes,'a'*64)

    def test_DN_evidence_ids_stay_traceable_to_original_scope(self):
        base,scopes=self.fixture();scopes[0]['audit']['plan_DN_scope_fusion']=[dict(mapping_id='SC-1',iso_edge='A',plan_drawn_nominal_mm=80,whole_main_DN_and_centerline_route=False)]
        out,audit=compose(base,scopes,'a'*64);row=audit['plan_DN_scope_fusion'][0]
        self.assertEqual(row['mapping_id'],'P08-SC-1');self.assertEqual(row['source_scope_mapping_id'],'SC-1')
        self.assertEqual(out['sourceCheckedCrossViewAttributeFusion']['whole_main_centerline_route_edges'],[])


if __name__=='__main__':unittest.main()
