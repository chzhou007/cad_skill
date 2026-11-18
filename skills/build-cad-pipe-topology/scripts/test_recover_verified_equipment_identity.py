import copy,unittest,ezdxf
from recover_verified_equipment_identity import unique_matching,recover

def fixture():
 d=ezdxf.new();b=d.blocks.new('40kW');b.add_lwpolyline([(0,0),(500,0),(500,500),(0,500)],close=True);m=d.modelspace();a=m.add_blockref('40kW',(0,0),dxfattribs={'layer':'空调'});z=m.add_blockref('40kW',(1000,0),dxfattribs={'layer':'空调'});t1=m.add_text('CRAH-1',dxfattribs={'insert':(-100,-100),'layer':'空调编号'});t2=m.add_text('CRAH-2',dxfattribs={'insert':(900,-100),'layer':'空调编号'});bindings=[{'source_handle':a.dxf.handle,'source_block':'40kW','bounds':[[0,0,0],[500,500,0]],'label_candidates':['CRAH-1','CRAH-2'],'parameter_candidates':['unknown']},{'source_handle':z.dxf.handle,'source_block':'40kW','bounds':[[1000,0,0],[1500,500,0]],'label_candidates':['CRAH-2'],'parameter_candidates':['unknown']}];g={'metadata':{'source_sha256':'S','hil_ready':False},'nodes':[{'node_id':'CRAH-2','node_type':'equipment','source_handle':z.dxf.handle}],'edges':[]};p={'source_sha256':'S','graph_sha256':'G','bindings_sha256':'B','group':{'source_handles':[a.dxf.handle,z.dxf.handle],'label_handles':{'CRAH-1':t1.dxf.handle,'CRAH-2':t2.dxf.handle},'expected_recovered_labels':['CRAH-1'],'floor':2}};return d,g,bindings,p
class EquipmentIdentityTest(unittest.TestCase):
 def test_unique_assignment_recovers_device_not_connection(self):
  d,g,b,p=fixture();old=copy.deepcopy(g);out,a=recover(d,g,b,p,'S','G','B');self.assertEqual(g,old);self.assertEqual(a['recovered_nodes'],['CRAH-1']);self.assertEqual(out['edges'],[]);self.assertEqual(out['nodes'][-1]['connection_status'],'ports_unresolved');self.assertFalse(out['metadata']['hil_ready'])
 def test_ambiguous_and_unbalanced_fail_closed(self):
  for matrix in ({'a':['x','y'],'b':['x','y']},{'a':['x','y']}):
   with self.assertRaises(ValueError):unique_matching(matrix)
 def test_changed_source_and_existing_claim_rejected(self):
  d,g,b,p=fixture();b[0]['bounds'][0][0]=1
  with self.assertRaisesRegex(ValueError,'bounds'):recover(d,g,b,p,'S','G','B')
  d,g,b,p=fixture();g['nodes'][0]['source_handle']='wrong'
  with self.assertRaisesRegex(ValueError,'contradicts'):recover(d,g,b,p,'S','G','B')
 def test_external_candidate_and_bad_hash_rejected(self):
  d,g,b,p=fixture();b.append({'source_handle':'outside','label_candidates':['CRAH-1']})
  with self.assertRaisesRegex(ValueError,'overlaps outside'):recover(d,g,b,p,'S','G','B')
  d,g,b,p=fixture()
  with self.assertRaisesRegex(ValueError,'hash'):recover(d,g,b,p,'bad','G','B')
if __name__=='__main__':unittest.main()
