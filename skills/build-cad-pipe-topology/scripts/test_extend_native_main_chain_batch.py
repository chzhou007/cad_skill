import unittest
from extend_native_main_chain_batch import compute

class Tests(unittest.TestCase):
    def test_changed_parent_receipt_is_rejected_before_native_or_rule_execution(self):
        with self.assertRaises((ValueError,FileNotFoundError)):
            compute(dict(parent_receipt=dict(path='missing-parent',sha256='not-current')))

if __name__=='__main__':unittest.main()
