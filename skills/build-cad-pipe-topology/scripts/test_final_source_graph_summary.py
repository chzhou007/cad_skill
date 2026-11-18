import csv,copy,json,tempfile,unittest
from pathlib import Path
from final_source_graph_summary import refresh


class Tests(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);path=root/'graph_with_edges.json'
        graph=dict(nodes=[dict(node_id='T',node_type='tee'),dict(node_id='EQ',node_type='equipment'),
                          dict(node_id='UT',node_type='virtual_equipment',subtype='unresolved_source_terminal')],
            edges=[dict(edge_id='E1',start_node_id='T',end_node_id='EQ'),dict(edge_id='E2',start_node_id='T',end_node_id='UT')],
            metadata=dict(source_sha256='source',hil_ready=False))
        path.write_text(json.dumps(graph),'utf8')
        (root/'assigned_edge_device_instances.csv').write_text('device_name,edge_id\nvalve,E2\n','utf8')
        summary=dict(nodes=99,edges=88,tee_nodes=77,equipment_nodes=66,virtual_equipment_nodes=55,
            unresolved_degree1_network_vertices=44,source_sha256='source',accepted_edge_length_coverage=.8,physical_length_mm=None)
        return path,graph,summary

    def test_final_counts_replace_stale_counts_without_changing_source_or_unknown_lengths(self):
        path,graph,summary=self.fixture();original=copy.deepcopy(summary);before=path.read_bytes()
        result=refresh(summary,path)
        self.assertEqual(summary,original);self.assertEqual(path.read_bytes(),before)
        self.assertEqual([result[k] for k in ('nodes','edges','tee_nodes','equipment_nodes','virtual_equipment_nodes','unresolved_degree1_network_vertices')],[3,2,1,1,1,1])
        self.assertEqual(result['base_extraction_summary']['nodes'],99);self.assertEqual(result['base_extraction_summary']['accepted_edge_length_coverage'],.8)
        self.assertEqual(result['final_canonical_components'],1);self.assertIsNone(result['physical_length_mm']);self.assertFalse(result['final_hil_ready'])
        self.assertEqual(refresh(result,path),result)

    def test_actual_degree_and_explicit_unknown_roles_are_preserved(self):
        path,graph,summary=self.fixture();graph['edges'].append(dict(edge_id='E3',start_node_id='EQ',end_node_id='UT'))
        path.write_text(json.dumps(graph),'utf8');result=refresh(summary,path)
        self.assertEqual(result['final_graph_counts']['unresolved_source_terminal_nodes'],1)
        self.assertEqual(result['unresolved_degree1_network_vertices'],0)

    def test_wrong_source_or_orphan_components_cannot_yield_final_counts(self):
        path,graph,summary=self.fixture();summary['source_sha256']='other'
        with self.assertRaisesRegex(ValueError,'source differs'):refresh(summary,path)
        summary['source_sha256']='source';(path.parent/'assigned_edge_device_instances.csv').write_text('device_name,edge_id\nvalve,absent\n','utf8')
        with self.assertRaisesRegex(ValueError,'orphaned'):refresh(summary,path)

    def test_typed_non_node_boundaries_remain_valid_and_are_counted_separately(self):
        path,graph,summary=self.fixture()
        graph['boundary_anchors']=[dict(boundary_id='A',kind='expert_non_node_source_boundary',system='supply',source_pipe_handle='H')]
        graph['edges'].append(dict(edge_id='E3',start_node_id='T',end_node_id=None,end_boundary_id='A',system='supply',source_handles=['H']))
        path.write_text(json.dumps(graph),'utf8');result=refresh(summary,path)
        self.assertEqual(result['nodes'],3);self.assertEqual(result['edges'],3)
        self.assertEqual(result['final_graph_counts']['boundary_anchors'],1)
        self.assertEqual(result['final_graph_counts']['unresolved_source_terminal_nodes'],1)
        graph['edges'][-1]['end_boundary_id']='absent';path.write_text(json.dumps(graph),'utf8')
        with self.assertRaisesRegex(ValueError,'missing boundary'):refresh(summary,path)

    def test_missing_component_table_or_dangling_graph_does_not_fall_back_to_old_summary(self):
        path,graph,summary=self.fixture();graph['edges'][0]['end_node_id']='absent';path.write_text(json.dumps(graph),'utf8')
        with self.assertRaisesRegex(ValueError,'dangling'):refresh(summary,path)
        graph['edges'][0]['end_node_id']='EQ';path.write_text(json.dumps(graph),'utf8');(path.parent/'assigned_edge_device_instances.csv').unlink()
        with self.assertRaises(FileNotFoundError):refresh(summary,path)


if __name__=='__main__':unittest.main()
