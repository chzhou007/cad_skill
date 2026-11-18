import copy,dataclasses,unittest
import ezdxf
from crossview_equipment_branch_inventory import service_route
from native_touching_plan_path_chunks import collect as touching
from native_line_path_evidence import LAYERS
from match_named_riser_floor_segments import correspond,through_role,implementation_hashes


@dataclasses.dataclass
class Removal:
    system:str
    vent_port:tuple
    junction:tuple


def fixture():
    docs={v:ezdxf.new() for v in ('plan','iso')};graphs={v:dict(metadata=dict(source_sha256=v),nodes=[],edges=[]) for v in docs}
    named={v:dict(records=[]) for v in docs};removed=[];contracts=[];specs=[]
    def node(v,nid,xy,floor=3,kind='tee'):
        graphs[v]['nodes'].append(dict(node_id=nid,node_type=kind,floor=floor,x=xy[0],y=xy[1]))
    def edge(v,eid,a,b,paths,system):
        graphs[v]['edges'].append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system=system,attribute_paths=paths))
    for v,point in [('plan',(30,30)),('iso',(400,40))]:node(v,'D',point,kind='equipment')
    for system,identifier,y,x in [('supply','CHWS1',0,100),('return','CHWR1',50,200)]:
        p=system;m=docs['plan'].modelspace();layer=LAYERS[system]
        for tag,point,kind in [('R',(0,y),'interface'),('N',(10,y),'tee'),('T',(10,y+10),'tee'),('L',(10,y-10),'interface'),('U',(10,y+20),'interface')]:node('plan',p+tag,point,kind=kind)
        m.add_line((0,y),(10,y),dxfattribs=dict(layer=layer));m.add_line((10,y-10),(10,y+20),dxfattribs=dict(layer=layer));m.add_line((10,y+10),(30,30),dxfattribs=dict(layer=layer))
        edge('plan',p+'RIF',p+'R',p+'N',[[[1,y],[10,y]]],system)
        edge('plan',p+'BRIDGE',p+'N',p+'T',[[[10,y],[10,y+5]],[[10,y+5],[10,y+10]]],system)
        edge('plan',p+'LOW',p+'L',p+'N',[[[10,y-10],[10,y]]],system)
        edge('plan',p+'UP',p+'T',p+'U',[[[10,y+10],[10,y+20]]],system)
        edge('plan',p+'EQ',p+'T','D',[[[10,y+10],[30,30]]],system)
        m=docs['iso'].modelspace()
        for tag,point,floor,kind in [('M',(x,0),2,'tee'),('N',(x+10,40),3,'tee'),('T',(x+20,50),3,'tee'),('L',(x,30),3,'interface'),('U',(x+30,60),3,'interface')]:node('iso',p+tag,point,floor,kind)
        vert=m.add_line((x,0),(x,45),dxfattribs=dict(layer=layer));m.add_line((x,40),(x+10,40),dxfattribs=dict(layer=layer))
        m.add_line((x,30),(x+10,40),dxfattribs=dict(layer=layer));m.add_line((x+10,40),(x+30,60),dxfattribs=dict(layer=layer));m.add_line((x+20,50),(400,40),dxfattribs=dict(layer=layer))
        edge('iso',p+'MIX',p+'M',p+'N',[[[x,0],[x,40],[x+10,40]]],system)
        edge('iso',p+'BRIDGE',p+'N',p+'T',[[[x+10,40],[x+20,50]]],system)
        edge('iso',p+'LOW',p+'L',p+'N',[[[x,30],[x+10,40]]],system)
        edge('iso',p+'UP',p+'T',p+'U',[[[x+20,50],[x+30,60]]],system)
        edge('iso',p+'EQ',p+'T','D',[[[x+20,50],[400,40]]],system)
        named['plan']['records'].append(dict(identifier=identifier,system=system,target_kind='plan_riser_circle',target=dict(node_id=p+'R',floor=3)))
        named['iso']['records'].append(dict(identifier=identifier,system=system,leader=dict(target_point=[x,43,0])))
        removed.append(Removal(system,(x,45),(x,40)))
        contracts.append(dict(system=system,middle_T=p+'M',segments=[dict(side='upper',edge_id=p+'MIX',segment_index=0,floor_pair=[2,3],scope_points=[[x,0],[x,40]],source_line_handle=vert.dxf.handle)]))
        specs.append(dict(identifier=identifier,axis_mixed_edge=p+'MIX',plan_bridge_edge=p+'BRIDGE',axis_bridge_edge=p+'BRIDGE'))
    inventory=dict(records=[dict(equipment_id='D',floor=3,ready_for_mapping_comparison=True,
        views={v:dict(services={s:dict(trace=service_route(g,'D',s)) for s in ('supply','return')}) for v,g in graphs.items()})])
    hashes={v:dict(source_sha256=v,graph_sha256=v+'-graph') for v in docs}
    ids=[eid for spec in specs for eid in [spec['identifier'].replace('CHWS1','supply').replace('CHWR1','return')+'RIF',spec['plan_bridge_edge']]]
    source=touching(docs['plan'],graphs['plan'],dict(view_kind='floor_plan',floor=3,edges=ids,**hashes['plan']),'plan','plan-graph')
    policy=dict(floor=3,equipment_id='D',services=specs)
    return docs,graphs,inventory,named,dict(through_contracts=contracts),source,removed,policy,hashes


