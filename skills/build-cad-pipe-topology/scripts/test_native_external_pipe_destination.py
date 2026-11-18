import copy,math,unittest
import ezdxf
from ezdxf.math import Matrix44
from native_external_pipe_destination import collect,LAYERS

def fixture(angle=0):
    doc=ezdxf.new()
    for name in ['ANNOT','DIM_SYMB',*LAYERS.values()]:doc.layers.new(name)
    msp=doc.modelspace();marker=msp.add_lwpolyline([(0,0),(40,0),(45,10),(50,-10),(55,0),(100,0)],dxfattribs=dict(layer='DIM_SYMB'))
    def caption(text,pos,a,b,tip):
        t=msp.add_text(text,dxfattribs=dict(insert=(*pos,0),height=20,layer='ANNOT'));u=msp.add_line((*a,0),(*b,0),dxfattribs=dict(layer='ANNOT'));lead=msp.add_line((*b,0),(*tip,0),dxfattribs=dict(layer='ANNOT'))
        return dict(text_handle=t.dxf.handle,expected_text=text,underline_handle=u.dxf.handle,leader_handle=lead.dxf.handle)
    common=caption('接至室外冷冻站',(-30,-114),(-40,-120),(10,-120),(40,0));members=[];nodes=[];edges=[]
    for i,(x,system,identifier) in enumerate([(10,'supply','CHWS1'),(30,'return','CHWR1'),(70,'supply','CHWS2'),(90,'return','CHWR2')]):
        pipe=msp.add_line((x,60,0),(x,0,0),dxfattribs=dict(layer=LAYERS[system]));left=i<2;y=-60 if i%2==0 else -80
        pos=(-70,y+6) if left else (130,y+6);a=(-80,y) if left else (200,y);b=(-5,y) if left else (120,y)
        spec=caption(identifier+' DN450',pos,a,b,(x,0));spec.update(node_id='UT'+str(i),identifier=identifier,source_line_handle=pipe.dxf.handle);members.append(spec)
        nodes.extend([dict(node_id='T'+str(i),node_type='tee',system=system,floor=1,x=x,y=60),dict(node_id='UT'+str(i),node_type='virtual_equipment',system=system,floor=1,x=x,y=0,source_handles=[pipe.dxf.handle])])
        edges.append(dict(edge_id='E'+str(i),start_node_id='T'+str(i),end_node_id='UT'+str(i),system=system,attribute_paths=[[[x,60],[x,0]]],source_handles=[pipe.dxf.handle]))
    graph=dict(metadata=dict(source_sha256='S'),nodes=nodes,edges=edges)
    if angle:
        rotation=Matrix44.z_rotate(math.radians(angle))
        for e in msp:e.transform(rotation)
        for n in graph['nodes']:
            pt=rotation.transform((n['x'],n['y'],0));n['x'],n['y']=pt.x,pt.y
        for e in graph['edges']:
            e['attribute_paths']=[[[p.x,p.y] for p in (rotation.transform((*point,0)) for point in path)] for path in e['attribute_paths']]
    policy=dict(source_sha256='S',graph_sha256='G',text_layers=['ANNOT'],leader_layers=['ANNOT'],caption=common,destination='室外冷冻站',marker_handle=marker.dxf.handle,marker_layer='DIM_SYMB',members=members)
    return doc,graph,policy,'S','G'

class Tests(unittest.TestCase):
    def test_four_named_pipes_share_only_destination_annotation_through_rotation(self):
        for angle in (0,90,180,270):
            with self.subTest(angle=angle):
                args=fixture(angle);before=copy.deepcopy(args[1]);data=collect(*args)
                self.assertEqual(args[1],before);self.assertEqual(len(data['records']),4);self.assertEqual({r['destination'] for r in data['records']},{'室外冷冻站'})
                self.assertFalse(data['common_marker_creates_pipe_connection']);self.assertEqual(data['nodes_merged'],0);self.assertEqual(data['new_connections_added'],0)
                self.assertTrue(all(not r['physical_port_verified'] and r['physical_length_mm'] is None and not r['whole_edge_DN_verified'] for r in data['records']))
    def test_wrong_colour_leader_target_missing_member_and_extra_pipe_block(self):
        for case in ('service','leader','partial','extra','source','text','marker','equipment','Z'):
            args=fixture();doc,graph,policy=args[:3];member=policy['members'][0]
            if case=='service':doc.entitydb[member['source_line_handle']].dxf.layer=LAYERS['return']
            elif case=='leader':doc.entitydb[member['leader_handle']].dxf.end=(12,0,0)
            elif case=='partial':policy['members'].pop()
            elif case=='extra':doc.modelspace().add_line((80,40,0),(80,0,0),dxfattribs=dict(layer=LAYERS['supply']))
            elif case=='source':policy['graph_sha256']='old'
            elif case=='text':doc.entitydb[policy['caption']['text_handle']].dxf.text='附近房间'
            elif case=='marker':doc.entitydb[policy['marker_handle']].closed=True
            elif case=='equipment':graph['nodes'][1]['node_type']='equipment'
            else:doc.entitydb[member['source_line_handle']].dxf.end=(10,0,100)
            with self.subTest(case=case),self.assertRaises(ValueError):collect(*args)
    def test_unsupported_mirrored_text_is_explicitly_rejected_not_silently_decoded(self):
        args=fixture();args[0].entitydb[args[2]['caption']['text_handle']].dxf.text_generation_flag=2
        with self.assertRaisesRegex(ValueError,'readable native'):collect(*args)
if __name__=='__main__':unittest.main()
