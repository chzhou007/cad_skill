import copy,unittest
import ezdxf
from ordered_anchor_branch_paths import discover,retained_boundary_geometry,measure_branch

def fixture():
    def graph(axis=False):
        prefix='I'if axis else'P';nodes=[dict(node_id=prefix+str(i),node_type='tee',floor=3,x=i*10,y=0)for i in range(3)]
        if axis:nodes.append(dict(node_id='V',node_type='virtual_equipment',subtype='external_system_interface',floor=3,x=10,y=10))
        edges=[dict(edge_id=prefix+'M'+str(i),start_node_id=prefix+str(i),end_node_id=prefix+str(i+1),system='supply',attribute_paths=[[[i*10,0],[(i+1)*10,0]]])for i in range(2)]
        edges.append(dict(edge_id=prefix+'B',start_node_id=prefix+'1',end_node_id='V'if axis else None,end_boundary_id=None if axis else'B',system='supply',attribute_paths=[[[10,1],[10,10]]]))
        return dict(nodes=nodes,edges=edges,boundary_anchors=[]if axis else[dict(boundary_id='B',kind='expert_non_node_source_boundary')])
    graphs=dict(plan=graph(),iso=graph(True));proof=dict(groups=[dict(mapping_id='G',floor=3,system='supply',records=[dict(plan_edge_id='PM0',axis_edge_id='IM0'),dict(plan_edge_id='PM1',axis_edge_id='IM1')],internal_main_junction_correspondence=[dict(plan_node='P1',axis_node='I1')])]);parent=[dict(plan_edges=['PM0','PM1'],iso_edges=['IM0','IM1'])]
    return graphs,proof,parent

class Tests(unittest.TestCase):
    def test_native_plan_reader_receives_source_service_and_excludes_unknown_boundary_length(self):
        from batch_native_path_coverage import collect
        doc=ezdxf.new();line=doc.modelspace().add_line((0,0),(5,0),dxfattribs=dict(layer='空调冷冻水供水'));edge=dict(edge_id='P',system='supply',start_node_id='T',end_node_id=None,end_boundary_id='B',attribute_paths=[[[0,0],[5,0]]],source_handles=[line.dxf.handle])
        graph=dict(metadata=dict(source_sha256='SOURCE'),nodes=[dict(node_id='T',floor=3,node_type='tee',x=0,y=0)],edges=[edge],boundary_anchors=[dict(boundary_id='B')]);before=copy.deepcopy(graph)
        proof=collect(doc,graph,['P'],'SOURCE','GRAPH');row=dict(system='supply',routes=dict(plan=dict(edges=['P'])))
        value=measure_branch(graph,proof,row,dict(plan_window=[-1,10,-1,1]));self.assertEqual(value['value_mm'],5);self.assertIsNone(value['installed_whole_edge_length_mm']);self.assertEqual(graph,before)
        row['system']='return'
        with self.assertRaises(ValueError):measure_branch(graph,proof,row,dict(plan_window=[-1,10,-1,1]))
    def test_expands_all_proved_anchors_without_equipment_identity_node_creation_or_self_feedback(self):
        args=fixture();before=copy.deepcopy(args);records,pending=discover(*args)
        self.assertEqual(len(records),1);self.assertEqual(pending,[]);self.assertEqual(records[0]['routes']['plan']['terminal_kind'],'source_boundary');self.assertFalse(records[0]['physical_port_verified']);self.assertIsNone(records[0]['whole_axis_physical_length_mm']);self.assertEqual(args,before)
    def test_already_used_or_wrong_service_unresolved_and_cross_floor_are_pending(self):
        for defect in('used','service','review','floor','equipment'):
            graphs,proof,parent=fixture()
            if defect=='used':parent.append(dict(plan_edges=['PB'],iso_edges=['IB']))
            elif defect=='service':graphs['plan']['edges'][-1]['system']='return'
            elif defect=='review':graphs['plan']['nodes'][1]['review_required']=True
            elif defect=='floor':graphs['iso']['nodes'][-1]['floor']=2
            else:graphs['iso']['nodes'][-1]['node_type']='equipment'
            with self.subTest(defect=defect):
                rows,pending=discover(graphs,proof,parent);self.assertEqual(rows,[]);self.assertEqual(len(pending),1)
    def test_existing_non_node_marker_rounding_and_auxiliary_Z_are_not_reinterpreted_as_capped_physical_port(self):
        doc=ezdxf.new();m=doc.modelspace();pipe=m.add_line((0,0,20),(0,10,21),dxfattribs=dict(layer='空调冷冻水供水'));a=m.add_line((-2,10.3,36),(2,10.3,36),dxfattribs=dict(layer='MARK'));b=m.add_line((-1,11.3,36),(1,11.3,36),dxfattribs=dict(layer='MARK'))
        boundary=dict(kind='expert_non_node_source_boundary',expert_issue='EXPERT',source_marker_kind='two_bar',source_pipe_handle=pipe.dxf.handle,source_marker_handles=[a.dxf.handle,b.dxf.handle],source_marker_lengths=[4,2],source_marker_spacing=1,source_marker_layer='MARK',source_marker_z=[36,36],source_pipe_endpoint_z=21,x=0,y=10);edge=dict(system='supply',source_handles=[pipe.dxf.handle])
        result=retained_boundary_geometry(doc,boundary,edge);self.assertFalse(result['new_capped_or_remote_role_assigned']);self.assertFalse(result['native_Z_used_as_physical_elevation']);self.assertIsNone(result['physical_length_mm'])
        a.dxf.start=(-2,11,36);a.dxf.end=(2,11,36)
        with self.assertRaises(ValueError):retained_boundary_geometry(doc,boundary,edge)
if __name__=='__main__':unittest.main()
