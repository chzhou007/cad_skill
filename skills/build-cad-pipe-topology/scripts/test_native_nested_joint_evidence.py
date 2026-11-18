import copy, unittest, ezdxf, subprocess, sys
from pathlib import Path
from native_device_circle_lines import collect as circle_collect
from native_nested_joint_evidence import collect, fingerprint


def fixture(mirror=False):
 d=ezdxf.new(); j=d.blocks.new('HOSE'); j.add_line((0,-1),(0,1));j.add_line((10,-1),(10,1))
 for x in (2,4,6,8):j.add_arc((x,0),1,0,180)
 b=d.blocks.new('EQ');b.add_circle((-10,0),1);b.add_line((-10,0),(0,0),dxfattribs={'layer':'空调冷冻水供水'});b.add_line((10,0),(20,0),dxfattribs={'layer':'空调冷冻水供水'});b.add_blockref('HOSE',(0,0))
 root=d.modelspace().add_blockref('EQ',(100,200),dxfattribs={'rotation':90,'xscale':-1 if mirror else 1})
 m=root.matrix44();a=m.transform((10,0,0));z=m.transform((20,0,0));pt=m.transform((0,0,0))
 graph={'edges':[{'edge_id':'E','system':'supply','source_insert_handle':root.dxf.handle,'device_label':'D','attribute_paths':[[[a.x,a.y],[z.x,z.y]]]}]}
 circle=circle_collect(d,graph,{'source_sha256':'S','graph_sha256':'G','edges':['E']},'S','G')
 inventory=[{'edge_id':'E','source_top_handle':root.dxf.handle,'source_block_name':'HOSE','equipment_type':'金属软接','assignment_status':'assigned','x':str(pt.x),'y':str(pt.y),'device_name':'J'}]
 hashes={'source_sha256':'S','graph_sha256':'G','inventory_sha256':'I','circle_sha256':'C'}
 policy=dict(hashes,joint_block='HOSE',block_fingerprint_sha256=fingerprint(j),edges=['E'])
 return d,graph,inventory,circle,policy,hashes


class JointEvidenceTest(unittest.TestCase):
 def test_evidence_and_mirror_preserve_graph(self):
  for mirror in (False,True):
   d,g,i,c,p,h=fixture(mirror);before=copy.deepcopy(g);r=collect(d,g,i,c,p,h);row=r['edges'][0]
   self.assertEqual(g,before);self.assertEqual(row['status'],'unique_source_symbol_evidence');self.assertEqual(row['matches'][0]['physical_length'],'unknown')
 def test_component_assignment_and_opposite_system_are_required(self):
  d,g,i,c,p,h=fixture();i[0]['edge_id']='other';self.assertEqual(collect(d,g,i,c,p,h)['edges'][0]['status'],'unresolved_no_unique_evidence')
  d,g,i,c,p,h=fixture();g['edges'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'edge/source'):collect(d,g,i,c,p,h)
 def test_fingerprint_and_hash_fail_closed(self):
  d,g,i,c,p,h=fixture();p['block_fingerprint_sha256']='wrong'
  with self.assertRaisesRegex(ValueError,'definition'):collect(d,g,i,c,p,h)
  d,g,i,c,p,h=fixture();h['inventory_sha256']='wrong'
  with self.assertRaisesRegex(ValueError,'hash'):collect(d,g,i,c,p,h)
 def test_duplicate_component_is_not_chosen(self):
  d,g,i,c,p,h=fixture();i.append(dict(i[0],device_name='J2'));self.assertEqual(collect(d,g,i,c,p,h)['edges'][0]['status'],'unresolved_no_unique_evidence')
 def test_joint_claimed_by_two_edges_is_not_unique(self):
  d,g,i,c,p,h=fixture();g['edges'].append(dict(g['edges'][0],edge_id='F'));i.append(dict(i[0],edge_id='F'));c['edges'].append(dict(c['edges'][0],edge_id='F'));p['edges'].append('F')
  r=collect(d,g,i,c,p,h)
  self.assertEqual([e['status'] for e in r['edges']],['unresolved_shared_source_identity']*2)
 def test_circle_z_disagreement_is_unresolved(self):
  d,g,i,c,p,h=fixture();c['edges'][0]['candidates'][0]['circles'][0]['z_coincident']=False
  self.assertEqual(collect(d,g,i,c,p,h)['edges'][0]['status'],'unresolved_no_unique_evidence')
 def test_supplemental_entry_requires_both_policies(self):
  script=Path(__file__).with_name('build_isometric_v17.py')
  r=subprocess.run([sys.executable,str(script),'--supplemental-device-circle-policy','unused'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('must be supplied together',r.stderr)
 def test_entry_requires_circle_policy(self):
  script=Path(__file__).with_name('build_isometric_v17.py')
  r=subprocess.run([sys.executable,str(script),'--nested-joint-policy','unused'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('requires device circle line evidence',r.stderr)


if __name__=='__main__':unittest.main()
