import copy,dataclasses,unittest
import ezdxf
from native_line_path_evidence import LAYERS
from crossview_equipment_branch_inventory import service_route
from match_named_riser_floor_paths import correspond,implementation_hashes


@dataclasses.dataclass
class Removal:
    system:str
    vent_port:tuple
    junction:tuple
    length:float=5
    action:str='trim'


def fixture():
    docs={v:ezdxf.new() for v in ['plan','iso']};graphs={v:dict(metadata=dict(source_sha256=v),nodes=[],edges=[]) for v in docs}
    for view in graphs:graphs[view]['nodes'].append(dict(node_id='D',node_type='equipment',floor=2,x=10 if view=='plan' else 110,y=-10 if view=='plan' else 10))
    named={v:dict(records=[]) for v in docs};contracts=[];removed=[]
    def node(view,nid,p,floor=2,kind='physical_junction'):
        graphs[view]['nodes'].append(dict(node_id=nid,node_type=kind,floor=floor,x=p[0],y=p[1]))
    def edge(view,eid,a,b,points,system):
        graphs[view]['edges'].append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system=system,attribute_paths=[points]))
    for system,identifier,y,x in [('supply','CHWS1',0,100),('return','CHWR1',50,200)]:
        p=system;layer=LAYERS[system]
        for tag,point,kind in [('R',[0,y],'interface'),('T',[10,y],'physical_junction'),('X',[20,y],'interface')]:node('plan',p+tag,point,kind=kind)
        docs['plan'].modelspace().add_circle((0,y),1,dxfattribs=dict(layer=layer))
        docs['plan'].modelspace().add_line((0,y),(20,y),dxfattribs=dict(layer=layer));docs['plan'].modelspace().add_line((10,y),(10,-10),dxfattribs=dict(layer=layer))
        edge('plan',p+'RIF',p+'R',p+'T',[[1,y],[10,y]],system);edge('plan',p+'MAIN',p+'T',p+'X',[[10,y],[20,y]],system);edge('plan',p+'EQ',p+'T','D',[[10,y],[10,-10]],system)
        for tag,point,floor,kind in [('M',[x,20],2,'physical_junction'),('T',[x+10,20],2,'physical_junction'),('X',[x+20,20],2,'interface'),('L',[x-5,0],1,'interface'),('U',[x+5,40],3,'interface')]:node('iso',p+tag,point,floor,kind)
        m=docs['iso'].modelspace();m.add_line((x,0),(x,45),dxfattribs=dict(layer=layer));m.add_line((x-5,0),(x,0),dxfattribs=dict(layer=layer));m.add_line((x,40),(x+5,40),dxfattribs=dict(layer=layer))
        m.add_line((x,20),(x+20,20),dxfattribs=dict(layer=layer));m.add_line((x+10,20),(110,10),dxfattribs=dict(layer=layer))
        edge('iso',p+'LOW',p+'L',p+'M',[[x-5,0],[x,0],[x,20]],system);edge('iso',p+'UP',p+'M',p+'U',[[x,20],[x,40],[x+5,40]],system)
        edge('iso',p+'RIF',p+'M',p+'T',[[x,20],[x+10,20]],system);edge('iso',p+'MAIN',p+'T',p+'X',[[x+10,20],[x+20,20]],system);edge('iso',p+'EQ',p+'T','D',[[x+10,20],[110,10]],system)
        named['plan']['records'].append(dict(identifier=identifier,system=system,target_kind='plan_riser_circle',target=dict(node_id=p+'R',floor=2)))
        named['iso']['records'].append(dict(identifier=identifier,system=system,leader=dict(target_point=[x,43,0])))
        removed.append(Removal(system,(x,45),(x,40)))
        contracts.append(dict(system=system,middle_T=p+'M',non_through_branch=p+'RIF',segments=[dict(side='upper',edge_id=p+'UP')]))
    inventory=dict(records=[dict(equipment_id='D',floor=2,ready_for_mapping_comparison=True,views={v:dict(services={s:dict(trace=service_route(graphs[v],'D',s)) for s in ['supply','return']}) for v in docs})])
    policy=dict(equipment_id='D',floor=2,identifiers=['CHWS1','CHWR1']);hashes={v:dict(source_sha256=v,graph_sha256=v+'-graph') for v in docs}
    return docs,graphs,inventory,named,dict(through_contracts=contracts),removed,policy,hashes


class Tests(unittest.TestCase):
    def test_native_names_actual_riser_Ts_and_independent_device_services_match_without_metrics(self):
        args=fixture();before=copy.deepcopy(args[1]);rows=correspond(*args)
        self.assertEqual(len(rows),2);self.assertEqual(args[1],before)
        for r in rows:
            self.assertEqual(r['system']+'RIF',r['plan_edges'][0]);self.assertEqual(r['system']+'RIF',r['iso_edges'][0]);self.assertIsNone(r['physical_length_mm'])
            self.assertFalse(r['physical_port_verified']);self.assertFalse(r['plan_glyph_radius_added_to_length']);self.assertFalse(r['human_accepted'])
    def test_same_equipment_does_not_overrule_wrong_or_repeated_named_riser(self):
        for case in ['identifier','duplicate','system','vent','column','floor','branch_role','unready','trace']:
            docs,g,inv,names,risers,removed,p,h=fixture()
            if case=='identifier':names['iso']['records'][0]['identifier']='CHWS2'
            elif case=='duplicate':names['iso']['records'].append(copy.deepcopy(names['iso']['records'][0]))
            elif case=='system':names['iso']['records'][0]['system']='return'
            elif case=='vent':removed[0].junction=(100,42)
            elif case=='column':risers['through_contracts'].append(copy.deepcopy(risers['through_contracts'][0]))
            elif case=='floor':p['floor']=3
            elif case=='branch_role':risers['through_contracts'][0]['non_through_branch']='OTHER'
            elif case=='unready':inv['records'][0]['ready_for_mapping_comparison']=False
            else:inv['records'][0]['views']['plan']['services']['supply']['trace']['tee']='OTHER'
            with self.subTest(case=case),self.assertRaises(ValueError):correspond(docs,g,inv,names,risers,removed,p,h)
    def test_disconnected_or_unsupported_native_approach_does_not_map_by_name(self):
        docs,g,inv,names,risers,removed,p,h=fixture();e=next(e for e in g['iso']['edges'] if e['edge_id']=='supplyRIF');e['attribute_paths'][0][0][1]+=1
        with self.assertRaises(ValueError):correspond(docs,g,inv,names,risers,removed,p,h)
    def test_dependency_closure_retains_old_riser_and_service_readers(self):
        hashes=implementation_hashes()
        for name in ['native_axis_riser_DN_scopes.py','native_named_riser_evidence.py','crossview_equipment_branch_inventory_v2.py','legacy_v17/analyze_graph.py']:
            self.assertIn(name,hashes)


if __name__=='__main__':unittest.main()
