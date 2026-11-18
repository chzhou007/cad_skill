import copy,unittest,ezdxf
from native_junction_ray_evidence import collect

def fixture():
 d=ezdxf.new();m=d.modelspace();layer='空调冷冻水供水';main=m.add_line((-10,0),(10,0),dxfattribs={'layer':layer});branch=m.add_line((0,0),(0,10),dxfattribs={'layer':layer});nodes=[{'node_id':'T','node_type':'physical_junction','x':0,'y':0}];edges=[]
 for eid,a,b in [('L',[-10,0],[0,0]),('R',[0,0],[10,0]),('B',[0,0],[0,10])]:edges.append({'edge_id':eid,'start_node_id':'T','end_node_id':eid,'system':'supply','attribute_paths':[[a,b]]})
 g={'nodes':nodes,'edges':edges};p={'source_sha256':'S','graph_sha256':'G','junctions':[{'node_id':'T','edge_witnesses':{'L':main.dxf.handle,'R':main.dxf.handle,'B':branch.dxf.handle}}]};return d,g,p
class NativeJunctionRaysTest(unittest.TestCase):
 def test_three_source_rays_not_mutating(self):
  d,g,p=fixture();before=copy.deepcopy(g);r=collect(d,g,p,'S','G');self.assertEqual(g,before);self.assertEqual(len(r['junctions'][0]['source_rays']),3);self.assertEqual({x['contact'] for x in r['junctions'][0]['native_line_contacts']},{'endpoint','interior'});self.assertFalse(r['hil_ready'])
 def test_opposite_system_contact_recorded_never_joined(self):
  d,g,p=fixture();d.modelspace().add_line((0,-10),(0,10),dxfattribs={'layer':'空调冷冻水回水'});r=collect(d,g,p,'S','G');self.assertEqual(len(r['junctions'][0]['opposite_system_contacts']),1)
 def test_extra_same_system_and_wrong_graph_rejected(self):
  d,g,p=fixture();d.modelspace().add_line((0,-10),(0,0),dxfattribs={'layer':'空调冷冻水供水'})
  with self.assertRaisesRegex(ValueError,'unaccounted'):collect(d,g,p,'S','G')
  d,g,p=fixture();g['edges'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'mixed'):collect(d,g,p,'S','G')
 def test_stale_and_ambiguous_source_rejected(self):
  d,g,p=fixture()
  with self.assertRaisesRegex(ValueError,'hash'):collect(d,g,p,'bad','G')
  d,g,p=fixture();d.modelspace().add_line((-10,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'})
  with self.assertRaisesRegex(ValueError,'ambiguous'):collect(d,g,p,'S','G')
 def test_branch_witness_in_selected_nested_insert(self):
  d,g,p=fixture();m=d.modelspace();branch=d.entitydb[p['junctions'][0]['edge_witnesses']['B']];m.delete_entity(branch)
  nested=d.blocks.new('INNER');nested.add_line((0,0),(0,10),dxfattribs={'layer':'空调冷冻水供水'})
  outer=d.blocks.new('OUTER');outer.add_blockref('INNER',(0,0));insert=m.add_blockref('OUTER',(0,0))
  g['edges'][2]['source_insert_handle']=insert.dxf.handle;p['junctions'][0]['edge_witnesses']['B']={'scope':'decomposed_selected_insert','insert_handle':insert.dxf.handle}
  r=collect(d,g,p,'S','G');ray=next(x for x in r['junctions'][0]['source_rays'] if x['edge_id']=='B')
  self.assertEqual(ray['source_insert_handle'],insert.dxf.handle);self.assertEqual(ray['scope'],'decomposed_selected_insert')
  nested.add_line((0,0),(0,10),dxfattribs={'layer':'空调冷冻水供水'})
  with self.assertRaisesRegex(ValueError,'nested ray source line ambiguous'):collect(d,g,p,'S','G')
 def test_wrong_nested_insert_rejected(self):
  d,g,p=fixture();insert=d.modelspace().add_blockref(d.blocks.new('EMPTY').name,(0,0));p['junctions'][0]['edge_witnesses']['B']={'scope':'decomposed_selected_insert','insert_handle':insert.dxf.handle}
  with self.assertRaisesRegex(ValueError,'insert mismatch'):collect(d,g,p,'S','G')
if __name__=='__main__':unittest.main()
