import copy,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_reconstruct_batch_circle_junctions as original_fixture
from reconstruct_batch_circle_junctions import prepare,DECISION
from repair_confirmed_circle_junctions import apply
from confirm_crossview_paths import load,sha,encode
from native_user_circle_endpoint_rays import collect
from user_circle_endpoint_plan_DN import current_tee


class Tests(unittest.TestCase):
    def fixture(self,angle=0,mirror=1):
        doc,parent,manifest,reply,policy=original_fixture.fixture()
        def xy(p):
            a=math.radians(angle)
            return [mirror*p[0]*math.cos(a)-p[1]*math.sin(a),mirror*p[0]*math.sin(a)+p[1]*math.cos(a)]
        for entity in doc.modelspace():
            if entity.dxftype()=='LINE':entity.dxf.start=xy(entity.dxf.start);entity.dxf.end=xy(entity.dxf.end)
            elif entity.dxftype()=='CIRCLE':entity.dxf.center=xy(entity.dxf.center)
        for node in parent['nodes']:
            node['x'],node['y']=xy([node['x'],node['y']]);node['floor']=1
        for edge in parent['edges']:
            edge['path']=[xy(p)for p in edge['path']]
            edge.update(attribute_paths=[copy.deepcopy(edge['path'])],path_points=copy.deepcopy(edge['path']),
                path_length=1400 if edge['edge_id']=='M' else 120,equipment_names=[],equipment_counts={},
                start_node_id='A'if edge['edge_id']=='M'else'EQ',end_node_id='B'if edge['edge_id']=='M'else'U',start_floor=1,end_floor=1)
        manifest['groups'][0]['candidates'][0]['circle_center']=xy([400,0])
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);base=Path(directory.name)
        original=base/'parent.json';original.write_bytes(encode(parent));parent=load(original)
        graph_hash=sha(original);policy['input_graph_sha256']=graph_hash;manifest['graph_sha256']=graph_hash
        image=base/'pair.png';image.write_bytes(b'pinned functional fixture only')
        manifest['groups'][0]['sha256']=sha(image);reply['sections'][0]['image']['sha256']=sha(image)
        mp,rp=base/'manifest.json',base/'reply.json';mp.write_bytes(encode(manifest));rp.write_bytes(encode(reply))
        policy.update(manifest=str(mp),manifest_sha256=sha(mp),reply=str(rp),reply_sha256=sha(rp),pair_images=[dict(path=str(image),sha256=sha(image))])
        pp=base/'policy.json';pp.write_bytes(encode(policy))
        screen,answers=prepare(doc,parent,manifest,reply,policy,'S',graph_hash)
        sp=base/'screen.json';sp.write_bytes(encode(screen))
        scope=base/'scope.json';scope.write_bytes(encode(dict(source_sha256='S',graph_sha256=graph_hash,pairs=[dict(connections=screen['candidates'])])))
        confirmation=dict(confirmed_by='user',question='Batch Pair circle connections',answer=DECISION,records=answers,reply_sha256=sha(rp))
        selection=dict(policy,screen_basis='current_graph',screen_sha256=sha(sp),circle_handles=[c['circle_handle']for c in screen['candidates']],
            review_evidence=dict(image=str(image),image_sha256=sha(image),manifest=str(scope),manifest_sha256=sha(scope),shown_circle_handles=[c['circle_handle']for c in screen['candidates']]),confirmation=confirmation)
        graph,_,_=apply(doc,parent,[],screen,selection,'S',graph_hash,sha(sp))
        review=dict(path=str(pp),sha256=sha(pp),screen=dict(path=str(sp),sha256=sha(sp)))
        return doc,graph,'T-USER-'+screen['candidates'][0]['circle_handle'],[dict(path=str(original),sha256=graph_hash)],review

    def test_inherited_corner_main_replays_both_native_LINEs_rotations_and_mirrors(self):
        for angle,mirror in [(0,1),(37,1),(90,1),(180,-1),(270,-1)]:
            doc,graph,nid,parents,review=self.fixture(angle,mirror);before=copy.deepcopy(graph)
            proof=collect(doc,graph,nid,'S','G',parents,review)
            self.assertEqual(graph,before);self.assertTrue(proof['through_pair_recomputed_from_native_rays'])
            rays=proof['junctions'][0]['source_rays'];self.assertEqual(len({r['source_line_handle']for r in rays}),3)
            self.assertEqual(sum(r['scope']=='confirmed_native_circle_center_LINE_endpoint'for r in rays),2)
            self.assertEqual(proof['physical_values_assigned'],0);self.assertFalse(proof['human_accepted'])
            self.assertFalse(proof['circle_layer_rewritten'])
            self.assertNotEqual(graph['nodes'][-1]['system'],None)

    def test_stale_original_evidence_wrong_service_and_extra_contacts_do_not_pass(self):
        for mode in ('reply','pair','screen','parent','mixed','duplicate','fourway','branch_rim','Z'):
            doc,graph,nid,parents,review=self.fixture();policy=load(review['path'])
            if mode=='reply':Path(policy['reply']).write_bytes(b'{}')
            elif mode=='pair':Path(policy['pair_images'][0]['path']).write_bytes(b'other')
            elif mode=='screen':Path(review['screen']['path']).write_bytes(b'{}')
            elif mode=='parent':Path(parents[0]['path']).write_bytes(b'{}')
            elif mode=='mixed':graph['edges'][0]['system']='return'
            elif mode=='duplicate':doc.modelspace().add_line((0,0),(400,0),dxfattribs={'layer':'空调冷冻水供水'})
            elif mode=='fourway':doc.modelspace().add_line((400,0),(300,-200),dxfattribs={'layer':'空调冷冻水供水'})
            elif mode=='branch_rim':next(e for e in graph['edges']if e['edge_id']=='BR')['attribute_paths'][0][-1]=[400,0]
            else:
                line=next(e for e in doc.modelspace().query('LINE')if e.dxf.start.x==600)
                line.dxf.end=(480,0,1)
            with self.subTest(mode=mode),self.assertRaises(ValueError):collect(doc,graph,nid,'S','G',parents,review)

    def test_unrelated_source_failure_does_not_enter_corner_fallback(self):
        with patch('user_circle_endpoint_plan_DN.previous_tee',side_effect=ValueError('missing or ambiguous graph T ray')):
            with patch('user_circle_endpoint_plan_DN.endpoint_collect')as fallback:
                with self.assertRaises(ValueError):current_tee(None,{},'T','S','G',[],None)
                fallback.assert_not_called()


if __name__=='__main__':unittest.main()
