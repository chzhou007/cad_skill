import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from reapply_candidate_ring_crossview_DN import endpoint_identity,attribute_graph_binding
from reapply_reviewed_ring_crossview_DN import select_scopes


class CandidateCrossviewTests(unittest.TestCase):
    def test_both_independent_endpoints_and_orientation_required(self):
        plan=dict(start_node_id='P',end_node_id='Q');axis=dict(start_node_id='B',end_node_id='A')
        self.assertTrue(endpoint_identity(plan,axis,dict(P='A',Q='B'))['orientation_reversed'])
        for mapping in ({'P':'A'},{'P':'A','Q':'A'},{'P':'A','Q':'C'}):
            with self.subTest(mapping=mapping),self.assertRaises(ValueError):endpoint_identity(plan,axis,mapping)

    def test_reused_local_ID_in_another_floor_is_not_a_source_match(self):
        graph=dict(edges=[dict(edge_id='CURRENT',floor_start=3,floor_end=3,system='return'),
                          dict(edge_id='OTHER',floor_start=2,floor_end=2,system='return')])
        observation=lambda eid:dict(plan_edges=['E0010'],grouped_axis_edges=[eid],mapping_id='M-'+eid)
        provider=dict(records=[dict(edge_id=eid,classification='horizontal_only',correspondence_observations=[observation(eid)])
                               for eid in ('CURRENT','OTHER')])
        before=copy.deepcopy(provider)
        candidates,excluded=select_scopes(provider,graph,{'E0010':dict(system='return')},3)
        self.assertEqual([r['axis_edge_id'] for r in candidates],['CURRENT'])
        self.assertEqual([r['axis_edge_id'] for r in excluded],['OTHER']);self.assertEqual(provider,before)
        with self.assertRaises(ValueError):select_scopes(provider,graph,{'E0010':dict(system='supply')},3)

    def test_existing_component_overlay_restores_the_exact_attribute_graph(self):
        from fragment_component_index import AUDIT,MODE
        from refresh_fragment_component_index import overlay
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def write(name,value):
                p=root/name;p.write_text(json.dumps(value),encoding='utf8')
                return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            parent=dict(edges=[dict(edge_id='Q',system='return',equipment_inventory=[])],instances=[dict(id='OLD')])
            before=write('parent.json',parent);current=copy.deepcopy(parent)
            audit=dict(added_instances=[dict(id='NEW')],added_count=1,previous_edge_inventories={'Q':[]},pipe_graph_restoration_exact=True)
            current['instances'].append(dict(id='NEW'));current['edges'][0]['equipment_inventory']=[dict(type='native-ball')];current[AUDIT]=audit
            rendered=write('current.json',current)
            proof=dict(mode=MODE,inputs=dict(parent_graph=before),rendered_graph_sha256=rendered['sha256'],audit=audit,
                complete_current_parent_native_replayed=True,new_correspondences_assigned=0,physical_values_assigned=0,human_accepted=False)
            proof_spec=write('proof.json',proof)
            inputs=dict(attribute_context_graph=before,rendered_graph=rendered,component_overlay_proof=proof_spec)
            manifest=dict(attributeValueContext=dict(current_rendered_graph_sha256=before['sha256']),componentFragmentOverlay=overlay(proof,proof_spec['path']))
            snapshot=copy.deepcopy((current,manifest));binding=attribute_graph_binding(current,manifest,inputs)
            self.assertTrue(binding['pipe_graph_restoration_exact']);self.assertEqual((current,manifest),snapshot)
            bad=copy.deepcopy(current);bad['edges'][0]['system']='supply'
            with self.assertRaisesRegex(ValueError,'restore'):attribute_graph_binding(bad,manifest,inputs)
            bad=copy.deepcopy(manifest);bad['attributeValueContext']['current_rendered_graph_sha256']=rendered['sha256']
            with self.assertRaisesRegex(ValueError,'binding'):attribute_graph_binding(current,bad,inputs)


if __name__=='__main__':unittest.main()
