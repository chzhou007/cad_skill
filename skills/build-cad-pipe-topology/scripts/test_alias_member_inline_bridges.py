import copy,math,unittest
from test_native_inline_joint_path_coverage import fixture
from alias_member_inline_bridges import reading_projection,bounded_paths,PARENT_MODE
from native_inline_joint_path_coverage import collect

class Tests(unittest.TestCase):
    def case(self,rotation=0,mirror=False):
        doc,g,inventory,policy,hashes=fixture(rotation,mirror)
        edge=g['edges'][0];edge.pop('source_flexible_joints',None)
        paths=edge['attribute_paths'];endpoints=[p for path in paths for p in path]
        farthest=max(((a,b)for a in endpoints for b in endpoints),key=lambda p:math.dist(*p))
        a,b=farthest;start=[a[i]+.1*(b[i]-a[i])for i in(0,1)];end=[a[i]+.9*(b[i]-a[i])for i in(0,1)]
        parent=dict(mode=PARENT_MODE,original_local_graphs_mutated=False,member_local_graph=dict(
            nodes=[dict(node_id='MEMBER:A',x=start[0],y=start[1]),dict(node_id='MEMBER:B',x=end[0],y=end[1])],
            external_ports=[dict(member_node_id='MEMBER:A',axis_edge_id='AXIS',system='supply'),dict(member_node_id='MEMBER:B',axis_edge_id='AXIS',system='supply')]))
        return doc,g,inventory,policy,hashes,parent
    def test_inherited_native_joint_reader_reconstructs_missing_metadata_for_rotated_mirrored_private_domains(self):
        for rotation,mirror in[(0,False),(90,False),(180,True),(270,True)]:
            with self.subTest(rotation=rotation,mirror=mirror):
                doc,g,inventory,policy,hashes,parent=self.case(rotation,mirror);before=copy.deepcopy(g)
                private,evidence,pending=reading_projection(doc,g,parent,inventory,policy)
                self.assertEqual(pending,[]);self.assertEqual(len(evidence),1);self.assertEqual(g,before)
                self.assertNotIn('source_flexible_joints',g['edges'][0]);self.assertEqual(len(private['edges'][0]['source_flexible_joints']),1)
                native=collect(doc,private,inventory,policy,hashes)['records'][0]
                self.assertEqual(native['source_drawn_pipe_length_units'],30)
                self.assertIsNone(native['physical_length_mm']);self.assertTrue(native['joint_spans_excluded_from_pipe_length'])
    def test_wrong_service_duplicate_line_and_competing_carrier_are_not_joined(self):
        for failure in('service','duplicate_line','carrier'):
            doc,g,inv,p,h,parent=self.case()
            if failure=='service':parent['member_local_graph']['external_ports'][1]['system']='return'
            elif failure=='duplicate_line':
                line=next(iter(doc.modelspace().query('LINE')));doc.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs=dict(layer=line.dxf.layer))
            else:g['edges'].append(dict(copy.deepcopy(g['edges'][0]),edge_id='OTHER'))
            before=copy.deepcopy(g);private,proof,pending=reading_projection(doc,g,parent,inv,p)
            self.assertEqual(proof,[]);self.assertEqual(len(pending),1);self.assertEqual(g,before);self.assertEqual(private,g)
    def test_joint_outside_member_bounds_is_not_deleted_to_force_a_chain(self):
        doc,g,inv,p,h,parent=self.case();ns=parent['member_local_graph']['nodes'];a=[ns[0]['x'],ns[0]['y']];b=[ns[1]['x'],ns[1]['y']]
        ns[1].update(x=a[0]+.2*(b[0]-a[0]),y=a[1]+.2*(b[1]-a[1]))
        private,proof,pending=reading_projection(doc,g,parent,inv,p)
        self.assertEqual(proof,[]);self.assertIn('outside',pending[0]['reason']);self.assertEqual(private,g)
    def test_private_clipping_retains_real_gaps_and_ignores_drawing_tails(self):
        paths=[[[0,0],[4,0]],[[6,0],[10,0]],[[0,0],[0,20]]]
        self.assertEqual(bounded_paths(paths,[2,0],[8,0]),[[[2.,0.],[4.,0.]],[[6.,0.],[8.,0.]]])
        self.assertEqual(bounded_paths(paths,[8,0],[2,0]),[[[4.,0.],[2.,0.]],[[8.,0.],[6.,0.]]])
        with self.assertRaises(ValueError):bounded_paths(paths,[2,0],[2,0])
        with self.assertRaises(ValueError):bounded_paths(paths,[2,0],[8,0],1)
    def test_member_namespace_collision_leaves_failed_projection_unchanged(self):
        doc,g,inv,p,h,parent=self.case();g['nodes'].append(copy.deepcopy(parent['member_local_graph']['nodes'][0]))
        private,proof,pending=reading_projection(doc,g,parent,inv,p)
        self.assertEqual(private,g);self.assertEqual(proof,[]);self.assertIn('namespace',pending[0]['reason'])
if __name__=='__main__':unittest.main()
