import copy
import math
import unittest

import ezdxf
from ezdxf.math import Matrix44
from normalize_two_arm_circle_continuity import collect, normalize, reassign_components

SUPPLY='空调冷冻水供水'
RETURN='空调冷冻水回水'


def fixture(chain=False):
    doc=ezdxf.new('R2013')
    doc.layers.new(SUPPLY,dxfattribs=dict(color=6));doc.layers.new(RETURN,dxfattribs=dict(color=4))
    space=doc.modelspace();circles=[space.add_circle((0,0),100,dxfattribs=dict(layer=RETURN))]
    if chain:circles.append(space.add_circle((-1000,0),100,dxfattribs=dict(layer=RETURN)))
    spans=[[(0,1000),(0,0)],[(-100,0),(-1000,0)]]
    if chain:spans.append([(-1000,-100),(-1000,-1000)])
    nodes=[dict(node_id='A',node_type='tee',subtype='physical_tee',floor=2,system='return',x=0,y=1000),
           dict(node_id='U0',node_type='virtual_equipment',subtype='unresolved_source_terminal',floor=2,system='return',x=0,y=0),
           dict(node_id='U1',node_type='virtual_equipment',subtype='unresolved_source_terminal',floor=2,system='return',x=-100,y=0)]
    if chain:
        nodes.extend([dict(node_id='U2',node_type='virtual_equipment',subtype='unresolved_source_terminal',floor=2,system='return',x=-1000,y=0),
                      dict(node_id='U3',node_type='virtual_equipment',subtype='unresolved_source_terminal',floor=2,system='return',x=-1000,y=-100)])
    nodes.append(dict(node_id='B',node_type='tee',subtype='physical_tee',floor=2,system='return',x=-1000,y=-1000 if chain else 0))
    pairs=[('A','U0'),('U1','U2' if chain else 'B')]+([('U3','B')] if chain else [])
    edges=[];rows=[]
    for i,(points,ends) in enumerate(zip(spans,pairs)):
        line=space.add_line(*points,dxfattribs=dict(layer=RETURN));name='VALVE'+str(i)
        edges.append(dict(edge_id='E'+str(i),start_node_id=ends[0],end_node_id=ends[1],system='return',
                          path_points=copy.deepcopy(points),path=copy.deepcopy(points),attribute_paths=[copy.deepcopy(points)],
                          source_handles=[line.dxf.handle],equipment_names=[name],equipment_counts=dict(ball_valve=1)))
        rows.append(dict(device_name=name,edge_id='E'+str(i),source_handle='V'+str(i),edge_distance='0'))
    return doc,dict(nodes=nodes,edges=edges,metadata={}),[c.dxf.handle for c in circles],rows


def transform(doc,graph,matrix):
    for entity in doc.modelspace():entity.transform(matrix)
    def xy(p):q=matrix.transform((p[0],p[1],0));return [q.x,q.y]
    for n in graph['nodes']:n['x'],n['y']=xy([n['x'],n['y']])
    for e in graph['edges']:
        for k in ['path','path_points']:e[k]=[xy(p) for p in e[k]]
        e['attribute_paths']=[[xy(p) for p in part] for part in e['attribute_paths']]


