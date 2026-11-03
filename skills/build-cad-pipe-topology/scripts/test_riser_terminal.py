import unittest
from cad_ceiling_native_rules import riser_terminal_candidate
class Riser(unittest.TestCase):
 def test_circle_with_unique_radial_pipe_is_interface(self):
  c=dict(center=(0,0),radius=225,system='supply');s=dict(a=(225,0),b=(2000,0),system='supply');self.assertIsNotNone(riser_terminal_candidate(c,[s],[225]))
 def test_plain_unknown_circle_does_not_create_interface(self):
  self.assertIsNone(riser_terminal_candidate(dict(center=(0,0),radius=200,system='supply'),[dict(a=(200,0),b=(2000,0),system='supply')],[225]))
 def test_insulation_circle_has_no_matching_hydraulic_class(self):
  self.assertIsNone(riser_terminal_candidate(dict(center=(0,0),radius=225,system='return'),[dict(a=(225,0),b=(2000,0),system='supply')],[225]))
if __name__=='__main__':unittest.main()
