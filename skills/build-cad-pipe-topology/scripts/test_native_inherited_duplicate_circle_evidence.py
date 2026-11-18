import copy,json,tempfile,unittest
from pathlib import Path
import ezdxf
from native_line_path_evidence import LAYERS
from confirm_crossview_paths import sha
from native_inherited_duplicate_circle_evidence import collect


def fixture(folder):
    doc=ezdxf.new();model=doc.modelspace();layer=LAYERS['supply'];source='a'*64
    mains=[model.add_line((0,-50,0),(0,100,0),dxfattribs=dict(layer=layer)) for _ in range(2)]
    nodes=[dict(node_id='LOW',x=0,y=-50,node_type='endpoint',floor=3),dict(node_id='HIGH',x=0,y=100,node_type='endpoint',floor=3)];edges=[];metadata=[]
    for nid,y in [('C',0),('A',20)]:
        circle=model.add_circle((0,y,0),1,dxfattribs=dict(layer=layer));branch=model.add_line((-10,y,0),(-1,y,0),dxfattribs=dict(layer=layer))
        n=dict(node_id=nid,x=0,y=y,node_type='tee',system='supply',floor=3)
        nodes.extend([n,dict(node_id='D'+nid,x=-10,y=y,node_type='virtual_equipment',system='supply',floor=3)])
        edges.append(dict(edge_id='B'+nid,start_node_id='D'+nid,end_node_id=nid,system='supply',source_handles=[branch.dxf.handle],attribute_paths=[[[-10,y],[-1,y]]]))
        meta=dict(circle_handle=circle.dxf.handle,circle_layer=layer,line_system='supply',center=[0,y],source_rim=[-1,y],circle_z=0,main_z_at_center=0,branch_z_at_rim=0,
            source_graph_sha256='b'*64,screen_sha256='c'*64,graphic_radius_is_physical_length=False,physical_length='unknown',coincident_native_main_handles=[e.dxf.handle for e in mains],physical_main_identity='unresolved')
        metadata.append(meta)
    for eid,u,v,a,b in [('ML','LOW','C',[0,-50],[0,0]),('MC','C','A',[0,0],[0,20]),('MH','A','HIGH',[0,20],[0,100])]:
        edges.append(dict(edge_id=eid,start_node_id=u,end_node_id=v,system='supply',source_handles=[mains[0].dxf.handle],attribute_paths=[[a,b]]))
    def issue(path,point,branch,note,label):
        raw=dict(sourceHashes=dict(main_dxf=source),issue=dict(id=path.stem,label=label,note=note,edges=[branch],sourceBounds=[point[0]-2,point[1]-2,4,4]))
        path.write_text(json.dumps(raw),'utf8');return dict(issue=str(path),issue_sha256=sha(path),issue_id=path.stem)
    proof=issue(folder/'control.json',[0,0],'BC','confirmed connection','ERR-CONTROL')
    expert=dict(confirmed_by='expert',question='source connection?',answer='confirmed connection')
    calibration=dict(confirmed_by='technical_calibration',question='same complete source shape?',answer='yes',human_accepted=False)
    metadata[0].update(confirmation=expert,expert_issue_evidence=proof)
    metadata[1].update(confirmation=calibration,expert_control_circle=metadata[0]['circle_handle'],human_accepted=False)
    nodes[2]['expert_confirmed_circle']=metadata[0];nodes[4]['calibrated_duplicate_circle']=metadata[1]
    def root(nid,meta,confirmation):
        return dict(records=[dict(tee=nid,circle_handle=meta['circle_handle'],branch_edge='B'+nid,system='supply')],confirmation=confirmation,
            source_sha256=source,input_graph_sha256='b'*64,screen_sha256='c'*64,supply_return_independent=True,physical_length='unknown')
    graph=dict(nodes=nodes,edges=edges,metadata=dict(source_sha256=source),
        expertConfirmedCircleJunctionRepair=root('C',metadata[0],expert),sourceCalibratedDuplicateCircleRepair=root('A',metadata[1],calibration))
    external_issue=issue(folder/'external.json',[0,20],'BA','circle node omitted','ERR-EXTERNAL')
    external=dict(external_cases={'A':dict(external_issue,control_node_id='C')})
    return doc,graph,source,'d'*64,external


