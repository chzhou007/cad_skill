import copy,unittest
import ezdxf
from native_proxy_evidence import block_fingerprint
from nested_equipment_ports import bind,native_instances,readable

def instance(nid='EQ-F1-A',poly=None):
    poly=poly or [[0,0],[10,0],[10,10],[0,10]]
    return dict(node_id=nid,polygon=poly,bounds=[min(p[0]for p in poly),min(p[1]for p in poly),max(p[0]for p in poly),max(p[1]for p in poly)],
        source_chain=['A','B',nid],source_block='BODY',floor='F1',tag='FW-201',source_tag_handle='TAG',texts=[],primitives=[],subtype='Fan Wall',subtype_zh='风墙',symbol_key='EQ_FW')

def graph(points=None):
    points=points or [[3,0],[7,0]];nodes=[];edges=[]
    for i,p in enumerate(points):
        nid='UT'+str(i);other='T'+str(i);q=[p[0],p[1]-20]
        nodes.extend([dict(node_id=nid,node_type='virtual_equipment',x=p[0],y=p[1],floor='F1',ports=[]),dict(node_id=other,node_type='tee',x=q[0],y=q[1])])
        edges.append(dict(edge_id='E'+str(i),start_node_id=nid,end_node_id=other,path_points=[p,q],attribute_paths=[[p,q]],source_handles=[str(i)],system=['supply','return'][i%2],equipment_inventory=[{'device_names':['V'+str(i)]}]))
    return {'nodes':nodes,'edges':edges}

class NativeEquipmentPorts(unittest.TestCase):
    profile={'contact_tolerance':.01}
    def test_pairs_one_body_preserve_services_and_paths(self):
        g=graph();out,a=bind(g,[instance()],self.profile)
        self.assertEqual(a['physical_port_count'],2);self.assertEqual(len(out['nodes']),3)
        self.assertEqual([e['system']for e in out['edges']],['supply','return'])
        self.assertEqual([e['attribute_paths']for e in out['edges']],[e['attribute_paths']for e in g['edges']])
        self.assertNotEqual(*[e['start_port_id']for e in out['edges']])
    def test_shared_caption_does_not_merge_instances(self):
        a=instance();b=instance('EQ-F1-B',[[20,0],[30,0],[30,10],[20,10]])
        out,audit=bind(graph([[3,0],[23,0]]),[a,b],self.profile)
        self.assertEqual(audit['connected_equipment_count'],2)
        self.assertNotEqual(*[e['start_node_id']for e in out['edges']])
    def test_nearby_endpoint_does_not_bind(self):
        _,a=bind(graph([[3,-.1]]),[instance()],self.profile);self.assertEqual(a['physical_port_count'],0)
    def test_bbox_interior_and_nonrectangular_body_rejected(self):
        _,a=bind(graph([[1,1]]),[instance(poly=[[0,5],[5,0],[10,5],[5,10]])],self.profile)
        self.assertEqual(a['physical_port_count'],0)
    def test_inward_ray_rejected(self):
        g=graph([[3,10]]);g['edges'][0]['path_points']=[[3,10],[3,5],[3,-20]]
        _,a=bind(g,[instance()],self.profile);self.assertEqual(a['physical_port_count'],0)
    def test_competing_owners_rejected(self):
        _,a=bind(graph(),[instance(),instance('EQ-F1-B')],self.profile);self.assertEqual(a['physical_port_count'],0)
    def test_known_destination_and_floor_protected(self):
        g=graph();g['nodes'][0]['interface_destination']={'text':'接至板换集装箱'};g['nodes'][2]['floor']='F2'
        _,a=bind(g,[instance()],self.profile);self.assertEqual(a['physical_port_count'],0)
    def test_nested_rotation_mirror_and_duplicate_tags(self):
        d=ezdxf.new();body=d.blocks.new('设备');body.add_lwpolyline([(0,0),(10,0),(10,5),(0,5)],close=True);body.add_text('FW-201')
        floor=d.blocks.new('FLOOR');floor.add_blockref('设备',(20,30),dxfattribs={'rotation':90,'xscale':-1})
        root=d.modelspace().add_blockref('FLOOR',(100,200))
        profile={'roots':[{'source_chain':[root.dxf.handle],'floor':'F1'}],'prototypes':[{'block':'设备','fingerprint':block_fingerprint(body),'tag_regex':'FW-201','label':'Fan Wall','label_zh':'风墙','symbol_key':'EQ_FW'}],'contact_tolerance':.01}
        rows=native_instances(d,profile)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['bounds'],[115,220,120,230])
        self.assertEqual(rows[0]['source_chain'][-1],next(iter(floor)).dxf.handle)
        broken=copy.deepcopy(profile);broken['prototypes'][0]['fingerprint']='invalid'
        with self.assertRaises(ValueError):native_instances(d,broken)
        broken=copy.deepcopy(profile);broken['roots'][0]['source_chain']=[next(iter(floor)).dxf.handle]
        with self.assertRaisesRegex(ValueError,'modelspace'):native_instances(d,broken)
    def test_unreadable_caption_rejected(self):
        with self.assertRaises(ValueError):readable('风墙\ufffd')
    def test_final_edge_identity_by_unique_native_paths(self):
        g=graph();prior=copy.deepcopy(g);prior['edges'][0]['edge_id']='E77'
        out,a=bind(g,[instance()],self.profile,prior)
        self.assertEqual(out['edges'][0]['edge_id'],'E77');self.assertEqual(a['contacts'][0]['edge_id'],'E77')

if __name__=='__main__':unittest.main()
