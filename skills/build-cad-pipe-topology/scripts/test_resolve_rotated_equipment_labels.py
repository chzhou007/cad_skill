import copy,math,unittest
from pathlib import Path
import ezdxf
from resolve_rotated_equipment_labels import resolve,footprint_candidates,measure_caption,sha

def profiles():
    return [dict(path=str(Path('C:/Windows/Fonts')/name),family=family,sha256=sha(Path('C:/Windows/Fonts')/name)) for name,family in [('simhei.ttf','SimHei'),('arial.ttf','Arial')]]

def fixture(rotation=0):
    doc=ezdxf.new();block=doc.blocks.new('BODY');block.add_lwpolyline([(0,200),(1000,200),(1000,1200),(0,1200)],close=True)
    angle=math.radians(rotation);turn=lambda x,y:(x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle))
    nodes=[];captions={}
    for index,label in enumerate(('CRAH-A','CRAH-B')):
        offset=1500*index;insert=doc.modelspace().add_blockref('BODY',turn(offset,0),dxfattribs=dict(layer='空调',rotation=rotation))
        text=doc.modelspace().add_text(label,dxfattribs=dict(layer='空调编号',height=200,width=.8,rotation=rotation,insert=turn(offset-200,0)))
        x,y=turn(offset+500,700)
        nodes.append(dict(node_id='EQ-SOURCE-'+insert.dxf.handle,node_type='equipment',floor=1,x=x,y=y,source_handle=insert.dxf.handle,identity_status='unresolved',connection_status='ports_unresolved',source_label_candidates=['CRAH-A','CRAH-B']))
        captions[label]=text.dxf.handle
    graph=dict(metadata=dict(source_sha256='S'),nodes=nodes,edges=[])
    policy=dict(source_sha256='S',graph_sha256='G',floor=1,equipment_layer='空调',equipment_block_names=['BODY'],caption_layer='空调编号',width_uncertainty_factors=[.8,1.2],font_profiles=profiles(),groups=[dict(id='PAIR',node_ids=[n['node_id'] for n in nodes],captions=captions)])
    return doc,graph,policy

class RotatedIdentityTests(unittest.TestCase):
    def test_native_cardinal_rotations_resolve_identity_without_ports_or_edges(self):
        for angle in (0,90,180,270):
            with self.subTest(rotation=angle):
                doc,graph,policy=fixture(angle);before=copy.deepcopy(graph)
                out,records=resolve(doc,graph,policy,'S','G',[])
                self.assertEqual(graph,before);self.assertEqual(len(out['nodes']),2);self.assertEqual(out['edges'],[])
                self.assertEqual({n['node_id'] for n in out['nodes']},{'CRAH-A','CRAH-B'})
                self.assertTrue(all(n['connection_status']=='ports_unresolved' for n in out['nodes']))
                self.assertFalse(out['sourceEquipmentIdentityResolution']['ports_inferred']);self.assertFalse(out['metadata']['hil_ready'])
                self.assertEqual({n['source_handle'] for n in graph['nodes']},{n['source_handle'] for n in out['nodes']})
    def test_insertion_marker_is_not_a_glyph_footprint(self):
        boxes={'LOW':[200,1200,0,1000],'HIGH':[200,1200,1500,2500]}
        result=footprint_candidates((0,-200),90,200,[800,850],boxes)
        self.assertEqual(result['certain'],['LOW']);self.assertEqual(result['possible'],['LOW'])
        self.assertLess(-200,boxes['LOW'][2])
    def test_font_width_uncertainty_keeps_long_spanning_label_ambiguous(self):
        boxes={'A':[0,1000,200,1200],'B':[1100,2100,200,1200]}
        result=footprint_candidates((0,0),0,200,[1000,1800],boxes)
        self.assertEqual(result['possible'],['A','B']);self.assertEqual(result['certain'],['A'])
        with self.assertRaisesRegex(ValueError,'uncertainty'):footprint_candidates((0,0),0,200,[1000],boxes,[.99,1.01])
    def test_mirrored_OCS_alignment_and_oblique_are_not_silently_measured(self):
        for changes in ({'text_generation_flag':2},{'extrusion':(0,0,-1)},{'halign':1},{'oblique':15}):
            doc,graph,policy=fixture();text=doc.entitydb[policy['groups'][0]['captions']['CRAH-A']]
            for key,value in changes.items():setattr(text.dxf,key,value)
            with self.assertRaisesRegex(ValueError,'transform'):measure_caption(text,policy['font_profiles'])
    def test_font_fallback_and_duplicated_families_fail_closed(self):
        doc,graph,policy=fixture();text=doc.entitydb[policy['groups'][0]['captions']['CRAH-A']]
        bad=copy.deepcopy(policy['font_profiles']);bad[0]['family']='NotTheFont'
        with self.assertRaisesRegex(ValueError,'fell back'):measure_caption(text,bad)
        with self.assertRaisesRegex(ValueError,'independent'):measure_caption(text,[policy['font_profiles'][0]]*2)
    def test_occupied_identity_component_owner_and_connected_body_require_migration(self):
        for variant in ('occupied','component','connected'):
            doc,graph,policy=fixture();inventory=[]
            if variant=='occupied':graph['nodes'].append(dict(node_id='CRAH-A',node_type='virtual_equipment'))
            elif variant=='component':inventory=[dict(owner_equipment=graph['nodes'][0]['node_id'])]
            else:graph['edges'].append(dict(edge_id='E',start_node_id=graph['nodes'][0]['node_id'],end_node_id=graph['nodes'][1]['node_id']))
            with self.assertRaises(ValueError):resolve(doc,graph,policy,'S','G',inventory)
    def test_changed_source_or_duplicate_caption_cannot_inherit_layout_identity(self):
        doc,graph,policy=fixture()
        with self.assertRaisesRegex(ValueError,'stale'):resolve(doc,graph,policy,'wrong','G',[])
        doc.modelspace().add_text('CRAH-A')
        with self.assertRaisesRegex(ValueError,'duplicate native'):resolve(doc,graph,policy,'S','G',[])

if __name__=='__main__':unittest.main()
