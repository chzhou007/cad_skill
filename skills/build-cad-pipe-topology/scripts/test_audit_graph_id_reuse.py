import hashlib,json,tempfile,unittest
from pathlib import Path
from audit_graph_id_reuse import audit,audit_bound


class AuditGraphIdReuse(unittest.TestCase):
    def test_reused_identifier_and_reverse_geometry(self):
        edge = {'edge_id': 'E1', 'system': 'supply', 'source_handles': ['A'], 'attribute_paths': [[[0, 0], [1, 0]]]}
        other = {'edge_id': 'E1', 'system': 'supply', 'source_handles': ['B'], 'attribute_paths': [[[0, 1], [1, 1]]]}
        moved = {**edge, 'edge_id': 'E2', 'attribute_paths': [[[1, 0], [0, 0]]]}
        report = audit({'nodes': [], 'edges': [edge]}, {'nodes': [], 'edges': [other, moved]})
        row = report['edges']['records'][0]
        self.assertEqual(row['candidate_new_ids'], ['E2'])
        self.assertTrue(row['unique_source_geometry_match'])
        self.assertTrue(row['id_reused_for_different_or_unverifiable_object'])
        self.assertFalse(report['review_migration_authorized'])

    def test_identical_parallel_candidates_are_not_unique(self):
        e = {'edge_id': 'E1', 'system': 'return', 'source_handles': ['A'], 'attribute_paths': [[[0, 0], [1, 0]]]}
        report = audit({'nodes': [], 'edges': [e]}, {'nodes': [], 'edges': [e, {**e, 'edge_id': 'E2'}]})
        self.assertFalse(report['edges']['records'][0]['unique_source_geometry_match'])

    def test_bound_audit_rejects_stale_graph_or_different_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=Path(tmp)/'old.json';new=Path(tmp)/'new.json'
            old.write_text(json.dumps({'nodes': [], 'edges': [], 'metadata': {'source_sha256': 'source'}}),encoding='utf8');new.write_bytes(old.read_bytes())
            spec={'previous_graph_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'source_sha256':'source'}
            self.assertFalse(audit_bound(old,new,'source',spec)['review_migration_authorized'])
            with self.assertRaisesRegex(ValueError,'source hash'):audit_bound(old,new,'other',spec)
            new.write_text(json.dumps({'nodes': [], 'edges': [], 'metadata': {'source_sha256': 'other'}}),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'graph source binding'):audit_bound(old,new,'source',spec)
            old.write_text('{}',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'previous graph'):audit_bound(old,new,'source',spec)

if __name__ == '__main__': unittest.main()
