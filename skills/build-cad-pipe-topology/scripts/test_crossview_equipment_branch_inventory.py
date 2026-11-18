import copy,unittest
import ezdxf
from crossview_equipment_branch_inventory import service_route,inspect_branch,native_tee,index_graph,unresolved_identity_candidates

class BranchInventoryTests(unittest.TestCase):
    def fixture(self):
        doc=ezdxf.new();layer='空调冷冻水供水';doc.layers.new(layer)
        nodes=[dict(node_id='EQ',node_type='equipment',floor=2,x=0,y=10),dict(node_id='T',node_type='tee',floor=2,x=0,y=0),dict(node_id='L',node_type='virtual_equipment',floor=2,x=-10,y=0),dict(node_id='R',node_type='virtual_equipment',floor=2,x=10,y=0)]
        edges=[]
        for eid,a,b in [('B','EQ','T'),('A','T','L'),('C','T','R')]:
            first=next(n for n in nodes if n['node_id']==a);last=next(n for n in nodes if n['node_id']==b);path=[[first['x'],first['y']],[last['x'],last['y']]]
            line=doc.modelspace().add_line(path[0],path[1],dxfattribs={'layer':layer})
            edges.append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system='supply',attribute_paths=[path],source_handles=[line.dxf.handle]))
        edges[0]['confirmed_equipment_interface']=dict(source_sha256='S',confirmation={'confirmed_by':'user'})
        graph=dict(nodes=nodes,edges=edges)
        return doc,graph,dict(source_sha256='S',graph_sha256='G',inventory_sha256='I')
    def test_native_plan_branch_yields_comparison_candidate_not_mapping(self):
        doc,graph,hashes=self.fixture();old=copy.deepcopy(graph)
        result=inspect_branch(doc,graph,'EQ','supply',hashes,'plan',[])
        self.assertTrue(result['ready_for_mapping_comparison']);self.assertEqual(graph,old)
        self.assertEqual(result['trace']['tee'],'T');self.assertNotIn('physical_length_mm',result)
    def test_missing_and_parallel_branches_do_not_pick_nearest(self):
        _,graph,_=self.fixture();self.assertEqual(service_route(graph,'EQ','return')['status'],'missing_service')
        duplicate=copy.deepcopy(graph['edges'][0]);duplicate['edge_id']='B2';graph['edges'].append(duplicate)
        self.assertEqual(service_route(graph,'EQ','supply')['status'],'ambiguous_service')
    def test_native_T_reuses_selected_insert_ray_check_not_proximity(self):
        for variant in ('valid','duplicate','wrong_layer','wrong_insert'):
            doc,graph,hashes=self.fixture();edge=graph['edges'][0]
            old=doc.entitydb[edge['source_handles'][0]];doc.modelspace().delete_entity(old)
            block=doc.blocks.new('BRANCH');layer='OTHER' if variant=='wrong_layer' else '空调冷冻水供水'
            block.add_line((0,0),(0,10),dxfattribs={'layer':layer})
            if variant=='duplicate':block.add_line((0,0),(0,10),dxfattribs={'layer':layer})
            insert=doc.modelspace().add_blockref('BRANCH',(0,0));edge['source_handles']=[];edge['source_insert_handle']=insert.dxf.handle if variant!='wrong_insert' else 'MISSING'
            if variant=='valid':
                result=native_tee(doc,graph,'T','S','G')
                selected=next(r for r in result['junctions'][0]['source_rays'] if r['edge_id']=='B')
                self.assertEqual(selected['source_insert_handle'],insert.dxf.handle)
                self.assertEqual(selected['scope'],'decomposed_selected_insert')
            else:
                with self.assertRaises(ValueError):native_tee(doc,graph,'T','S','G')
    def test_calibrated_logical_owner_is_only_a_native_comparison_candidate(self):
        doc,graph,hashes=self.fixture();edge=graph['edges'][0];edge.pop('confirmed_equipment_interface')
        record=dict(source_sha256='S',equipment_id='EQ',system='supply',human_accepted=False,
            endpoint_snapshot=dict(start_node_id=edge['start_node_id'],end_node_id=edge['end_node_id'],attribute_paths=copy.deepcopy(edge['attribute_paths'])))
        edge['source_layout_equipment_interface']=record
        graph['sourceLayoutEquipmentOwnership']=dict(status='native_calibrated_logical_ownership_source_checked',records=[copy.deepcopy(record)])
        result=inspect_branch(doc,graph,'EQ','supply',hashes,'plan',[])
        self.assertTrue(result['ready_for_mapping_comparison']);self.assertFalse(result['physical_ports_verified'])
        self.assertEqual(result['logical_ownership_basis'],'source_calibrated_native_layout')
        edge['source_layout_equipment_interface']['system']='return'
        result=inspect_branch(doc,graph,'EQ','supply',hashes,'plan',[])
        self.assertFalse(result['ready_for_mapping_comparison']);self.assertIn('ownership differs',result['reason'])
    def test_floor_system_and_pending_T_are_protected(self):
        for variant in ('floor','system','pending'):
            _,graph,_=self.fixture()
            if variant=='floor':graph['nodes'][1]['floor']=3
            elif variant=='system':graph['edges'][1]['system']='return'
            else:graph['nodes'][1]['review_required']=True
            self.assertNotEqual(service_route(graph,'EQ','supply')['status'],'unique_graph_service_to_T')
    def test_missing_native_ray_and_unconfirmed_device_keep_specific_reason(self):
        for variant in ('source','owner'):
            doc,graph,hashes=self.fixture()
            if variant=='source':doc.modelspace().delete_entity(doc.entitydb[graph['edges'][1]['source_handles'][0]])
            else:graph['edges'][0].pop('confirmed_equipment_interface')
            result=inspect_branch(doc,graph,'EQ','supply',hashes,'plan',[])
            self.assertFalse(result['ready_for_mapping_comparison']);self.assertTrue(result['reason'])
    def test_ordinary_four_way_and_duplicate_native_line_are_rejected(self):
        doc,graph,hashes=self.fixture();doc.modelspace().add_line((0,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'})
        with self.assertRaisesRegex(ValueError,'uniquely'):native_tee(doc,graph,'T','S','G')
        extra=copy.deepcopy(graph['edges'][1]);extra['edge_id']='D';graph['edges'].append(extra)
        self.assertEqual(service_route(graph,'EQ','supply')['status'],'unresolved_or_non_tee_junction')
    def test_broken_node_reference_is_not_silently_a_missing_service(self):
        _,graph,_=self.fixture();graph['edges'][0]['end_node_id']='missing'
        with self.assertRaisesRegex(ValueError,'missing node'):index_graph(graph)
    def test_retained_anonymous_bodies_are_not_missing_or_auto_assigned(self):
        doc=ezdxf.new();body=doc.blocks.new('BODY');body.add_line((0,0),(10,10));insert=doc.modelspace().add_blockref('BODY',(0,0))
        node=dict(node_id='EQ-SOURCE',node_type='equipment',floor=1,x=5,y=5,source_handle=insert.dxf.handle,source_label_candidates=['CRAH-A','CRAH-B'])
        graph=dict(nodes=[node],edges=[]);old=copy.deepcopy(graph)
        candidates=unresolved_identity_candidates(doc,graph,'CRAH-A',1)
        self.assertEqual(len(candidates),1);self.assertEqual(candidates[0]['node_id'],'EQ-SOURCE')
        self.assertFalse(candidates[0]['equipment_identity_selected']);self.assertFalse(candidates[0]['ports_verified']);self.assertEqual(graph,old)
        self.assertEqual(unresolved_identity_candidates(doc,graph,'CRAH-A',2),[])
        node['x']+=1;self.assertEqual(unresolved_identity_candidates(doc,graph,'CRAH-A',1),[])

if __name__=='__main__':unittest.main()
