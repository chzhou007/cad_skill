import copy,unittest
from test_source_direct_dn_evidence import fixture
from compound_carrier_fragment_scope import qualify

def case(rotation=90):
    doc,g,policy,line,text=fixture();other=doc.modelspace().add_text('DN300(3.600)/DN200(3.000)',dxfattribs=dict(insert=(140,100),rotation=rotation,height=5,layer='空调平面'))
    declaration=dict(handle=other.dxf.handle,raw_text=other.plain_text());corridors=[dict(source_LINE=line.dxf.handle,declarations=[declaration],edges=[dict(edge_id='E1')])]
    value=dict(nominal_mm=200,plan_DN_record=dict(status='direct_plan_DN',lineage=[dict(evidence=[dict(evidence_id='source:'+text.dxf.handle,edge_path=['E1'],transfers=[])])]))
    return [doc,g,dict(plan_edges=['E1']),value,corridors,'SRC','GRAPH']

class Tests(unittest.TestCase):
    def test_orthogonal_composite_arm_is_not_a_compound_carrier_assignment(self):
        args=case();before=copy.deepcopy(args[1:]);r=qualify(*args);self.assertEqual(args[1:],before)
        self.assertEqual(r['corridors'],[]);self.assertEqual(len(r['excluded_unbound_fragment_proposals']),1)
        self.assertEqual(r['direct_native_evidence']['observations'][0]['nominal_mm'],200);self.assertFalse(r['physical_member_identity_inferred'])
    def test_parallel_compound_label_and_missing_direct_evidence_keep_barrier(self):
        args=case(0);self.assertEqual(len(qualify(*args)['corridors']),1)
        args=case();args[3]['plan_DN_record']['status']='T_inherited_plan_DN';self.assertEqual(len(qualify(*args)['corridors']),1)
    def test_unmodeled_parallel_pipe_or_unsupported_text_cannot_clear_risk(self):
        args=case();args[0].modelspace().add_line((0,3),(100,3),dxfattribs=dict(layer='空调冷冻水回水'))
        self.assertEqual(len(qualify(*args)['corridors']),1)
        args=case();args[0].entitydb[args[4][0]['declarations'][0]['handle']].dxf.halign=2
        self.assertEqual(len(qualify(*args)['corridors']),1)
if __name__=='__main__':unittest.main()
