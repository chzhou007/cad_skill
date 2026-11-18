import copy,unittest
from test_source_terminal_pair_inventory import SourcePairInventoryTest
from reconstruct_confirmed_equipment_pairs import prepare,rebuild,DECISION

def fixture():
    doc,g,inventory_scope=SourcePairInventoryTest().fixture();m=doc.modelspace();nodes={n['node_id']:n for n in g['nodes']}
    device=nodes['device'];device.update(x=150,y=-150,floor=2,label='device')
    m.add_text('device',dxfattribs={'insert':(150,-150)})
    rows=[];bindings=[]
    for system,x,y,offset in [('return',0,-1000,-1),('supply',300,-500,0)]:
        n=nodes[system];n.update(node_type='virtual_equipment',floor=2,ports=[dict(port_id=system+'-P1',system=system)])
        center=[x,y+offset];rim=[x,y+offset+100];circle=m.add_circle(center,100,dxfattribs={'layer':'空调冷冻水供水' if system=='return' else '空调冷冻水回水'})
        branch=m.add_line((x,0),rim,dxfattribs={'layer':'空调冷冻水供水' if system=='supply' else '空调冷冻水回水'})
        main=m.add_line((-200,y),(800,y),dxfattribs={'layer':branch.dxf.layer})
        terminal='end'+system;g['nodes'].append(dict(node_id=terminal,node_type='virtual_equipment',subtype='unresolved_source_terminal',system=system,floor=2,x=rim[0],y=rim[1]))
        for suffix,xx in [('A',-200),('B',800)]:g['nodes'].append(dict(node_id=system+suffix,node_type='tee',system=system,floor=2,x=xx,y=y))
        edge=next(e for e in g['edges'] if e['edge_id']=='E'+system)
        path=[[x,0],rim];edge.update(system=system,path=path,path_points=copy.deepcopy(path),attribute_paths=[copy.deepcopy(path)],source_handles=[branch.dxf.handle],start_port_id=system+'-P1',path_length=abs(rim[1]),equipment_names=[],equipment_counts={},start_floor=2,end_floor=2)
        g['edges'].append(dict(edge_id='M'+system,start_node_id=system+'A',end_node_id=system+'B',system=system,path=[[-200,y],[800,y]],attribute_paths=[[[-200,y],[800,y]]],path_length=1000,source_handles=[main.dxf.handle],equipment_names=['V'+system],equipment_counts={'valve':1},start_floor=2,end_floor=2))
        rows.append(dict(edge_id='M'+system,device_name='V'+system,equipment_type='valve',source_handle='VALVE'+system,x='500',y=str(y)))
        bindings.append(dict(system=system,interface_id=system,edge_id='E'+system,main_edge_id='M'+system,circle_handle=circle.dxf.handle,main_handle=main.dxf.handle,branch_handle=branch.dxf.handle,maximum_circle_main_offset_drawing_units=1.01 if system=='return' else .01))
    g['virtual_equipment_ports']=[];reviewed=copy.deepcopy(g)
    manifest=dict(source_sha256='S',images=[dict(sha256='IMAGE',equipment=['device'],window=[-500,1000,-1200,300])])
    reply=dict(sections=[dict(image=dict(sha256='IMAGE'),questions=[dict(id='Q',text='device：相邻供回水接口及同系统主管',answer=dict(decision=DECISION))])])
    policy=dict(source_sha256='S',graph_sha256='G',reply_sha256='REPLY',inventory_scope={k:inventory_scope[k] for k in ['pair_spacing','pair_tolerance','body_search_radius']},equipment=[dict(equipment_id='device',equipment_handle=device['source_handle'],question_id='Q',connections=bindings)])
    return doc,g,reviewed,rows,manifest,reply,policy

class EquipmentPairReconstructionTests(unittest.TestCase):
    def test_backtracking_main_does_not_create_false_three_ray_T(self):
        d,g,old,rows,m,r,p=fixture()
        for graph in (g,old):
            edge=next(e for e in graph['edges'] if e['edge_id']=='Mreturn');edge['path']=[[-200,-1000],[0,-1000],[-200,-1000]]
        with self.assertRaisesRegex(ValueError,'three distinct'):prepare(d,g,old,m,r,p,'S','G')
    def test_confirmed_pair_rebuilds_two_mains_and_preserves_native_offset(self):
        doc,g,old,rows,m,r,p=fixture();before=copy.deepcopy(g)
        connections,questions=prepare(doc,g,old,m,r,p,'S','G')
        out,assigned,audit=rebuild(doc,g,rows,connections,questions,p,'S','G')
        self.assertEqual(len(out['edges']),6);self.assertEqual(len(audit['records']),2)
        self.assertNotIn('supply',{n['node_id'] for n in out['nodes']});self.assertNotIn('return',{n['node_id'] for n in out['nodes']})
        for rec in audit['records']:
            incident=[e for e in out['edges'] if rec['tee'] in (e.get('start_node_id'),e.get('end_node_id'))]
            self.assertEqual(len(incident),3);self.assertEqual({e['system'] for e in incident},{rec['system']})
            self.assertEqual(next(e for e in out['edges'] if e['edge_id']==rec['branch_edge'])['start_node_id'],'device')
        self.assertAlmostEqual(next(x for x in audit['records'] if x['system']=='return')['actual_circle_main_offset'],1)
        self.assertEqual({x['device_name'] for x in assigned},{'Vreturn','Vsupply'});self.assertEqual(g,before)
        self.assertFalse(out['metadata']['hil_ready'])
    def test_unconfirmed_image_or_changed_route_cannot_reuse_reply(self):
        for kind in ('answer','image','route'):
            d,g,old,rows,m,r,p=fixture()
            if kind=='answer':r['sections'][0]['questions'][0]['answer']['decision']='部分成立'
            elif kind=='image':r['sections'][0]['image']['sha256']='OTHER'
            else:g['edges'][0]['path_length']+=1
            with self.assertRaises(ValueError):prepare(d,g,old,m,r,p,'S','G')
    def test_offset_bound_non_node_boundary_and_caption_are_protected(self):
        for kind in ('offset','boundary','caption'):
            d,g,old,rows,m,r,p=fixture();b=p['equipment'][0]['connections'][0]
            if kind=='offset':b['maximum_circle_main_offset_drawing_units']=.5
            elif kind=='boundary':g['boundary_anchors']=[dict(source_marker_handles=[b['circle_handle']])]
            else:d.modelspace().add_text('device',dxfattribs={'insert':(155,-150)})
            with self.assertRaises(ValueError):prepare(d,g,old,m,r,p,'S','G')
    def test_cross_system_branch_and_ordinary_crossing_do_not_connect(self):
        for kind in ('system','circle'):
            d,g,old,rows,m,r,p=fixture();b=p['equipment'][0]['connections'][0]
            if kind=='system':d.entitydb[b['branch_handle']].dxf.layer='空调冷冻水供水'
            else:d.entitydb[b['circle_handle']].destroy()
            with self.assertRaises(ValueError):prepare(d,g,old,m,r,p,'S','G')

if __name__=='__main__':unittest.main()