class Tests(unittest.TestCase):
    def test_native_roles_names_and_independent_services_map_only_the_horizontal_suffix(self):
        args=fixture();before=copy.deepcopy(args[1]);result=correspond(*args)
        self.assertEqual(len(result['records']),4);self.assertEqual(len(result['floor_interface_correspondences']),2)
        self.assertEqual(result['local_graphs_mutated'],False);self.assertEqual(args[1],before)
        for row in result['records']:
            selected=row['iso_segment_scopes'][0]
            if row['kind'].endswith('approach'):
                self.assertEqual(selected['segment_indices'],[1]);self.assertFalse(selected['whole_local_edge'])
            self.assertFalse(row['whole_axis_DN_assigned']);self.assertFalse(row['whole_axis_length_assigned'])
    def test_wrong_names_floor_ready_state_column_and_bridge_cannot_be_overruled(self):
        for case in ('repeat_name','wrong_name','floor','unready','column','bridge','vertical','touching'):
            args=list(fixture());docs,g,inv,names,riser,touch,removed,policy,hashes=args
            if case=='repeat_name':names['iso']['records'].append(copy.deepcopy(names['iso']['records'][0]))
            elif case=='wrong_name':names['iso']['records'][0]['identifier']='CHWS2'
            elif case=='floor':policy['floor']=2
            elif case=='unready':inv['records'][0]['ready_for_mapping_comparison']=False
            elif case=='column':removed[0].junction=(100,41)
            elif case=='bridge':policy['services'][0]['axis_bridge_edge']='supplyLOW'
            elif case=='vertical':riser['through_contracts'][0]['segments'][0]['segment_index']=1
            else:touch['normalizations'][0]['added_span_units']=1
            with self.subTest(case=case),self.assertRaises(ValueError):correspond(*args)
    def test_split_native_LINE_endpoints_need_matching_XYZ_not_only_planar_touch(self):
        args=fixture();docs,g,inv,names,riser,touch,removed,policy,hashes=args
        through_role(docs['iso'],g['iso'],'supplyN','supply','iso','iso-graph')
        line=next(e for e in docs['iso'].modelspace().query('LINE') if e.dxf.start.x==100 and e.dxf.start.y==30)
        line.dxf.start=(100,30,10);line.dxf.end=(110,40,10)
        with self.assertRaises(ValueError):through_role(docs['iso'],g['iso'],'supplyN','supply','iso','iso-graph')
    def test_dependency_closure_keeps_old_naming_riser_and_new_chunk_rules(self):
        for name in ('match_named_riser_floor_paths.py','native_axis_riser_DN_scopes.py','native_touching_plan_path_chunks.py','native_named_riser_evidence.py'):
            self.assertIn(name,implementation_hashes())


if __name__=='__main__':unittest.main()
