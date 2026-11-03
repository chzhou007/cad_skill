import unittest
from proven_contacts import canonical_contact_points,validate_junction_contacts
class Contacts(unittest.TestCase):
 def test_across_rounding_boundary(self):
  ss=[dict(id=0,a=(1.,0.024),b=(1.,-2.)),dict(id=1,a=(0.,0.026),b=(2.,0.026))]
  f=canonical_contact_points(ss,[((0,0.),(1,.5),(1.,.024))])
  self.assertEqual(f(ss[0],0.),f(ss[1],.5))
 def test_unproven_nearby_kept_separate(self):
  ss=[dict(id=0,a=(1.,.024),b=(1.,-2.)),dict(id=1,a=(0.,.026),b=(2.,.026))]
  f=canonical_contact_points(ss,[])
  self.assertNotEqual(f(ss[0],0.),f(ss[1],.5))
 def test_transitive_proven_contacts(self):
  ss=[dict(id=i,a=(i,0.),b=(i,2.)) for i in range(3)]
  f=canonical_contact_points(ss,[((0,0.),(1,0.),(0.,0.)),((1,0.),(2,0.),(0.,0.))])
  self.assertEqual(f(ss[0],0.),f(ss[2],0.))
class Gate(unittest.TestCase):
 def test_missing_junction_blocks(self):
  with self.assertRaises(ValueError):validate_junction_contacts([],[],[dict(semantic_endpoint=(0,0))],.05)
 def test_three_edges_pass(self):
  n=[dict(node_id='T1',node_type='tee',x=0,y=0)];e=[dict(start_node_id='T1',end_node_id=str(i))for i in range(3)]
  self.assertTrue(validate_junction_contacts(n,e,[dict(semantic_endpoint=(0,0))],.05)[0]['valid'])
if __name__=='__main__':unittest.main()
