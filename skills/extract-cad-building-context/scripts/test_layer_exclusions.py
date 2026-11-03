import unittest
from architecture_context import category
class LayerExclusion(unittest.TestCase):
 def test_mep_names_are_not_doors(self):
  for layer in ['HVAC-D-阀门仪表','HVAC-阀件','HVAC-仪表','MEP-VALVE','MEP-INSTRUMENT']:self.assertIsNone(category(layer))
 def test_real_doors_remain(self):
  for layer in ['A-DOOR','建筑-门']:self.assertEqual(category(layer),'door')
if __name__=='__main__':unittest.main()
