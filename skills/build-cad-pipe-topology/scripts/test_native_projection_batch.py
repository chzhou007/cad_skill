import copy,unittest
from native_projection_batch import selections,work
from reconstruct_native_block_branches import projected_coverage
from test_reconstruct_native_block_branches import fixture

class Tests(unittest.TestCase):
    def test_restored_family_and_explicit_scopes_do_not_silently_expand(self):
        _,g,_,_,_=fixture();g['edges'][0]['source_native_block_branch']={'native':True}
        self.assertEqual(selections(g,dict(family='restored_native_block_branches')),['E']);self.assertEqual(selections(g,dict(family='explicit_edge_scope',edge_ids=['L'])),['L'])
        for ids in ([],['E','E'],['MISSING']):
            with self.assertRaises(ValueError):selections(g,dict(family='explicit_edge_scope',edge_ids=ids))
    def test_original_and_fast_native_proofs_equal_for_mirror_and_omission(self):
        import native_projection_batch as module
        for omission in (False,True):
            for mirror in (False,True):
                doc,g,_,_,_=fixture(omission,mirror);before=copy.deepcopy(g)
                expected=projected_coverage(doc,g,'E','S');module._doc=doc;module._graph=g;module._source_hash='S'
                actual=work('E');self.assertEqual(actual,dict(edge_id='E',projections=expected));self.assertEqual(g,before)
if __name__=='__main__':unittest.main()
