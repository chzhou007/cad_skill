import copy,unittest
from group_ambiguous_dn_patterns import group

def fixture():
 def row(handle):return {'text_handle':handle,'text':'DN300','status':'ambiguous_source_lines','height':350,'rotation_degrees':0,'native_line_candidates':[{'system':'supply','provenance':{'scope':'modelspace'},'distance_drawing_units':10},{'system':'return','provenance':{'scope':'modelspace'},'distance_drawing_units':20}]}
 return {'status':'native_dn_bulk_screen_candidates_only','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[row('A'),row('B')]},{'groups':[{'text_handles':['A','B']}]}
class AmbiguousDNPatternsTest(unittest.TestCase):
 def test_group_keeps_ambiguity_and_original(self):
  s,p=fixture();old=copy.deepcopy(s);r=group(s,p);self.assertEqual(s,old);self.assertIsNone(r['groups'][0]['selected_owner']);self.assertFalse(r['hil_ready'])
 def test_different_distance_or_system_rejected(self):
  s,p=fixture();s['records'][1]['native_line_candidates'][1]['distance_drawing_units']+=1
  with self.assertRaisesRegex(ValueError,'differ'):group(s,p)
  s,p=fixture();s['records'][1]['native_line_candidates'][1]['system']='supply'
  with self.assertRaisesRegex(ValueError,'differ'):group(s,p)
 def test_duplicate_and_preaccepted_source_rejected(self):
  s,p=fixture();p['groups'].append({'text_handles':['A','B']})
  with self.assertRaises(ValueError):group(s,p)
  s,p=fixture();s['human_accepted']=True
  with self.assertRaises(ValueError):group(s,p)
if __name__=='__main__':unittest.main()
