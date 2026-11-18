import copy
import unittest

from producer_process_identity import bind_tree, bind_access_records, identity, verify_launches, same_epoch_live


def row(pid,start,end,parent):
    return dict(pid=pid,started_ns=start,finished_ns=end,parent_pid=parent)


class ProducerEpochTests(unittest.TestCase):
    def fixture(self):
        rows=[row(1,100,1000,900),row(7,200,250,1),row(7,400,450,1)]
        tree=bind_tree(rows,1)
        access={identity(r):dict(r,multiprocessing_spawn_requests=[],multiprocessing_spawn_token=None,qualified_node_calls=[])for r in rows}
        observed={k:dict(qualified_subprocesses=[])for k in access}
        observed[(1,100)]['qualified_subprocesses']=[dict(outcome='created',pid=7,parent_pid=1,executable_role='qualified_python',command_sha256=str(n))for n in (1,2)]
        return rows,tree,access,observed

    def test_valid_reused_child_PID_retains_both_original_epochs(self):
        rows,tree,access,observed=self.fixture()
        self.assertEqual(len(tree['records']),3)
        self.assertEqual(tree['reused_PIDs'],{7:2})
        result=verify_launches(tree,access,observed)
        self.assertEqual(result['ordinary_qualified_Python_children'],2)
        self.assertEqual(result['processes'],3)

    def test_parent_PID_reuse_binds_children_to_original_lifetimes(self):
        rows=[row(1,100,1000,900),row(7,200,300,1),row(7,400,500,1),row(9,250,270,7),row(10,450,470,7)]
        tree=bind_tree(rows,1)
        self.assertEqual(tree['parents'][(9,250)],(7,200))
        self.assertEqual(tree['parents'][(10,450)],(7,400))

    def test_exact_duplicate_epoch_is_not_PID_reuse(self):
        rows,_,_,_=self.fixture();rows.append(copy.deepcopy(rows[1]))
        with self.assertRaisesRegex(ValueError,'Repeated process epoch'):bind_tree(rows,1)

    def test_overlapping_parent_lifetimes_are_not_guessed(self):
        rows=[row(1,100,1000,900),row(7,200,500,1),row(7,400,600,1),row(9,450,470,7)]
        with self.assertRaisesRegex(ValueError,'ambiguous parent lifetime'):bind_tree(rows,1)

    def test_unrelated_or_delayed_child_without_lifetime_evidence_remains_held(self):
        rows=[row(1,100,300,900),row(7,400,500,1)]
        with self.assertRaisesRegex(ValueError,'Unrelated process'):bind_tree(rows,1)

    def test_unknown_epoch_is_retained_only_for_unique_legacy_PID(self):
        rows=[dict(pid=1,parent_pid=900),dict(pid=7,parent_pid=1)]
        tree=bind_tree(rows,1)
        self.assertEqual(tree['root'],(1,None))
        self.assertEqual(tree['identity_mode'],'legacy_unique_PID_unknown_epoch_retained')
        rows.append(dict(pid=7,parent_pid=1))
        with self.assertRaises(ValueError):bind_tree(rows,1)

    def test_access_receipts_for_reused_PID_need_explicit_epoch(self):
        rows,tree,_,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'requires an epoch'):
            bind_access_records([dict(pid=r['pid'],parent_pid=r['parent_pid'])for r in rows],tree)
        self.assertEqual(set(bind_access_records(rows,tree)),set(tree['records']))

    def test_resolver_binds_original_access_observation_epochs(self):
        rows,tree,_,_=self.fixture()
        access=[dict(pid=r['pid'],parent_pid=r['parent_pid'],original=i)for i,r in enumerate(rows)]
        self.assertEqual(set(bind_access_records(access,tree,lambda r:rows[r['original']])),set(tree['records']))

    def test_a_missing_reused_launch_is_not_hidden_by_matching_PID_set(self):
        _,tree,access,observed=self.fixture()
        observed[(1,100)]['qualified_subprocesses'].pop()
        with self.assertRaisesRegex(ValueError,'launch count'):verify_launches(tree,access,observed)

    def test_multiprocessing_tokens_bind_original_parent_epoch(self):
        rows,tree,access,observed=self.fixture()
        observed[(1,100)]['qualified_subprocesses']=[]
        access[(1,100)]['multiprocessing_spawn_requests']=[dict(spawn_token='first'),dict(spawn_token='second')]
        access[(7,200)]['multiprocessing_spawn_token']='first'
        access[(7,400)]['multiprocessing_spawn_token']='second'
        self.assertEqual(verify_launches(tree,access,observed)['multiprocessing_children'],2)

    def test_original_qualified_Node_calls_must_have_matching_launches(self):
        _,tree,access,observed=self.fixture()
        observed[(1,100)]['qualified_subprocesses'].append(dict(outcome='created',pid=8,parent_pid=1,executable_role='qualified_node'))
        with self.assertRaisesRegex(ValueError,'Node launches'):verify_launches(tree,access,observed)
        access[(1,100)]['qualified_node_calls']=[dict(pid=8)]
        self.assertTrue(verify_launches(tree,access,observed)['every_Python_child_launch_and_receipt_accounted'])

    def test_new_live_owner_of_reused_PID_does_not_make_old_epoch_live(self):
        self.assertFalse(same_epoch_live(7,200,lambda pid:dict(created_ns=400,terminated=False)))
        self.assertTrue(same_epoch_live(7,450,lambda pid:dict(created_ns=400,terminated=False)))

    def test_real_exit_or_missing_handle_are_terminal_for_the_observed_epoch(self):
        self.assertFalse(same_epoch_live(7,200,lambda pid:None))
        self.assertFalse(same_epoch_live(7,200,lambda pid:dict(created_ns=100,terminated=True,exit_code=259)))

    def test_failed_handle_query_is_not_silently_terminal(self):
        def denied(pid):raise PermissionError('access denied')
        with self.assertRaises(PermissionError):same_epoch_live(7,200,denied)


if __name__=='__main__':unittest.main()
