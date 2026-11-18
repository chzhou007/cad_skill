import copy,unittest
import ezdxf
from attach_confirmed_gap_joints import repair,DECISION
from repair_native_flexible_joints import fingerprint

def fixture():
    doc=ezdxf.new();b=doc.blocks.new('JOINT')
    b.add_line((-150,-20),(-150,20));b.add_line((150,-20),(150,20))
    b.add_point((-150,0));b.add_point((150,0));b.add_spline([(0,0),(1,1),(2,0),(3,1)])
    m=doc.modelspace();ins=m.add_blockref('JOINT',(250,0));layer='空调冷冻水供水'
    a=m.add_line((-100,0),(0,0),dxfattribs={'layer':layer});c=m.add_line((500,0),(600,0),dxfattribs={'layer':layer})
    edge=dict(edge_id='E',system='supply',start_node_id='A',end_node_id='B',attribute_paths=[[[-100,0],[0,0],[500,0],[600,0]]],
        path_length=200,source_path_length=200,physical_length='unknown',equipment_inventory=[],
        source_path_coverage=dict(source_sha256='S',coverage_sha256='OLD',input_graph_sha256='OLD',unverified_segment_indices=[1],unverified_drawing_length=500))
    g=dict(metadata=dict(source_sha256='S'),nodes=[dict(node_id='A'),dict(node_id='B')],edges=[edge])
    old=copy.deepcopy(g);h=ins.dxf.handle
    manifest=dict(source_sha256='S',image_sha256='IMAGE',records=[dict(handle=h,edge='E',source_line_handles=[a.dxf.handle,c.dxf.handle],gap_endpoints=[[0,0],[500,0]])])
    reply=dict(sections=[dict(image=dict(sha256='IMAGE'),questions=[dict(id='Q',text=h+' 的符号及两侧关系',answer=dict(decision=DECISION))])])
    p=dict(source_sha256='S',graph_sha256='G',calibration=dict(block_name='JOINT',block_fingerprint_sha256=fingerprint(b)),selections=[dict(insert_handle=h,question_id='Q')])
    return doc,g,old,manifest,reply,p

class ConfirmedGapJointTests(unittest.TestCase):
    def test_add_component_with_unchanged_connectivity_coverage_and_unknown_length(self):
        d,g,old,m,r,p=fixture();before=copy.deepcopy(g)
        out,rows,audit=repair(d,g,[],old,m,r,p,'S','G')
        self.assertEqual(out['nodes'],g['nodes']);self.assertEqual(len(out['edges']),1);self.assertEqual(len(rows),1)
        e=out['edges'][0]
        for key in ('attribute_paths','path_length','source_path_length','source_path_coverage','physical_length','start_node_id','end_node_id'):
            self.assertEqual(e[key],g['edges'][0][key])
        self.assertEqual(e['equipment_inventory'][0]['count'],1)
        self.assertEqual(rows[0]['source_top_handle'],p['selections'][0]['insert_handle'])
        self.assertEqual(rows[0]['owner_equipment'],'');self.assertEqual(audit['records'][0]['physical_length'],'unknown')
        self.assertFalse(out['metadata']['hil_ready']);self.assertEqual(g,before)
    def test_missing_answer_and_changed_image_reject(self):
        for kind in ('answer','image'):
            d,g,old,m,r,p=fixture()
            if kind=='answer':r['sections'][0]['questions'][0]['answer']['decision']='不是金属软接'
            else:r['sections'][0]['image']['sha256']='OTHER'
            with self.assertRaises(ValueError):repair(d,g,[],old,m,r,p,'S','G')
    def test_changed_route_or_system_cannot_reuse_old_reply(self):
        for kind in ('path','system'):
            d,g,old,m,r,p=fixture()
            if kind=='path':g['edges'][0]['attribute_paths'][0][0]=[-150,0]
            else:g['edges'][0]['system']='return'
            with self.assertRaisesRegex(ValueError,'edge changed'):repair(d,g,[],old,m,r,p,'S','G')
    def test_cross_system_neighbour_and_changed_fingerprint_reject(self):
        for kind in ('service','symbol'):
            d,g,old,m,r,p=fixture()
            if kind=='service':d.entitydb[m['records'][0]['source_line_handles'][1]].dxf.layer='空调冷冻水回水'
            else:d.blocks['JOINT'].add_line((0,0),(20,20))
            with self.assertRaises(ValueError):repair(d,g,[],old,m,r,p,'S','G')
    def test_rebound_coverage_receipt_allowed_but_changed_gap_not_allowed(self):
        d,g,old,m,r,p=fixture();g['edges'][0]['source_path_coverage']['input_graph_sha256']='NEW'
        out,_,_=repair(d,g,[],old,m,r,p,'S','G');self.assertEqual(out['edges'][0]['source_path_coverage']['input_graph_sha256'],'NEW')
        g['edges'][0]['source_path_coverage']['unverified_segment_indices']=[]
        with self.assertRaisesRegex(ValueError,'coverage changed'):repair(d,g,[],old,m,r,p,'S','G')
    def test_already_assigned_joint_not_duplicated(self):
        d,g,old,m,r,p=fixture();out,rows,_=repair(d,g,[],old,m,r,p,'S','G')
        reviewed=copy.deepcopy(out)
        with self.assertRaisesRegex(ValueError,'already claimed'):repair(d,out,rows,reviewed,m,r,p,'S','G')

if __name__=='__main__':unittest.main()
