import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from source_comparison_gate import check,check_confirmed_gap_joint_graph

class ConfirmedGapJointGateTests(unittest.TestCase):
    def test_graph_flag_is_not_proof_of_confirmed_joint(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);gp=root/'graph_with_edges.json';gp.write_text(json.dumps({'sourceConfirmedGapJoints':{'claimed':True}}))
            result=check({},'G',root,gp)
            self.assertEqual(result['status'],'failed');self.assertFalse(result['hil_ready'])
            self.assertIn('stage invalid',result['errors'][0])
    def fixture(self,base):
        parent=base/'parent';parent.mkdir();child=base/'child';child.mkdir()
        gp=child/'graph_with_edges.json';gp.write_text('{}');(child/'edge_device_instances.csv').write_text('inventory')
        pg=parent/'graph.json';pg.write_text('{}')
        report=dict(graph_sha256='PARENT');rp=parent/'source-comparison-report.json';rp.write_text(json.dumps(report))
        receipt=parent/'rebuild-receipt.json';receipt.write_text(json.dumps(dict(final_graph_sha256='PARENT')))
        sh=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        policy=dict(parent_task_root=str(parent),parent_report_sha256=sh(rp),parent_receipt_sha256=sh(receipt))
        pp=child/'policy.json';pp.write_text(json.dumps(policy))
        audit=dict(output_graph_sha256='CHILD',inputs=dict(policy=dict(path=str(pp)),graph=dict(path=str(pg),sha256='PARENT')),records=[dict(insert_handle='J1')])
        result=dict(status='pending',errors=[],pending=['1 source joint candidates require comparison','equipment ports unresolved','DN attribution pending'],missing_gap_joint_blockers=[dict(source_handle='J1')])
        return child,gp,report,audit,result,pp
    def test_reuse_geometry_but_keep_other_unknowns_and_fresh_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            root,gp,report,audit,parent,pp=self.fixture(Path(folder))
            with patch('attach_confirmed_gap_joints.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=parent):
                out=check_confirmed_gap_joint_graph(root,report,'CHILD',gp)
            self.assertEqual(out['missing_gap_joint_blockers'],[])
            self.assertEqual(out['pending'],['equipment ports unresolved','DN attribution pending'])
            self.assertFalse(out['hil_ready']);self.assertEqual(out['graph_sha256'],'CHILD')
            self.assertEqual(out['confirmed_gap_joint_stage']['physical_lengths'],'unknown')
            self.assertEqual(len(parent['missing_gap_joint_blockers']),1)
    def test_wrong_report_scope_or_hash_rejects_before_parent_checks(self):
        for kind in ('report','scope','hash'):
            with tempfile.TemporaryDirectory() as folder:
                root,gp,report,audit,parent,pp=self.fixture(Path(folder))
                policy=json.loads(pp.read_text())
                if kind=='report':report={}
                elif kind=='scope':policy['parent_task_root']=str(root)
                else:policy['parent_report_sha256']='STALE'
                pp.write_text(json.dumps(policy))
                with patch('attach_confirmed_gap_joints.verify_output',return_value=audit),self.assertRaises(ValueError):
                    check_confirmed_gap_joint_graph(root,report,'CHILD',gp)
    def test_unmatched_parent_candidate_cannot_be_silently_dropped(self):
        with tempfile.TemporaryDirectory() as folder:
            root,gp,report,audit,parent,pp=self.fixture(Path(folder));parent['missing_gap_joint_blockers'][0]['source_handle']='OTHER'
            with patch('attach_confirmed_gap_joints.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=parent),self.assertRaisesRegex(ValueError,'candidate scope'):
                check_confirmed_gap_joint_graph(root,report,'CHILD',gp)

if __name__=='__main__':unittest.main()
