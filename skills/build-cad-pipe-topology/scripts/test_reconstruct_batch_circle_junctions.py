import copy,unittest
import ezdxf
from reconstruct_batch_circle_junctions import prepare,DECISION
from repair_confirmed_circle_junctions import apply


def fixture():
    d=ezdxf.new();m=d.modelspace();layer='空调冷冻水供水'
    l=m.add_line((0,0),(400,0),dxfattribs={'layer':layer})
    r=m.add_line((400,0),(400,1000),dxfattribs={'layer':layer})
    b=m.add_line((600,0),(480,0),dxfattribs={'layer':layer})
    c=m.add_circle((400,0),80,dxfattribs={'layer':'空调冷冻水回水'})
    nodes=[dict(node_id='A',node_type='tee',x=0,y=0,system='supply'),dict(node_id='B',node_type='tee',x=400,y=1000,system='supply'),dict(node_id='U',node_type='virtual_equipment',subtype='unresolved_source_terminal',x=480,y=0,system='supply'),dict(node_id='EQ',node_type='equipment',x=600,y=0)]
    edges=[dict(edge_id='M',system='supply',source_handles=[l.dxf.handle,r.dxf.handle],path=[[0,0],[400,0],[400,1000]]),dict(edge_id='BR',system='supply',source_handles=[b.dxf.handle],path=[[600,0],[480,0]])]
    g=dict(metadata={'source_sha256':'S'},nodes=nodes,edges=edges)
    candidate=dict(circle_handle=c.dxf.handle,system='supply',main_handle=l.dxf.handle,branch_handle=b.dxf.handle,circle_center=[400,0],main_edge='M',branch_edge='BR',terminal='U')
    manifest=dict(source_sha256='S',graph_sha256='G',groups=[dict(sha256='IMAGE',candidates=[candidate])])
    q=dict(id='Q',text='圆 '+c.dxf.handle+' 是否接入同系统主管？',answer={'decision':DECISION})
    reply=dict(sections=[dict(image={'sha256':'IMAGE'},questions=[q])])
    p=dict(source_sha256='S',input_graph_sha256='G',selections=[dict(question_id='Q',circle_handle=c.dxf.handle)])
    return d,g,manifest,reply,p


class BatchCircleTest(unittest.TestCase):
    def test_mapping_to_bend_splits_the_main_and_rebuilds_three_incident_edges(self):
        d,g,m,r,p=fixture();screen,answers=prepare(d,g,m,r,p,'S','G');circle=p['selections'][0]['circle_handle']
        for node in g['nodes']:node['floor']=1
        for edge in g['edges']:
            edge.update(attribute_paths=[copy.deepcopy(edge['path'])],path_points=copy.deepcopy(edge['path']),
                        path_length=1400 if edge['edge_id']=='M' else 120,equipment_names=[],equipment_counts={},
                        start_node_id='A' if edge['edge_id']=='M' else 'EQ',end_node_id='B' if edge['edge_id']=='M' else 'U',start_floor=1,end_floor=1)
        g['confirmedEquipmentInterfaceRepair']={'input_graph_sha256':'G'}
        policy=dict(source_sha256='S',input_graph_sha256='G',screen_sha256='SCREEN',circle_handles=[circle],confirmation=dict(confirmed_by='user',question=answers[0]['question'],answer=DECISION))
        out,_,audit=apply(d,g,[],screen,policy,'S','G','SCREEN')
        tee='T-USER-'+circle;incident=[e for e in out['edges'] if tee in (e['start_node_id'],e['end_node_id'])]
        self.assertEqual(len(g['edges']),2);self.assertEqual(len(out['edges']),3);self.assertEqual(len(incident),3)
        children=[e for e in out['edges'] if e.get('split_source_edge',{}).get('edge_id')=='M']
        self.assertEqual(len(children),2);self.assertEqual(sorted(e['path_length'] for e in children),[400,1000])
        self.assertEqual({h for e in children for h in e['source_handles']},set(g['edges'][0]['source_handles']))
        self.assertEqual(audit['records'][0]['retired_terminal'],'U')
    def test_bend_main_has_two_native_rays_and_keeps_conflicting_circle_colour(self):
        d,g,m,r,p=fixture();before=copy.deepcopy(g);screen,answers=prepare(d,g,m,r,p,'S','G')
        row=screen['candidates'][0]
        self.assertEqual(len(row['native_main_rays']),2);self.assertEqual(len(row['ray_directions']),3)
        self.assertFalse(row['circle_layer_matches_lines']);self.assertEqual(row['line_system'],'supply')
        self.assertEqual(g,before);self.assertEqual(len(answers),1)
    def test_no_positive_reply_or_wrong_pair_never_confirms(self):
        for change in ('reply','image'):
            d,g,m,r,p=fixture()
            if change=='reply':r['sections'][0]['questions'][0]['answer']['decision']='部分连接，见说明'
            else:r['sections'][0]['image']['sha256']='OTHER'
            with self.assertRaises(ValueError):prepare(d,g,m,r,p,'S','G')
    def test_unreferenced_competing_main_rejects_unique_ray_claim(self):
        d,g,m,r,p=fixture();d.modelspace().add_line((0,0),(400,0),dxfattribs={'layer':'空调冷冻水供水'})
        with self.assertRaisesRegex(ValueError,'ambiguous'):prepare(d,g,m,r,p,'S','G')
    def test_changed_graph_or_opposite_service_never_connects(self):
        d,g,m,r,p=fixture()
        with self.assertRaises(ValueError):prepare(d,g,m,r,p,'S','OLD')
        g['edges'][1]['system']='return'
        with self.assertRaises(ValueError):prepare(d,g,m,r,p,'S','G')
    def test_ordinary_protected_boundary_remains_protected(self):
        d,g,m,r,p=fixture();g['boundary_anchors']=[dict(boundary_id='X',source_marker_handles=[p['selections'][0]['circle_handle']])]
        with self.assertRaisesRegex(ValueError,'protected'):prepare(d,g,m,r,p,'S','G')


if __name__=='__main__':unittest.main()
