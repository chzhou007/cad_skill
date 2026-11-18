import copy,json,unittest
from pathlib import Path
from confirmed_equipment_interfaces import apply,prepare_direct_dn_recheck
class ConfirmedInterfaces(unittest.TestCase):
 def setUp(self):
  self.h='source-sha';self.gh='graph-sha'; self.g={'metadata':{'source_sha256':self.h},'nodes':[],'edges':[],'virtual_equipment_ports':[]}
  self.p={'source_sha256':self.h,'graph_sha256':self.gh,'confirmation':{'confirmed_by':'user','question':'Are these distinct interfaces connected?','answer':'yes'},'connections':[]}
  for i,(device,system) in enumerate([('D1','return'),('D1','supply'),('D2','return'),('D2','supply')]):
   n=f'V{i}';e=f'E{i}';t=f'T{i}';h=f'H{i}';dh='body-'+device;port=n+'-P1'
   self.g['nodes'] += [{'node_id':n,'node_type':'virtual_equipment','subtype':'out_of_plane_interface','floor':2,'system':system,'x':i*10.,'y':1.,'source_handle':h,'source_handles':[h],'ports':[{'port_id':port,'system':system}]},{'node_id':t,'node_type':'tee','floor':2}]
   self.g['edges'].append({'edge_id':e,'start_node_id':t,'end_node_id':n,'end_port_id':port,'system':system,'path':[[i*10.,0.],[i*10.,1.]],'source_handles':['line-'+str(i)],'path_length':1})
   self.g['virtual_equipment_ports'].append({'virtual_equipment_id':n,'port_id':port})
   self.p['connections'].append({'interface_id':n,'edge_id':e,'equipment_id':device,'system':system,'interface_handle':h,'equipment_handle':dh})
  for d in ('D1','D2'):self.g['nodes'].append({'node_id':d,'node_type':'equipment','floor':2,'source_handle':'body-'+d})
  self.inv={'source_sha256':self.h,'graph_sha256':self.gh,'equipment':[{'node_id':x['equipment_id'],'source_handle':x['equipment_handle']} for x in self.p['connections']]}
 def call(self):return apply(self.g,self.p,self.inv,self.h,self.gh)
 def test_four_links_preserve_source_and_separate_systems(self):
  before=copy.deepcopy(self.g);out,audit=self.call();self.assertEqual(self.g,before);self.assertEqual(len(audit['mappings']),4)
  self.assertEqual(len(out['nodes']),len(before['nodes'])-4);self.assertEqual(len(out['edges']),len(before['edges']))
  for r in self.p['connections']:
   e=next(x for x in out['edges'] if x['edge_id']==r['edge_id']);old=next(x for x in before['edges'] if x['edge_id']==r['edge_id'])
   self.assertEqual(e['end_node_id'],r['equipment_id']);self.assertEqual(e['system'],r['system']);self.assertEqual(e['path'],old['path']);self.assertEqual(e['source_handles'],old['source_handles']);self.assertFalse(e['path_length_complete']);self.assertFalse(e['confirmed_equipment_interface']['physical_port_verified'])
  self.assertFalse(out['metadata']['hil_ready']);self.assertEqual(out['preHilComparison']['status'],'pending')
 def test_fail_closed_wrong_system(self):
  self.p['connections'][0]['system']='supply'
  with self.assertRaises(ValueError):self.call()
 def test_repeated_confirmation_retains_earlier_audit(self):
  self.g['confirmedEquipmentInterfaceRepair']={'source_sha256':self.h,'mappings':[{'retired_node_id':'historical'}]}
  out,_=self.call();self.assertEqual(out['confirmedEquipmentInterfaceRepair']['previous_repair']['mappings'][0]['retired_node_id'],'historical')
 def test_fail_closed_wrong_hash(self):
  self.p['graph_sha256']='wrong'
  with self.assertRaises(ValueError):self.call()
 def test_fail_closed_missing_confirmation(self):
  self.p['confirmation']['answer']=''
  with self.assertRaises(ValueError):self.call()
 def test_fail_closed_duplicate_or_unpaired(self):
  self.p['connections'].pop()
  with self.assertRaises(ValueError):self.call()
 def test_fail_closed_device_handle(self):
  self.p['connections'][0]['equipment_handle']='wrong'
  with self.assertRaises(ValueError):self.call()
 def test_dn_recheck_binds_new_graph_and_rejects_geometry_change(self):
  out,_=self.call();p={'source_sha256':self.h,'graph_sha256':self.gh,'text_layers':['空调平面'],'selections':[{'edge_id':'E0'}]};raw=json.dumps(p,ensure_ascii=False).encode('utf8')
  rebound=prepare_direct_dn_recheck(self.g,out,raw,self.h,self.gh,'new-graph')
  self.assertEqual(rebound['graph_sha256'],'new-graph');self.assertEqual(rebound['prior_graph_sha256'],self.gh)
  out['edges'][0]['path'][0][0]+=1
  with self.assertRaises(ValueError):prepare_direct_dn_recheck(self.g,out,raw,self.h,self.gh,'new-graph')
 def test_dn_recheck_rejects_stale_or_empty_policy(self):
  out,_=self.call();p={'source_sha256':self.h,'graph_sha256':'stale','text_layers':['空调平面'],'selections':[{'edge_id':'E0'}]}
  with self.assertRaises(ValueError):prepare_direct_dn_recheck(self.g,out,json.dumps(p).encode(),self.h,self.gh,'new')
  p['graph_sha256']=self.gh;p['selections']=[]
  with self.assertRaises(ValueError):prepare_direct_dn_recheck(self.g,out,json.dumps(p).encode(),self.h,self.gh,'new')
if __name__=='__main__':unittest.main()
