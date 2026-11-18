import copy,sys,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[2]/s/'scripts') for s in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline')]
from test_compound_member_interfaces import fixture as native_fixture
from compound_member_interfaces import group,MODE as SOURCE_MODE
from compound_interface_context import collect

def fixture():
    args,_,_=native_fixture();g=group(*args);raw=copy.deepcopy(args[3]);display=copy.deepcopy(raw);display['instances']=[]
    h=dict(axis_graph='a'*64,rendered_graph='b'*64,native_proof='c'*64,member_proof='d'*64)
    prior=dict(source_graph_sha256=h['axis_graph'],rendered_graph_sha256=h['rendered_graph'],compound_member_mains=dict(source_bindings=dict(native_proof=h['member_proof']),records=[]))
    proof=dict(mode=SOURCE_MODE,member_topology_rebuilt=True,source_drawing_graphs_unchanged=True,DN_used_for_mapping=False,installed_lengths_assigned=0,human_accepted=False,
        source_hashes=dict(raw_axis_graph=h['axis_graph'],member_proof=h['member_proof'],**args[-1]),records=g['records'],counts=dict(new_axis_correspondences=3),
        member_local_graph=dict(nodes=g['new_member_nodes'],edges=g['new_member_edges'],external_ports=g['external_ports']))
    return raw,display,proof,h,prior

class Tests(unittest.TestCase):
    def test_current_native_values_compose_without_changing_axis_or_parent(self):
        args=fixture();before=copy.deepcopy(args);r=collect(*args)
        self.assertEqual(r['axis_edges'],3);self.assertEqual(args,before);self.assertTrue(r['member_topology_rebuilt']);self.assertFalse(r['global_plan_topology_complete'])
        self.assertEqual(sum(x['complete_horizontal_centerline_route_mm'] is not None for x in r['records']),1)
    def test_existing_writer_and_wrong_native_source_do_not_compose(self):
        args=list(fixture());args[4]['member_plan_runs']=dict(records=[dict(axis_edge_id='MAIN')])
        with self.assertRaisesRegex(ValueError,'inherited owner'):collect(*args)
        args=list(fixture());args[2]['records'][0]['source_hashes']['plan_source']='z'*64
        with self.assertRaisesRegex(ValueError,'source binding'):collect(*args)
    def test_component_count_equality_does_not_hide_wrong_source_instance(self):
        args=list(fixture());raw,view=args[:2];edge=next(e for e in raw['edges'] if e['edge_id']=='MAIN');shown=next(e for e in view['edges'] if e['edge_id']=='MAIN')
        edge['equipment_inventory']=[dict(device_names=['球阀-VA1'],count=1)];shown['equipment_inventory']=[dict(device_names=['Ball Valve-VA1'],count=1)]
        view['instances']=[dict(id='I1',edge_id='MAIN',source_device_name='WRONG',name='Ball Valve-VA1',source_top_handle='H1')]
        with self.assertRaisesRegex(ValueError,'identities'):collect(*args)

if __name__=='__main__':unittest.main()
