import unittest
from native_original_plan_DN_replay import compare

class NativeComparison(unittest.TestCase):
    def test_key_order_only_is_equal_without_changing_original(self):
        compare({'known':150,'scope':{'a':1,'b':2}},{'scope':{'b':2,'a':1},'known':150})
    def test_value_type_array_order_missing_field_or_unknown_to_zero_fails(self):
        original={'value':None,'path':['A','B'],'flag':False}
        for changed in[{'value':0,'path':['A','B'],'flag':False},{'value':None,'path':['B','A'],'flag':False},{'value':None,'path':['A','B'],'flag':0},{'value':None,'path':['A','B']}]:
            with self.assertRaises(ValueError):compare(original,changed)

if __name__=='__main__':unittest.main()