class Tests(unittest.TestCase):
    def test_expert_and_full_branch_calibration_preserve_ambiguity_and_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            doc,g,source,gh,_=fixture(Path(temp));before=copy.deepcopy(g)
            for nid in ('C','A'):
                result=collect(doc,g,nid,source,gh)
                self.assertEqual(len(result['junctions'][0]['source_rays']),3);self.assertFalse(result['physical_main_identity_resolved'])
                self.assertFalse(result['human_accepted']);self.assertFalse(result['physical_ports_verified'])
                self.assertIsNone(result['junctions'][0]['source_rays'][0]['physical_connector_length'])
            self.assertEqual(g,before)

    def test_native_system_Z_full_signature_source_issue_floor_or_incidence_changes_fail(self):
        for case in ('signature','main_Z','branch_Z','issue','bounds','floor','mixed','fourway','human','root','radius','opposite'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                doc,g,source,gh,_=fixture(Path(temp));node=next(n for n in g['nodes'] if n['node_id']=='A');meta=node['calibrated_duplicate_circle']
                if case=='signature':doc.entitydb[next(e for e in g['edges'] if e['edge_id']=='BA')['source_handles'][0]].dxf.start=(-11,20,0)
                elif case=='main_Z':doc.entitydb[meta['coincident_native_main_handles'][1]].dxf.start=(0,-50,1)
                elif case=='branch_Z':doc.entitydb[next(e for e in g['edges'] if e['edge_id']=='BA')['source_handles'][0]].dxf.end=(-1,20,1)
                elif case=='issue':Path(temp,'control.json').write_text('{}','utf8')
                elif case=='bounds':
                    p=Path(temp,'control.json');d=json.loads(p.read_text('utf8'));d['issue']['sourceBounds']=[20,20,1,1];p.write_text(json.dumps(d),'utf8')
                    next(n for n in g['nodes'] if n['node_id']=='C')['expert_confirmed_circle']['expert_issue_evidence']['issue_sha256']=sha(p)
                elif case=='floor':node['floor']=2
                elif case=='mixed':next(e for e in g['edges'] if e['edge_id']=='BA')['system']='return'
                elif case=='fourway':g['edges'].append(dict(edge_id='extra',start_node_id='A',end_node_id='DA',system='supply'))
                elif case=='human':meta['human_accepted']=True
                elif case=='root':g['sourceCalibratedDuplicateCircleRepair']['screen_sha256']='wrong'
                elif case=='radius':doc.entitydb[meta['circle_handle']].dxf.radius=2
                else:doc.modelspace().add_line((-20,20,0),(20,20,0),dxfattribs=dict(layer=LAYERS['return']))
                with self.assertRaises(ValueError):collect(doc,g,'A',source,gh)

    def test_legacy_edge_issue_uses_native_control_without_transferring_expert_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            doc,g,source,gh,policy=fixture(Path(temp));node=next(n for n in g['nodes'] if n['node_id']=='A');meta=node.pop('calibrated_duplicate_circle')
            edge=next(e for e in g['edges'] if e['edge_id']=='BA');edge['source_circle_connection']=dict(expert_issue='ERR-EXTERNAL',circle_handle=meta['circle_handle'],
                main_pipe_handle=meta['coincident_native_main_handles'][0],branch_pipe_handle=edge['source_handles'][0],branch_rim=meta['source_rim'],center=meta['center'],
                graphic_radius_not_physical_length=1,physical_length='unknown')
            result=collect(doc,g,'A',source,gh,policy);self.assertIsNotNone(result['control_evidence']);self.assertFalse(result['human_accepted'])
            with self.assertRaises(ValueError):collect(doc,g,'A',source,gh)
            edge['source_circle_connection']['graphic_radius_not_physical_length']=0
            with self.assertRaises(ValueError):collect(doc,g,'A',source,gh,policy)


if __name__=='__main__':unittest.main()
