import copy,tempfile,unittest
from pathlib import Path
import ezdxf
from test_native_inherited_duplicate_circle_evidence import fixture as circle_fixture
from inherited_circle_branch_inventory import extend,path_evidence
from crossview_equipment_branch_inventory import service_route
from native_line_path_evidence import LAYERS


def fixture(folder):
    doc,graph,source,gh,external=circle_fixture(folder);root=dict(status='native_calibrated_logical_ownership_source_checked',records=[])
    for node in graph['nodes']:
        if node['node_id'].startswith('D'):node['node_type']='equipment'
    for edge in graph['edges']:
        if not edge['edge_id'].startswith('B'):continue
        eq=edge['start_node_id'];owner=dict(source_sha256=source,equipment_id=eq,system='supply',human_accepted=False,physical_port_verified=False,
            endpoint_snapshot=dict(start_node_id=eq,end_node_id=edge['end_node_id'],system='supply',attribute_paths=copy.deepcopy(edge['attribute_paths'])))
        edge.update(source_layout_equipment_interface=owner,equipment_connector_length_mm=None);root['records'].append(copy.deepcopy(owner))
    graph['sourceLayoutEquipmentOwnership']=root;rows=[]
    for eq in ('DC','DA'):
        services=dict(supply=dict(trace=service_route(graph,eq,'supply'),ready_for_mapping_comparison=False,status='source_check_pending',reason='historical schema'),
            **{'return':dict(trace=dict(status='missing_service',edges=[]),ready_for_mapping_comparison=False)})
        rows.append(dict(equipment_id=eq,floor=3,ready_for_mapping_comparison=False,views=dict(plan=dict(services=services),iso=dict(services={s:dict(ready_for_mapping_comparison=True) for s in ('supply','return')}))))
    parent=dict(records=rows,counts=dict(equipment=2,ready_for_mapping_comparison=0),status='source_comparison_inventory_not_mapping',local_graphs_mutated=False,mapped_paths=0,human_accepted=False,hil_ready=False)
    policy=dict(selections=[dict(equipment_id='DA',system='supply',node_id='A',edge_id='BA')])
    return doc,graph,parent,policy,source,gh


class Tests(unittest.TestCase):
    def test_new_branch_witness_preserves_other_services_and_does_not_promote_incomplete_equipment(self):
        with tempfile.TemporaryDirectory() as temp:
            args=fixture(Path(temp));before=copy.deepcopy(args[1:3]);result,proof=extend(*args)
            self.assertEqual(args[1:3],before);self.assertEqual(result['records'][0],args[2]['records'][0]);self.assertEqual(len(proof),1)
            row=result['records'][1];self.assertTrue(row['views']['plan']['services']['supply']['ready_for_mapping_comparison'])
            self.assertFalse(row['views']['plan']['services']['return']['ready_for_mapping_comparison']);self.assertFalse(row['ready_for_mapping_comparison'])
            self.assertEqual(result['counts']['ready_for_mapping_comparison'],0);self.assertFalse(proof[0]['source_evidence']['physical_ports_verified'])

    def test_ready_scope_changed_T_edge_owner_and_unproven_path_fail(self):
        for case in ('duplicate','ready','tee','edge','owner','snapshot','root','path'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                args=list(fixture(Path(temp)));doc,graph,parent,policy,source,gh=args;edge=next(e for e in graph['edges'] if e['edge_id']=='BA')
                if case=='duplicate':policy['selections']*=2
                elif case=='ready':parent['records'][1]['views']['plan']['services']['supply']['ready_for_mapping_comparison']=True
                elif case=='tee':policy['selections'][0]['node_id']='C'
                elif case=='edge':policy['selections'][0]['edge_id']='BC'
                elif case=='owner':edge['source_layout_equipment_interface']['equipment_id']='DC'
                elif case=='snapshot':edge['source_layout_equipment_interface']['endpoint_snapshot']['system']='return'
                elif case=='root':graph['sourceLayoutEquipmentOwnership']['records']=[]
                else:edge['attribute_paths'][0].insert(1,[-5,21])
                with self.assertRaises(ValueError):extend(*args)

    def crossover(self):
        doc=ezdxf.new();m=doc.modelspace();a=m.add_line((-10,0),(-1,0),dxfattribs=dict(layer=LAYERS['return']));b=m.add_line((1,0),(10,0),dxfattribs=dict(layer=LAYERS['return']))
        cross=m.add_line((0,-10),(0,10),dxfattribs=dict(layer=LAYERS['supply']))
        gap=dict(source_handles=[a.dxf.handle,b.dxf.handle],a=[-1,0],b=[1,0],crossings=[dict(crossing=[0,0],crossed_handle=cross.dxf.handle,crossed_source_system='supply')],
            crossing_connectivity='independent_pipes_no_junction',physical_length='unknown',relative_elevation='unknown')
        edge=dict(edge_id='E',system='return',source_handles=[a.dxf.handle,b.dxf.handle],attribute_paths=[[[-10,0],[-1,0]],[[1,0],[10,0]]],path_length=18,path_length_complete=False,
            source_circle_connection=dict(expert_issue='PINNED-CASE'),source_normalized_crossovers=[gap])
        graph=dict(metadata=dict(source_sha256='S'),nodes=[dict(node_id='N',x=-10,y=0)],edges=[edge])
        return doc,graph,edge

    def test_legacy_gap_projection_reuses_native_crossover_checks_and_keeps_original_identity(self):
        doc,graph,edge=self.crossover();before=copy.deepcopy(graph);proof=path_evidence(doc,graph,edge,'S','G')
        self.assertEqual(graph,before);self.assertEqual(len(proof['evidence']['paths']),2);self.assertEqual(len(proof['evidence']['crossovers']),1)
        self.assertNotEqual(proof['projection_graph_sha256'],'G');self.assertEqual(proof['input_graph_sha256'],'G')
        self.assertTrue(proof['legacy_metadata_projection'][0]['current_projection_gap_id'].startswith('CURRENT-LEGACY-CROSSOVER:'))
        self.assertNotIn('source_gap_id',edge['source_normalized_crossovers'][0]);self.assertIsNone(proof['evidence']['physical_length_mm'])

    def test_legacy_gap_wrong_system_missing_exclusion_and_extra_piece_fail(self):
        for case in ('system','no_contract','no_gap','extra_path','physical','unknown_schema'):
            with self.subTest(case=case):
                doc,graph,edge=self.crossover()
                if case=='system':edge['source_normalized_crossovers'][0]['crossings'][0]['crossed_source_system']='return'
                elif case=='no_contract':edge.pop('source_circle_connection')
                elif case=='no_gap':edge['source_normalized_crossovers']=[]
                elif case=='extra_path':edge['attribute_paths'].append([[11,0],[12,0]])
                elif case=='physical':edge['source_normalized_crossovers'][0]['physical_length']=0
                else:edge['source_normalized_crossovers'][0]['unsupported']='x'
                with self.assertRaises(ValueError):path_evidence(doc,graph,edge,'S','G')


if __name__=='__main__':unittest.main()
