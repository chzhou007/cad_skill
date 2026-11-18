import copy, unittest
from test_native_repeated_branch_DN_layout import fixture as original_fixture
from reapply_ambiguous_layout_DN import discover, compose
from axis_unbranched_vertical_DN import native_items
from native_line_path_evidence import LAYERS


def fixture():
    doc, graph, handles, roots = original_fixture(); rows = []
    # Make a genuinely ambiguous original graph projection beside each target.
    foreign = [e for e in doc.modelspace().query('LINE')]
    for i, line in enumerate(foreign):
        x = 808.2 if i == 0 else 828.2
        line.dxf.start = (x,0,0); line.dxf.end = (x,100,0)
        eid = 'foreign'+str(i); a,b = eid+'A',eid+'B'
        graph['nodes'] += [dict(node_id=a,node_type='interface',x=x,y=0,floor=2),
                           dict(node_id=b,node_type='interface',x=x,y=100,floor=2)]
        system = next(k for k,v in LAYERS.items() if v==line.dxf.layer)
        graph['edges'].append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system=system,
            source_insert_handle=None,attribute_paths=[[[x,0],[x,100]]],native_test_handle=line.dxf.handle))
    for edge in graph['edges']:
        edge.update(floor_start=2,floor_end=2)
        rows.append(dict(edge_id=edge['edge_id'],path_index=0,segment_index=0,
            scope_points=copy.deepcopy(edge['attribute_paths'][0]),system=edge['system'],floor_start=2,floor_end=2,
            direction_class='vertical',native_source_status='single_source_line_covers',native_witnesses=[dict(
                scope='decomposed_selected_insert' if edge.get('source_insert_handle') else 'modelspace',
                source_handle=edge.get('source_insert_handle') or edge['native_test_handle'],layer=LAYERS[edge['system']])]))
    route = dict(records=rows,inputs=dict(source=dict(sha256='S'),graph=dict(sha256='G')))
    parent = dict(counts=dict(current_known=len(rows)-2),pending=[dict(edge_id=s+'4',path_index=0,segment_index=0,
        original_reason='ambiguous_native_text_projection_requires_ownership_rule') for s in ('supply','return')])
    return doc, graph, route, parent, handles, roots


class Tests(unittest.TestCase):
    def test_ambiguous_entry_reaches_original_independent_layout_owner(self):
        doc,g,route,parent,handles,roots = fixture(); before=copy.deepcopy((g,route,parent))
        selected=discover(doc,g,route,parent,'S')
        self.assertEqual({r['text_handle'] for r in selected['records']},set(handles))
        result=compose(doc,g,route,parent,native_items(doc,g),'S','G')
        self.assertEqual(result['counts']['new_direct'],2)
        self.assertEqual({r['nominal_mm'] for r in result['records']},{80})
        self.assertEqual((g,route,parent),before)
        for r in result['original_layout_qualification']['records']:
            self.assertEqual(len(r['independent_control_roots']),4)
            self.assertNotIn(roots[-1],r['independent_control_roots'])
            self.assertFalse(set(handles)&set(r['independent_control_text_handles']))

    def test_same_source_new_DN_keeps_transition_unknown(self):
        doc,g,route,parent,_,_ = fixture()
        doc.modelspace().add_text('DN50',dxfattribs=dict(layer='AN',height=1,rotation=90,insert=(809,50)))
        result=compose(doc,g,route,parent,native_items(doc,g),'S','G')
        self.assertFalse(any(r['edge_id']=='supply4' for r in result['records']))
        self.assertTrue(result['direct_held'])

    def test_original_controls_and_known_domain_boundaries_remain_required(self):
        doc,g,route,parent,_,roots=fixture();doc.modelspace().delete_entity(doc.entitydb[roots[0]])
        with self.assertRaises(ValueError):compose(doc,g,route,parent,native_items(doc,g),'S','G')
        doc,g,route,parent,_,_=fixture();parent['pending'][0]['original_reason']='no_qualified_axis_annotation_on_this_vertical_segment'
        selected=discover(doc,g,route,parent,'S')
        self.assertEqual(len(selected['complete_ambiguous_pending_domains']),1)


if __name__=='__main__':unittest.main()