class Tests(unittest.TestCase):
    def test_center_rim_corner_is_one_path_not_a_new_T_or_physical_length(self):
        doc,g,handles,rows=fixture();before=copy.deepcopy(g);evidence=collect(doc,g,handles)
        out,aliases=normalize(g,evidence);assigned=reassign_components(rows,aliases,out['edges'])
        self.assertEqual(g,before);self.assertEqual(len(out['nodes']),2);self.assertEqual(len(out['edges']),1)
        edge=out['edges'][0];self.assertAlmostEqual(edge['path_length'],1900);self.assertAlmostEqual(edge['drawing_path_length'],2000)
        self.assertEqual(len(edge['attribute_paths']),2);self.assertIsNone(edge['physical_length_mm']);self.assertFalse(edge['path_length_complete'])
        self.assertEqual(edge['equipment_counts'],dict(ball_valve=2));self.assertEqual(len(assigned),2)
        self.assertEqual({r['edge_id'] for r in assigned},{edge['edge_id']});self.assertEqual(out['sourceTwoArmCircleContinuity']['physical_Ts_added'],0)

    def test_two_markers_share_one_fragment_without_duplicate_edges_or_components(self):
        doc,g,handles,rows=fixture(True);records=collect(doc,g,handles);out,aliases=normalize(g,records)
        self.assertEqual((len(out['nodes']),len(out['edges'])),(2,1));self.assertEqual(len(aliases),3)
        edge=out['edges'][0];self.assertAlmostEqual(edge['path_length'],2800);self.assertAlmostEqual(edge['drawing_path_length'],3000)
        self.assertEqual(len(edge['attribute_paths']),3);self.assertEqual(len(reassign_components(rows,aliases,out['edges'])),3)
        other,_=normalize(g,list(reversed(records)));self.assertEqual(out['edges'],other['edges'])

    def test_rotations_mirrors_and_negative_OCS_keep_source_ownership(self):
        for angle,mirror in [(0,False),(37,False),(90,False),(180,False),(270,False),(37,True)]:
            with self.subTest(angle=angle,mirror=mirror):
                doc,g,handles,_=fixture();matrix=Matrix44.chain(Matrix44.scale(-1 if mirror else 1,1,1),Matrix44.z_rotate(math.radians(angle)),Matrix44.translate(10000,15000,0));transform(doc,g,matrix)
                evidence=collect(doc,g,handles);out,_=normalize(g,evidence)
                self.assertAlmostEqual(out['edges'][0]['path_length'],1900);self.assertEqual(evidence[0]['system'],'return')

    def test_circle_layer_does_not_override_two_independent_pipe_owners(self):
        doc,g,handles,_=fixture();doc.entitydb[handles[0]].dxf.layer=SUPPLY
        proof=collect(doc,g,handles)
        self.assertFalse(proof[0]['circle_layer_matches_lines']);self.assertEqual(proof[0]['system'],'return')

    def test_ordinary_crossing_third_ray_system_colour_and_Z_are_not_bridged(self):
        for kind in ['missing_circle','third_arm','system','colour','Z','tangent']:
            with self.subTest(kind=kind):
                doc,g,handles,_=fixture();lines=list(doc.modelspace().query('LINE'))
                if kind=='missing_circle':doc.modelspace().delete_entity(doc.entitydb[handles[0]])
                elif kind=='third_arm':doc.modelspace().add_line((0,0),(1000,0),dxfattribs=dict(layer=RETURN))
                elif kind=='system':lines[1].dxf.layer=SUPPLY
                elif kind=='colour':lines[1].dxf.color=1
                elif kind=='Z':lines[0].dxf.start=(0,1000,1)
                else:lines[1].dxf.end=(-100,-1000,0)
                with self.assertRaises(ValueError):collect(doc,g,handles)

    def test_extra_polyline_insert_or_duplicate_marker_is_not_ignored(self):
        for kind in ['polyline','insert','duplicate_circle']:
            with self.subTest(kind=kind):
                doc,g,handles,_=fixture();space=doc.modelspace()
                if kind=='polyline':space.add_lwpolyline([(0,0),(1000,0)],dxfattribs=dict(layer=RETURN))
                elif kind=='insert':block=doc.blocks.new('DEVICE');block.add_line((-50,0),(50,0));space.add_blockref('DEVICE',(0,0),dxfattribs=dict(layer=RETURN))
                else:space.add_circle((0,0),100,dxfattribs=dict(layer=RETURN))
                with self.assertRaises(ValueError):collect(doc,g,handles)

    def test_reviewed_boundaries_and_non_unresolved_endpoint_owners_are_protected(self):
        for kind in ['boundary','equipment','degree','floor','wrong_handle']:
            with self.subTest(kind=kind):
                doc,g,handles,_=fixture()
                if kind=='boundary':g['boundary_anchors']=[dict(boundary_id='KNOWN',source_marker_handles=handles)]
                elif kind=='equipment':g['nodes'][1]['subtype']='actual_equipment_port'
                elif kind=='degree':g['edges'].append(dict(g['edges'][0],edge_id='OTHER'))
                elif kind=='floor':g['nodes'][1]['floor']=3
                else:g['edges'][0]['source_handles']=['NOT_NATIVE']
                with self.assertRaises(ValueError):normalize(g,collect(doc,g,handles))

    def test_prior_values_remain_scoped_lineage_and_unaffected_objects_are_identical(self):
        doc,g,handles,_=fixture();g['edges'][0]['legacy_DN']=200;g['edges'][1]['legacy_DN']=450
        g['nodes'].append(dict(node_id='OTHER',node_type='equipment',floor=2,x=99999,y=99999))
        out,_=normalize(g,collect(doc,g,handles));edge=out['edges'][0]
        self.assertNotIn('legacy_DN',edge);self.assertEqual({e['legacy_DN'] for e in edge['source_circle_continuity']['prior_edge_snapshots']},{200,450})
        self.assertEqual(next(n for n in out['nodes'] if n['node_id']=='OTHER'),g['nodes'][-1]);self.assertIn('crossview_mapping',out['derivedEvidenceInvalidation']['recompute'])

    def test_component_duplicates_and_missing_graph_assignment_are_blocked(self):
        doc,g,handles,rows=fixture();out,aliases=normalize(g,collect(doc,g,handles))
        with self.assertRaises(ValueError):reassign_components(rows+[rows[0]],aliases,out['edges'])
        rows[0]['device_name']='NOT_THE_SOURCE_COMPONENT'
        with self.assertRaises(ValueError):reassign_components(rows,aliases,out['edges'])


if __name__=='__main__':unittest.main()
