import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import ezdxf
from normalize_plan_circle_paths import apply,snapshot
from native_circle_rim_junction_evidence import collect
from crossview_equipment_branch_inventory import inspect_branch,native_tee

class CirclePathTests(unittest.TestCase):
    def fixture(self,angle=0,mirror=1):
        import math
        def xy(x,y):
            a=math.radians(angle);return [mirror*x*math.cos(a)-y*math.sin(a),mirror*x*math.sin(a)+y*math.cos(a)]
        doc=ezdxf.new();layer='空调冷冻水供水';doc.layers.new(layer)
        main=doc.modelspace().add_line(xy(-20,0),xy(20,0),dxfattribs={'layer':layer})
        branch=doc.modelspace().add_line(xy(0,2),xy(0,10),dxfattribs={'layer':layer})
        circle=doc.modelspace().add_circle((0,0),2,dxfattribs={'layer':layer})
        nodes=[dict(node_id=n,node_type=t,system='supply',floor=1,x=xy(x,y)[0],y=xy(x,y)[1]) for n,t,x,y in [('T','tee',0,0),('EQ','equipment',0,10),('L','virtual_equipment',-20,0),('R','virtual_equipment',20,0)]]
        edges=[dict(edge_id=e,start_node_id='T',end_node_id=n,system='supply',attribute_paths=[[[0,0],xy(x,y)]],source_handles=[h],path_length=length) for e,n,x,y,h,length in [('B','EQ',0,10,branch.dxf.handle,10),('M1','L',-20,0,main.dxf.handle,20),('M2','R',20,0,main.dxf.handle,20)]]
        old=edges[0];record=dict(source_sha256='S',equipment_id='EQ',system='supply',human_accepted=False,endpoint_snapshot=snapshot(old))
        old['source_layout_equipment_interface']=record
        graph=dict(nodes=nodes,edges=edges,sourceLayoutEquipmentOwnership=dict(status='native_calibrated_logical_ownership_source_checked',records=[copy.deepcopy(record)]))
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);base=Path(temp.name)
        picture=base/'pair.png';picture.write_bytes(b'fixed functional fixture only')
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        row=dict(circle_handle=circle.dxf.handle,main_handle=main.dxf.handle,branch_handle=branch.dxf.handle,system='supply',radius=2,pair_image=str(picture),pair_sha256=sha(picture),disposition='direct_same_system_circle_rim_contact')
        review=base/'review.json';review.write_text(json.dumps(dict(source_sha256='S',review_kind='technical_native_source_comparison',connections=[row])),encoding='utf8')
        policy=dict(source_sha256='S',review_manifest=str(review),review_sha256=sha(review),circle_handles=[circle.dxf.handle])
        return doc,graph,policy

    def test_rotated_mirrored_exclusion_preserves_connection_ownership_and_unknown_length(self):
        for angle,mirror in [(0,1),(90,1),(180,-1),(270,-1)]:
            doc,graph,policy=self.fixture(angle,mirror);before=copy.deepcopy(graph)
            out,records=apply(doc,graph,policy,'S');self.assertEqual(graph,before)
            self.assertEqual(out['nodes'],graph['nodes']);self.assertEqual(out['edges'][1:],graph['edges'][1:]);self.assertEqual(out['sourceLayoutEquipmentOwnership'],graph['sourceLayoutEquipmentOwnership'])
            self.assertEqual(len(records),1);edge=out['edges'][0];self.assertAlmostEqual(edge['path_length'],8)
            self.assertFalse(edge['path_length_complete']);self.assertIsNone(records[0]['physical_connector_length'])
            self.assertEqual(edge['source_layout_equipment_interface'],graph['edges'][0]['source_layout_equipment_interface'])
            result=inspect_branch(doc,out,'EQ','supply',dict(source_sha256='S',graph_sha256='G',inventory_sha256='I'),'plan',[])
            self.assertTrue(result['ready_for_mapping_comparison'],result)
            rays=result['junction_evidence']['junctions'][0]['source_rays'];self.assertEqual(sum(r.get('scope')=='source_reviewed_circle_rim' for r in rays),1)
            self.assertFalse(result['physical_ports_verified'])

    def test_radius_twice_stale_review_and_existing_attributes_rejected(self):
        doc,g,p=self.fixture();out,_=apply(doc,g,p,'S')
        with self.assertRaisesRegex(ValueError,'already normalized'):apply(doc,out,p,'S')
        g['edges'][0]['cross_view_attributes']={}
        with self.assertRaisesRegex(ValueError,'attributes'):apply(doc,g,p,'S')
        Path(p['review_manifest']).write_text('{}',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'stale'):apply(doc,g,p,'S')

    def test_duplicate_main_opposite_system_and_Z_do_not_gain_connections(self):
        for variant in ('duplicate','opposite','Z','fourway'):
            doc,g,p=self.fixture()
            if variant=='duplicate':doc.modelspace().add_line((-20,0),(20,0),dxfattribs={'layer':'空调冷冻水供水'})
            if variant=='opposite':doc.layers.new('空调冷冻水回水');doc.modelspace().add_line((0,-20),(0,20),dxfattribs={'layer':'空调冷冻水回水'})
            if variant=='Z':doc.entitydb[g['edges'][0]['source_handles'][0]].dxf.start=(0,2,1)
            if variant=='fourway':extra=copy.deepcopy(g['edges'][1]);extra['edge_id']='M3';g['edges'].append(extra)
            with self.assertRaises(ValueError):apply(doc,g,p,'S')

    def test_a_circle_flag_or_tampered_radius_path_does_not_bypass_replay(self):
        doc,g,p=self.fixture();out,_=apply(doc,g,p,'S');edge=out['edges'][0]
        edge['attribute_paths'][0][0]=[0,0]
        with self.assertRaises(ValueError):collect(doc,out,'T','S','G')
        result=inspect_branch(doc,out,'EQ','supply',dict(source_sha256='S',graph_sha256='G',inventory_sha256='I'),'plan',[])
        self.assertFalse(result['ready_for_mapping_comparison'])
        edge.pop('source_circle_connection')
        with self.assertRaises(ValueError):native_tee(doc,out,'T','S','G')

if __name__=='__main__':unittest.main()
