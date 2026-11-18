import copy,unittest
from paired_endpoint_dn_evidence import group

def fixture():
 def row(h,sd,rd):
  return {'text_handle':h,'text':'DN200','nominal_mm_candidate':200,'status':'no_source_line_in_local_scope','endpoint_context_candidates':[{'system':'supply','provenance':{'scope':'modelspace','handle':'S'},'distance_drawing_units':sd,'graph_segment_candidates':[{'edge_id':'ES'}]},{'system':'return','provenance':{'scope':'modelspace','handle':'R'},'distance_drawing_units':rd,'graph_segment_candidates':[{'edge_id':'ER'}]}]}
 return {'status':'native_dn_bulk_screen_candidates_only','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[row('A',1,2),row('B',3,1)]},{'groups':[{'text_handles':['A','B']}]}

class PairedEndpointTests(unittest.TestCase):
 def test_both_assignments_retained_no_selection_or_mutation(self):
  s,p=fixture();before=copy.deepcopy(s);r=group(s,p);self.assertEqual(s,before);self.assertEqual(len(r['groups'][0]['alternatives']),2);self.assertIsNone(r['groups'][0]['selected_alternative']);self.assertFalse(r['hil_ready'])
 def test_extra_or_changed_line_and_missing_dn_fail_closed(self):
  s,p=fixture();s['records'][1]['endpoint_context_candidates'][0]['provenance']['handle']='OTHER'
  with self.assertRaises(ValueError):group(s,p)
  s,p=fixture();s['records'][0]['nominal_mm_candidate']=s['records'][1]['nominal_mm_candidate']=None
  with self.assertRaises(ValueError):group(s,p)
 def test_duplicate_group_and_already_attributed_rejected(self):
  s,p=fixture();p['groups'].append({'text_handles':['B','A']})
  with self.assertRaises(ValueError):group(s,p)
  s,p=fixture();s['records'][0]['status']='unique_source_line_and_graph_segment_candidate'
  with self.assertRaises(ValueError):group(s,p)

if __name__=='__main__':unittest.main()
