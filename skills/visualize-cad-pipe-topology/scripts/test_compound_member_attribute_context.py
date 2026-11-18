import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from compound_member_attribute_context import collect
from compound_carrier_members import member
from test_compound_carrier_members import fixture

def data():
    args=list(fixture());r=member(*args);axis=args[2];axis['sourceFullPlanBatchAttributes']=dict(source_hashes=dict(identity_graph='a'*64))
    r['native_evidence']['iso']['snapshot']=dict(edges=copy.deepcopy(axis['edges']));r['superseded_scalar_observation']=dict(plan_nominal_mm=300)
    proof=dict(mode='native_compound_carrier_member_projection_v1',source_drawing_graphs_unchanged=True,DN_selected_from_axis_value=False,human_accepted=False,records=[r],source_hashes={k:'a'*64 for k in('axis_graph','axis_source','plan_source','plan_graph')},member_local_graph=dict(nodes=[],edges=[]))
    return axis,copy.deepcopy(axis),proof,dict(axis_graph='a'*64,rendered_graph='b'*64,native_proof='c'*64)

class Tests(unittest.TestCase):
    def test_preserves_drawing_identity_and_carries_plan_member_and_history(self):
        args=data();before=copy.deepcopy(args);r=collect(*args);self.assertEqual(args,before)
        self.assertEqual(r['records'][0]['nominal_mm'],200);self.assertEqual(r['records'][0]['superseded_scalar_observation']['plan_nominal_mm'],300)
        self.assertFalse(r['records'][0]['related_HIL_confirmation_inherited']);self.assertFalse(r['global_plan_topology_complete'])
    def test_native_geometry_change_and_length_promotion_fail(self):
        args=list(data());args[1]['edges'][0]['end_node_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'geometry differs'):collect(*args)
        args=list(data());args[2]['records'][0]['installed_whole_length_mm']=0
        with self.assertRaisesRegex(ValueError,'promoted or inferred'):collect(*args)
if __name__=='__main__':unittest.main()
