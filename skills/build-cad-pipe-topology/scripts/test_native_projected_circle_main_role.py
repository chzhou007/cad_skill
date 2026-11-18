import copy,unittest
import ezdxf
from native_line_path_evidence import LAYERS
from native_projected_circle_main_role import collect,STATUS,AUTHORITY
from projected_circle_plan_DN import infer

class ProjectedCircleTests(unittest.TestCase):
    def fixture(self):
        doc=ezdxf.new();m=doc.modelspace();layer=LAYERS['return'];doc.layers.new(layer)
        main=m.add_line((-5,0),(5,0),dxfattribs={'layer':layer});circle=m.add_circle((0,0),1,dxfattribs={'layer':layer});branch=m.add_line((8,0),(10,0),dxfattribs={'layer':layer})
        link=dict(expert_issue='EXPERT',circle_handle=circle.dxf.handle,main_source_handle=main.dxf.handle,branch_source_handle=branch.dxf.handle,source_endpoint=[8,0],circle_center=[0,0],logical_projection_is_not_a_measured_pipe=True,physical_length='unknown',relative_elevation='unknown')
        nodes=[dict(node_id=n,node_type='tee'if n=='T'else'virtual_equipment',floor=2,system='return',x=x,y=0)for n,x in [('T',0),('L',-5),('R',5),('B',10)]]
        nodes[0]['expert_circle_evidence']=dict(expert_issue='EXPERT',circle_handle=circle.dxf.handle,main_handle=main.dxf.handle,branch_handle=branch.dxf.handle)
        edges=[dict(edge_id=e,start_node_id=a,end_node_id=b,system='return',attribute_paths=[path],source_handles=[h])for e,a,b,path,h in [('P','L','T',[[-5,0],[0,0]],main.dxf.handle),('Q','T','R',[[0,0],[5,0]],main.dxf.handle),('BR','B','T',[[10,0],[8,0]],branch.dxf.handle)]]
        edges[2]['source_expert_circle_link']=link
        graph=dict(metadata=dict(source_sha256='a'*64),nodes=nodes,edges=edges)
        authority=dict(issue=dict(path='original-expert-issue.json',sha256='c'*64),basis=AUTHORITY,source_sha256='a'*64,issue_label='EXPERT',source_bounds=[-1,-1,12,2],explicit_expert_note='explicit source-circle target')
        return doc,graph,authority
    def test_remote_parallel_branch_uses_native_main_identity_without_fake_ray_or_length(self):
        doc,g,a=self.fixture();before=copy.deepcopy(g);p=collect(doc,g,'T','a'*64,'b'*64,[a]);self.assertEqual(p['status'],STATUS);self.assertFalse(p['branch_center_ray_fabricated']);self.assertIsNone(p['physical_connector_length_mm']);self.assertEqual(p['original_main_identity']['through'],['P','Q'])
        self.assertEqual(p['junctions'][0]['source_rays'][-1]['graph_segment'][0],[8,0]);self.assertEqual(g,before)
        result=infer(g,[dict(edge_id='P',nominal_mm=200,evidence_id='native:DN200')],{'P','Q','BR'},{'T':p},'a'*64,'b'*64)
        self.assertEqual({r['edge_id']:r['nominal_mm']for r in result['records']},{'BR':200,'P':200,'Q':200})
    def test_explicit_branch_DN_does_not_backflow_into_main(self):
        doc,g,a=self.fixture();p=collect(doc,g,'T','a'*64,'b'*64,[a]);result=infer(g,[dict(edge_id='P',nominal_mm=200,evidence_id='main'),dict(edge_id='BR',nominal_mm=100,evidence_id='branch')],{'P','Q','BR'},{'T':p},'a'*64,'b'*64)
        self.assertEqual({r['edge_id']:r['nominal_mm']for r in result['records']},{'BR':100,'P':200,'Q':200})
    def test_similar_location_outside_original_expert_extent_remains_pending(self):
        doc,g,a=self.fixture();a['source_bounds']=[-1,5,12,2]
        with self.assertRaisesRegex(ValueError,'outside an explicit expert source extent'):collect(doc,g,'T','a'*64,'b'*64,[a])
    def test_wrong_service_competing_line_circle_and_changed_identity_fail_closed(self):
        for kind in ('service','all-services','line','branch-line','circle','identity','length'):
            doc,g,a=self.fixture()
            if kind=='service':g['edges'][2]['system']='supply'
            if kind=='all-services':
                for edge in g['edges']:edge['system']='supply'
            if kind=='line':doc.modelspace().add_line((-5,0),(5,0),dxfattribs={'layer':LAYERS['return']})
            if kind=='branch-line':doc.modelspace().add_line((8,0),(10,0),dxfattribs={'layer':LAYERS['return']})
            if kind=='circle':doc.modelspace().add_circle((-.5,0),1,dxfattribs={'layer':LAYERS['return']})
            if kind=='identity':g['nodes'][0]['expert_circle_evidence']['main_handle']='changed'
            if kind=='length':g['edges'][2]['source_expert_circle_link']['physical_length']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):collect(doc,g,'T','a'*64,'b'*64,[a])
    def test_missing_native_main_scope_does_not_supply_branch_DN(self):
        doc,g,a=self.fixture();p=collect(doc,g,'T','a'*64,'b'*64,[a]);result=infer(g,[dict(edge_id='P',nominal_mm=200,evidence_id='main')],{'P','BR'},{'T':p},'a'*64,'b'*64)
        self.assertIsNone(next(r for r in result['records']if r['edge_id']=='BR')['nominal_mm'])
if __name__=='__main__':unittest.main()
