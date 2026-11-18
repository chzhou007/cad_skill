import copy
import unittest
import ezdxf
from final_plan_line_coverage import inventory
from coincident_plan_source_segments import compare


class CoincidentPlanSegmentsTest(unittest.TestCase):
 def fixture(self):
  doc=ezdxf.new();m=doc.modelspace()
  main=m.add_line((0,0,0),(20,0,0),dxfattribs={'layer':'S'})
  candidate=m.add_line((20,0,0),(0,0,0),dxfattribs={'layer':'S'})
  graph={'metadata':{'source_sha256':'source'},'edges':[
   {'edge_id':'a','system':'supply','source_handles':[main.dxf.handle], 'attribute_paths':[[[0,0],[10,0],[10,5]]]},
   {'edge_id':'b','system':'supply','source_handles':[main.dxf.handle], 'attribute_paths':[[[10,0],[20,0]]]}]}
  policy={'source_sha256':'source','graph_sha256':'graph','system_layers':{'S':'supply'},'normalization_tolerance':.05}
  return doc,graph,inventory(doc,graph,policy,'source','graph'),candidate

 def test_scoped_spans_do_not_infer_identity_or_branch(self):
  d,g,i,c=self.fixture();r=compare(d,g,i,'source','graph');self.assertEqual(len(r['records']),1)
  row=r['records'][0];self.assertEqual(row['unreferenced_source_handle'],c.dxf.handle)
  self.assertFalse(row['physical_identity_resolved']);self.assertFalse(r['graph_mutated'])
  self.assertEqual([len(e['overlap_spans']) for e in row['related_edges']],[1,1])
  self.assertEqual([e['overlap_spans'][0]['drawing_overlap_length'] for e in row['related_edges']],[10,10])

 def test_stale_or_conflicting_evidence_fails(self):
  d,g,i,_=self.fixture()
  with self.assertRaises(ValueError):compare(d,g,i,'source','new-graph')
  bad=copy.deepcopy(i);bad['records'][-1]['coincident_referenced_sources'][0]['edge_ids']=['a']
  with self.assertRaises(ValueError):compare(d,g,bad,'source','graph')
  bad=copy.deepcopy(g);bad['edges'][1]['system']='return'
  with self.assertRaises(ValueError):compare(d,bad,i,'source','graph')
  bad=copy.deepcopy(i);bad['normalization_tolerance']=.1
  with self.assertRaises(ValueError):compare(d,g,bad,'source','graph')

 def test_z_offset_is_not_a_candidate(self):
  d,g,_,c=self.fixture();c.dxf.start=(20,0,1);c.dxf.end=(0,0,1)
  p={'source_sha256':'source','graph_sha256':'graph','system_layers':{'S':'supply'},'normalization_tolerance':.05}
  i=inventory(d,g,p,'source','graph');self.assertEqual(compare(d,g,i,'source','graph')['records'],[])

if __name__=='__main__':unittest.main()
