import unittest
import pipe_geometry as geometry

class OverlaidServiceNetwork(unittest.TestCase):
 def setUp(self): geometry.set_tolerance(.01)
 def segment(self,handle,service,a,b):
  return {'handle':handle,'system':'physical','source_system':service,'a':a,'b':b}
 def test_overlaid_mains_have_separate_system_tees_and_source_coverage(self):
  segments=[self.segment('S-M','supply',(-10,0),(10,0)),self.segment('R-M','return',(-10,0),(10,0)),self.segment('S-B','supply',(0,0),(0,5)),self.segment('R-B','return',(0,0),(0,-5))]
  vertices,pieces,adj=geometry.build_network(segments,partition_by_source_system=True)
  tees=[i for i,p in enumerate(vertices) if geometry.dist(p,(0,0))<.01]
  self.assertEqual(len(tees),2)
  self.assertEqual(sorted(len(adj['physical',v]) for v in tees),[3,3])
  handles=[{h for j in adj['physical',v] for h in pieces[j]['source_handles']} for v in tees]
  self.assertCountEqual(handles,[{'S-M','S-B'},{'R-M','R-B'}])
 def test_a_branch_on_one_service_does_not_split_the_other(self):
  s=[self.segment('S','supply',(-10,0),(10,0)),self.segment('R','return',(-10,0),(10,0)),self.segment('B','return',(0,0),(0,5))]
  vertices,pieces,adj=geometry.build_network(s,partition_by_source_system=True)
  supply=[p for p in pieces if 'S' in p['source_handles']];self.assertEqual(len(supply),1)
  tees=[v for v in range(len(vertices)) if len(adj.get(('physical',v),[]))==3];self.assertEqual(len(tees),1)
  self.assertEqual({h for j in adj['physical',tees[0]] for h in pieces[j]['source_handles']},{'R','B'})
 def test_unknown_service_is_not_merged_into_a_known_service(self):
  s=[self.segment('S','supply',(-10,0),(10,0)),self.segment('U','unclassified_water',(-10,0),(10,0))]
  vertices,pieces,adj=geometry.build_network(s,partition_by_source_system=True);self.assertEqual(len(pieces),2);self.assertFalse(set(pieces[0]['vertices'])&set(pieces[1]['vertices']))
 def test_missing_partition_rejected(self):
  with self.assertRaises(ValueError):geometry.build_network([{'handle':'X','system':'physical','a':(0,0),'b':(1,0)}],partition_by_source_system=True)

if __name__=='__main__':unittest.main()
