import copy,unittest
import ezdxf
from match_source_checked_crossview_paths import mutual_main_paths,native_main_corridor


def fixture(reverse=False):
    doc=ezdxf.new();layer='空调冷冻水供水';doc.modelspace().add_line((-10,0),(40,0),dxfattribs={'layer':layer})
    nodes=[dict(node_id=f'T{i}',node_type='tee',floor=1,x=(30-i*10 if reverse else i*10),y=0) for i in range(4)]
    order=list(reversed(range(4))) if reverse else list(range(4));edges=[]
    for i,(a,b) in enumerate(zip(order,order[1:])):
        edges.append(dict(edge_id=f'M{i}',start_node_id=f'T{a}',end_node_id=f'T{b}',system='supply',attribute_paths=[[[nodes[a]['x'],0],[nodes[b]['x'],0]]]))
    return doc,dict(nodes=nodes,edges=edges),{f'D{i}':f'T{i}' for i in range(4)}


class SourceCheckedPathTests(unittest.TestCase):
    def test_different_geometric_order_can_preserve_the_same_equipment_topology(self):
        _,plan,taps=fixture();_,iso,_=fixture(True)
        result=mutual_main_paths(dict(plan=plan,iso=iso),dict(plan=taps,iso=taps),'supply',1)
        self.assertEqual(len(result['adjacent']),3);self.assertEqual(len(result['pairwise_order_checks']),6)

    def test_same_names_with_wrong_branch_order_do_not_match(self):
        _,plan,taps=fixture();bad=copy.deepcopy(taps);bad['D1'],bad['D2']=bad['D2'],bad['D1']
        with self.assertRaisesRegex(ValueError,'different native main branch order'):mutual_main_paths(dict(plan=plan,iso=plan),dict(plan=taps,iso=bad),'supply',1)

    def test_parallel_routes_and_wrong_floor_or_system_fail_without_source_scope(self):
        for variant in ('cycle','parallel','floor','system'):
            _,g,taps=fixture()
            if variant=='cycle':g['edges'].append(dict(edge_id='LOOP',start_node_id='T0',end_node_id='T3',system='supply',attribute_paths=[[[0,0],[0,10],[30,10],[30,0]]]))
            elif variant=='parallel':g['edges'].append(dict(g['edges'][0],edge_id='PARALLEL'))
            elif variant=='floor':g['nodes'][1]['floor']=2
            else:g['edges'][1]['system']='return'
            with self.assertRaises(ValueError):mutual_main_paths(dict(plan=g,iso=g),dict(plan=taps,iso=taps),'supply',1)

    def test_native_corridor_supports_a_local_mapping_inside_a_larger_ring(self):
        doc,g,taps=fixture();g['edges'].append(dict(edge_id='LOOP',start_node_id='T0',end_node_id='T3',system='supply',attribute_paths=[[[0,0],[0,10],[30,10],[30,0]]]))
        scoped,evidence=native_main_corridor(doc,g,taps,'supply',1)
        self.assertNotIn('LOOP',[e['edge_id'] for e in scoped['edges']]);self.assertIn('not asserted unique',evidence['scope'])
        self.assertEqual(len(mutual_main_paths(dict(plan=scoped,iso=scoped),dict(plan=taps,iso=taps),'supply',1)['adjacent']),3)
        doc.modelspace().add_line((-10,0),(40,0),dxfattribs={'layer':'空调冷冻水供水'})
        with self.assertRaisesRegex(ValueError,'unique native LINE'):native_main_corridor(doc,g,taps,'supply',1)

    def test_two_anchors_or_collapsed_Ts_cannot_claim_mutual_corroboration(self):
        _,g,taps=fixture()
        for selected in [dict(list(taps.items())[:2]),dict(taps,D1='T0')]:
            with self.assertRaises(ValueError):mutual_main_paths(dict(plan=g,iso=g),dict(plan=selected,iso=selected),'supply',1)


if __name__=='__main__':unittest.main()
