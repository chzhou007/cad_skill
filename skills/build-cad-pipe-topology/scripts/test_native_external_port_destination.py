import copy,math,unittest
from test_native_external_pipe_destination import fixture as frontier_fixture
from native_external_port_destination import collect,LAYERS


def fixture(angle=0):
    doc,graph,policy,sh,gh=frontier_fixture(angle);marker=doc.entitydb[policy['marker_handle']];vertices=list(marker.get_points('xy'))
    centre=[(vertices[0][i]+vertices[-1][i])/2 for i in (0,1)];old_nodes={n['node_id']:n for n in graph['nodes']};ports=[]
    for spec,edge in zip(policy['members'],graph['edges']):
        old=old_nodes[spec.pop('node_id')];pid=old['node_id']+'-port';spec.update(port_id=pid,edge_id=edge['edge_id'])
        ports.append(dict(port_id=pid,node_id='V',system=edge['system'],source_marker_handle=marker.dxf.handle,x=old['x'],y=old['y']))
        edge.update(end_node_id='V',end_port_id=pid,source_insert_handle=marker.dxf.handle);edge['attribute_paths'][0].append(centre)
    graph['nodes']=[n for n in graph['nodes'] if n['node_type']=='tee']+[dict(node_id='V',node_type='virtual_equipment',subtype='external_system_interface',floor=1,x=centre[0],y=centre[1],ports=ports,source_marker_handle=marker.dxf.handle)]
    policy['node_id']='V'
    return doc,graph,policy,sh,gh


class Tests(unittest.TestCase):
    def test_separate_named_ports_replay_through_rotations_without_node_merge(self):
        for angle in (0,90,180,270):
            with self.subTest(angle=angle):
                args=fixture(angle);before=copy.deepcopy(args[1]);data=collect(*args)
                self.assertEqual(args[1],before);self.assertEqual(len(data['records']),4);self.assertFalse(data['common_marker_creates_pipe_connection'])
                self.assertEqual(data['new_connections_added'],0);self.assertEqual(len({r['port_id'] for r in data['records']}),4)
                self.assertTrue(all(r['physical_length_mm'] is None and not r['physical_port_verified'] and not r['whole_edge_DN_verified'] for r in data['records']))
    def test_caption_without_zhi_can_target_marker_segment_interior(self):
        args=fixture();doc,graph,p=args[:3];caption=doc.entitydb[p['caption']['text_handle']];caption.dxf.text='接室外冷冻站';p['caption']['expected_text']=caption.dxf.text
        doc.entitydb[p['caption']['leader_handle']].dxf.end=(35,0,0)
        self.assertEqual(collect(*args)['destination'],'室外冷冻站')
    def test_wrong_service_missing_port_graph_span_extra_pipe_or_native_leader_fail(self):
        for case in ('colour','leader','port','partial','extra','display','pipe','marker','real_equipment','label','Z','duplicate'):
            args=fixture();doc,graph,p=args[:3];spec=p['members'][0];edge=graph['edges'][0];node=graph['nodes'][-1]
            if case=='colour':doc.entitydb[spec['source_line_handle']].dxf.layer=LAYERS['return']
            elif case=='leader':doc.entitydb[spec['leader_handle']].dxf.end=(12,0,0)
            elif case=='port':edge['end_port_id']='wrong'
            elif case=='partial':p['members'].pop()
            elif case=='extra':doc.modelspace().add_line((80,40,0),(80,0,0),dxfattribs=dict(layer=LAYERS['supply']))
            elif case=='display':edge['attribute_paths'][0][-1]=[999,0]
            elif case=='pipe':edge['attribute_paths'][0][0]=[999,60]
            elif case=='marker':doc.entitydb[p['marker_handle']].closed=True
            elif case=='real_equipment':node['node_type']='equipment'
            elif case=='label':spec['identifier']='CHWS99'
            elif case=='Z':doc.entitydb[spec['source_line_handle']].dxf.end=(10,0,100)
            else:node['ports'].append(copy.deepcopy(node['ports'][0]))
            with self.subTest(case=case),self.assertRaises(ValueError):collect(*args)

if __name__=='__main__':unittest.main()
