import copy,unittest
from attach_anchored_floor_main_attributes import append,ROOT,FIELD

def fixture():
    nodes=[dict(node_id='T'+str(i),node_type='tee',floor=1,x=i*5,y=0) for i in range(3)]
    edges=[dict(edge_id='I'+str(i),start_node_id='T'+str(i),end_node_id='T'+str(i+1),floor_start=1,floor_end=1,system='supply',attribute_paths=[[[i*5,0],[(i+1)*5,0]]]) for i in range(2)]
    local=dict(nodes=nodes,edges=edges);parent=copy.deepcopy(local)
    parent['edges'][0]['cross_view_attributes']=dict(mapping_kind='main_between_equipment_branches',floor=1,plan_edges=['P0'],diameter=dict(plan_drawn_nominal_mm=200),horizontal_projection=dict(value_mm=5))
    rows=[dict(mapping_id='M'+str(i),floor=1,system='supply',plan_edges=['P'+str(i)],iso_edges=['I'+str(i)],iso_start='T'+str(i),iso_end='T'+str(i+1)) for i in range(2)]
    mapping=dict(floor=1,records=rows,plan_graph_sha256='p',iso_graph_sha256='i',source_sha256=dict(plan='s',iso='t'),historical_main_paths=1,additional_main_paths=1,
        evidence=dict(historical_scope_lineage=[dict(current_main_mapping_id='M0')],preserved_floor_attributes=dict(named_main_mapping_ids=[])))
    values=[dict(mapping_id='M'+str(i),floor=1,system='supply',plan_edges=['P'+str(i)],iso_edges=['I'+str(i)],diameter=dict(edge_id='P'+str(i),system='supply',nominal_mm=200 if i==0 else 100,status='direct_plan_DN',lineage=[{}]),
        horizontal_projection=dict(value_mm=5,pieces=[dict(length_mm=5)]),inline_interiors_unknown=False) for i in range(2)]
    hashes=dict(mapping='a'*64,attributes='b'*64,parent='c'*64)
    attrs=dict(mapping_sha256=hashes['mapping'],graph_sha256=dict(plan='p',iso='i'),source_sha256=mapping['source_sha256'],physical_values_fused=False,human_accepted=False,records=values)
    return parent,local,{},mapping,attrs,hashes,[0,45,135]

class Tests(unittest.TestCase):
    def test_adds_only_new_main_and_keeps_entire_parent_geometry_and_values(self):
        args=fixture();before=copy.deepcopy(args);graph,proof=append(*args)
        self.assertEqual(args,before);self.assertEqual(graph['nodes'],args[0]['nodes']);self.assertEqual(graph['edges'][0],args[0]['edges'][0])
        new=graph['edges'][1][FIELD];self.assertEqual(new['nominal_mm'],100);self.assertEqual(new['complete_horizontal_centerline_route_mm'],5);self.assertIsNone(new['installed_whole_edge_length_mm']);self.assertFalse(new['human_accepted'])
        self.assertEqual({k:v for k,v in graph['edges'][1].items() if k!=FIELD},args[0]['edges'][1]);self.assertEqual(graph[ROOT],proof)
    def test_conflict_and_inline_partial_length_never_gain_unknown_whole_values(self):
        args=fixture();row=args[4]['records'][1];row['diameter'].update(nominal_mm=None,status='conflict',lineage=[dict(nominal_mm=200),dict(nominal_mm=450)])
        row['inline_interiors_unknown']=True;row['horizontal_projection'].update(joint_graphic_spans_added=False,inline_joint_interior_length_mm=None)
        graph,proof=append(*args);new=graph['edges'][1][FIELD]
        self.assertIsNone(new['nominal_mm']);self.assertEqual(len(new['diameter_evidence']['lineage']),2);self.assertIsNone(new['complete_horizontal_centerline_route_mm']);self.assertEqual(proof['conflict_DN_records'],1)
    def test_stale_mapping_cross_floor_plumb_writer_and_old_value_regression_block(self):
        for case in ('mapping','old_value','raw_geometry','plumb','floor','writer','missing','joint_length','duplicate'):
            args=list(fixture());parent,local,_,mapping,attrs,hashes,angles=args
            if case=='mapping':attrs['mapping_sha256']='stale'
            elif case=='old_value':attrs['records'][0]['diameter']['nominal_mm']=250
            elif case=='raw_geometry':parent['edges'][1]['system']='return'
            elif case=='plumb':angles[:]=[90]
            elif case=='floor':local['edges'][1]['floor_end']=2;parent['edges'][1]['floor_end']=2
            elif case=='writer':parent['edges'][1]['axis_riser_attributes']=[]
            elif case=='missing':attrs['records'].pop()
            elif case=='duplicate':attrs['records'].append(copy.deepcopy(attrs['records'][1]))
            else:attrs['records'][1]['inline_interiors_unknown']=True;attrs['records'][1]['horizontal_projection']['joint_graphic_spans_added']=True
            with self.subTest(case=case),self.assertRaises(ValueError):append(*args)
if __name__=='__main__':unittest.main()
