import copy,math,unittest
from test_match_named_external_boundary_paths import fixture as mapping_fixture
from match_named_external_boundary_paths import match
from attach_external_feed_plan_attributes import append,ROOT,FIELD,NODE_FIELD,ATTRIBUTE_MODE


def fixture():
    parts=list(mapping_fixture());graphs=parts[0]
    for coverage in parts[-1]['edges']:
        path=next(e for e in graphs['iso']['edges'] if e['edge_id']==coverage['edge_id'])['attribute_paths'][0]
        for segment in coverage['segments']:segment.update(start=path[segment['index']],end=path[segment['index']+1])
    mapping=match(*parts);local=graphs['iso'];parent=copy.deepcopy(local);parent['retained_old_root']={'unchanged':True}
    parent['edges'][-1]['cross_view_attributes']={'old_DN':200,'old_XY':123}
    attrs=dict(mode=ATTRIBUTE_MODE,source_sha256=mapping['source_sha256'],graph_sha256=mapping['graph_sha256'],mapping_sha256='b'*64,local_graphs_mutated=False,physical_values_fused=False,human_accepted=False,hil_ready=False,installed_whole_lengths_assigned=0,records=[])
    pe={e['edge_id']:e for e in graphs['plan']['edges']}
    for record in mapping['records']:
        row=copy.deepcopy(record);eid=row['plan_edges'][0];path=pe[eid]['attribute_paths'][0];indices=[s['index'] for s in row['native_axis_path_coverage']['segments'] if s['status']=='single_source_line_covers']
        row.update(diameter=dict(edge_id=eid,system=row['system'],nominal_mm=450,status='direct_plan_DN',scope_paths=[path]),horizontal_projection=dict(value_mm=60,pieces=[dict(plan_edge=eid,source_line_handle='LINE',length_mm=60,points=path)],joint_graphic_spans_added=False,inline_joint_interior_length_mm=None),
            axis_pipe_segment_indices=indices,axis_inline_gap_segment_indices=[1],inline_interiors_unknown=True,complete_horizontal_centerline_route_mm=None,installed_whole_edge_length_mm=None,
            whole_axis_edge_DN_selected=False,axis_named_DN_used_as_plan_seed=False,physical_ports_verified=False)
        attrs['records'].append(row)
    return parent,local,mapping,attrs,dict(plan=parts[2],axis=parts[3]),dict(parent='a'*64,mapping='b'*64,attributes='c'*64,plan_destinations='d'*64,axis_destinations='e'*64)


class Tests(unittest.TestCase):
    def test_four_pipe_scopes_and_one_context_preserve_every_old_node_edge_and_attribute(self):
        args=fixture();before=copy.deepcopy(args);graph,stage=append(*args);self.assertEqual(args,before)
        self.assertEqual(graph['retained_old_root'],args[0]['retained_old_root']);self.assertEqual(stage['added_external_pipe_scopes'],4);self.assertEqual(stage['source_declared_boundary_contexts'],1)
        for old,new in zip(args[0]['nodes'],graph['nodes']):self.assertEqual({k:v for k,v in new.items() if k!=NODE_FIELD},old)
        for old,new in zip(args[0]['edges'],graph['edges']):
            self.assertEqual({k:v for k,v in new.items() if k!=FIELD},old)
            if FIELD in new:
                r=new[FIELD];self.assertEqual(r['nominal_mm'],450);self.assertEqual(r['segment_indices'],[0,2]);self.assertEqual(r['horizontal_projection']['value_mm'],60)
                self.assertIsNone(r['installed_whole_edge_length_mm']);self.assertIsNone(r['complete_horizontal_centerline_route_mm']);self.assertFalse(r['physical_external_connection_verified'])
        context=next(n[NODE_FIELD] for n in graph['nodes'] if NODE_FIELD in n)
        self.assertEqual(context['destination'],'室外冷冻站');self.assertEqual(len(context['ports']),4);self.assertFalse(context['direct_connection_between_ports']);self.assertFalse(context['physical_equipment']);self.assertEqual(graph[ROOT],stage)
    def test_marker_gap_wrong_port_DN_unknown_length_or_prior_geometry_changes_block(self):
        for case in ('mapping','source','scope','metric','whole','DN','status','port','destination','node','old','duplicate','connection'):
            args=list(fixture());row=args[3]['records'][0];eid=row['iso_edges'][0];edge=next(e for e in args[0]['edges'] if e['edge_id']==eid)
            if case=='mapping':args[3]['mapping_sha256']='stale'
            elif case=='source':args[4]['axis']['source_sha256']='stale'
            elif case=='scope':row['axis_pipe_segment_indices'].append(row['axis_display_only_segment_index'])
            elif case=='metric':row['horizontal_projection']['pieces'][0]['length_mm']=0
            elif case=='whole':row['installed_whole_edge_length_mm']=0
            elif case=='DN':row['diameter']['nominal_mm']=0
            elif case=='status':row['diameter']['status']='conflict'
            elif case=='port':edge['end_port_id']='wrong'
            elif case=='destination':args[4]['axis']['destination']='elsewhere'
            elif case=='node':next(n for n in args[0]['nodes'] if n['node_id']==row['axis_boundary_node'])['x']+=1
            elif case=='old':edge['equipment_names']=['new']
            elif case=='duplicate':args[3]['records'].append(copy.deepcopy(row))
            else:row['external_ports_connected_to_each_other']=True
            with self.subTest(case=case),self.assertRaises(ValueError):append(*args)

if __name__=='__main__':unittest.main()
