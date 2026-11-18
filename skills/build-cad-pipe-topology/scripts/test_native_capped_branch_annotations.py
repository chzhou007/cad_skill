import copy,math,unittest
import ezdxf
from native_capped_branch_annotations import collect,LAYERS


class Tests(unittest.TestCase):
    def fixture(self,rotation=0,mirror=False):
        doc=ezdxf.new();m=doc.modelspace();angle=math.radians(rotation)
        def point(p):
            x,y=p[:2];x=-x if mirror else x
            return (1000+x*math.cos(angle)-y*math.sin(angle),2000+x*math.sin(angle)+y*math.cos(angle),p[2] if len(p)>2 else 0)
        def line(a,b,layer='annotation'):return m.add_line(point(a),point(b),dxfattribs=dict(layer=layer))
        caption=m.add_text('预留支管接口/共2处',dxfattribs=dict(insert=point((0,400)),height=140,layer='annotation',rotation=rotation,text_generation_flag=2 if mirror else 0))
        qualifier=m.add_text('盲板封堵',dxfattribs=dict(insert=point((0,200)),height=140,layer='annotation',rotation=rotation,text_generation_flag=2 if mirror else 0))
        pipe=line((400,-400,7),(400,0,12),LAYERS['supply']);long=line((340,20,15),(460,20,15));short=line((360,60,15),(440,60,15));leader=line((-40,300),(400,60))
        p=point((400,0));n=dict(node_id='UT',node_type='virtual_equipment',subtype='unresolved_source_terminal',x=p[0],y=p[1],system='supply',source_handles=[pipe.dxf.handle])
        graph=dict(nodes=[n],edges=[dict(edge_id='E',start_node_id='T',end_node_id='UT',system='supply',source_handles=[pipe.dxf.handle])],metadata=dict(source_sha256='S'))
        choice=dict(node_id='UT',pipe_handle=pipe.dxf.handle,marker_handles=[long.dxf.handle,short.dxf.handle],caption_handle=caption.dxf.handle,qualifier_handle=qualifier.dxf.handle,leader_handles=[leader.dxf.handle])
        return doc,graph,choice

    def test_native_xyz_offset_is_evidence_not_a_snap_or_new_pipe(self):
        doc,g,c=self.fixture();before=copy.deepcopy(g);result=collect(doc,g,'S',[c]);r=result['records'][0]
        self.assertEqual(g,before);self.assertFalse(result['graph_mutated']);self.assertEqual(result['topology_nodes_retired'],0)
        self.assertEqual(r['source_geometry']['frontier_to_first_marker_offset_xy'],20)
        self.assertEqual(r['source_geometry']['source_pipe_endpoints'][0][2],12);self.assertEqual(r['source_geometry']['marker_centres'][0][2],15)
        self.assertFalse(r['physical_connection_assigned']);self.assertIsNone(r['physical_length_mm']);self.assertFalse(r['quantity_expanded_into_ports'])

    def test_rotation_and_mirror_keep_the_same_caption_marker_relation(self):
        for angle in (0,37,90,180,270):
            for mirror in (False,True):
                with self.subTest(angle=angle,mirror=mirror):
                    doc,g,c=self.fixture(angle,mirror);result=collect(doc,g,'S',[c]);self.assertEqual(len(result['records']),1)
                    self.assertAlmostEqual(result['records'][0]['source_geometry']['frontier_to_first_marker_offset_xy'],20)

    def test_missing_or_unrelated_chinese_text_cannot_classify_two_bars(self):
        for text in ('金属软管','预留空调位','盲板封堵','预留支管接口/共0处'):
            with self.subTest(text=text):
                doc,g,c=self.fixture();doc.entitydb[c['caption_handle']].dxf.text=text
                with self.assertRaisesRegex(ValueError,'declaration'):collect(doc,g,'S',[c])
        doc,g,c=self.fixture();doc.entitydb[c['qualifier_handle']].dxf.insert=(3000,4000,0)
        with self.assertRaisesRegex(ValueError,'caption frame'):collect(doc,g,'S',[c])

    def test_no_leader_or_wrong_tip_and_large_frontier_gap_block(self):
        doc,g,c=self.fixture();c['leader_handles']=[]
        with self.assertRaisesRegex(ValueError,'chain'):collect(doc,g,'S',[c])
        doc,g,c=self.fixture();doc.entitydb[c['leader_handles'][0]].dxf.end=(1440,2060,0)
        with self.assertRaisesRegex(ValueError,'misses marker'):collect(doc,g,'S',[c])
        doc,g,c=self.fixture();g['nodes'][0]['y']=1980;doc.entitydb[c['pipe_handle']].dxf.end=(1400,1980,12)
        with self.assertRaisesRegex(ValueError,'bounded marker'):collect(doc,g,'S',[c])

    def test_competing_pipe_endpoints_do_not_choose_a_nearest_candidate(self):
        doc,g,c=self.fixture();other=doc.modelspace().add_line((1400,1600,12),(1400,2000,12),dxfattribs=dict(layer=LAYERS['supply']))
        n=copy.deepcopy(g['nodes'][0]);n.update(node_id='OTHER',source_handles=[other.dxf.handle]);g['nodes'].append(n)
        with self.assertRaisesRegex(ValueError,'competing'):collect(doc,g,'S',[c])

    def test_wrong_system_nonleaf_duplicate_or_source_drift_block(self):
        for mode in ('system','nonleaf','source','duplicate'):
            with self.subTest(mode=mode):
                doc,g,c=self.fixture();choices=[c]
                if mode=='system':g['nodes'][0]['system']='return'
                elif mode=='nonleaf':g['edges'].append(copy.deepcopy(g['edges'][0]))
                elif mode=='source':g['metadata']['source_sha256']='CHANGED'
                else:choices.append(c)
                with self.assertRaises(ValueError):collect(doc,g,'S',choices)


if __name__=='__main__':unittest.main()
