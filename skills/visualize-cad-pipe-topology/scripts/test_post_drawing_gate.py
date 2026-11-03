import unittest,tempfile,json
from pathlib import Path
import ezdxf
from post_drawing_gate import check,digest

class PostDrawingGate(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.viewer=self.root/'viewer';(self.viewer/'public/data').mkdir(parents=True)
  self.source=self.root/'source.dxf';d=ezdxf.new();e=d.modelspace().add_line((10,20),(30,20));d.saveas(self.source)
  self.node={'node_id':'P','node_type':'equipment','display_source_handles':[e.dxf.handle],'sourceGeometry':[dict(points=[[0,0],[10,0]],fill=False)]}
  self.graph={'nodes':[self.node],'edges':[],'instances':[],'transform':dict(originX=10,originY=20,scale=2),'provenance':{'sha256':digest(self.source)}};self.save()
 def tearDown(self):self.tmp.cleanup()
 def save(self):(self.viewer/'public/data/graph.json').write_text(json.dumps(self.graph),encoding='utf8')
 def test_machine_success_does_not_claim_visual_or_human_review(self):
  r=check(self.viewer,self.source);self.assertEqual(r['status'],'AWAITING_VISUAL_CHECK');self.assertIn('unchanged',r['human_review'])
 def test_accepted_gap_without_final_edge_blocks(self):
  self.graph['normalizationCoverage']=[dict(id='gap1',status='applied',edge_ids=['MISSING'])];self.save();self.assertEqual(check(self.viewer,self.source)['status'],'FAIL')
 def test_unexplained_new_junction_degree_blocks(self):
  self.graph['junctionValidation']={'new_unexplained_degree_exceptions':['T1']};self.save();self.assertEqual(check(self.viewer,self.source)['status'],'FAIL')
 def test_three_edges_in_one_direction_do_not_make_a_tee(self):
  self.graph['nodes'] += [dict(node_id='T1',node_type='physical_junction',x=0,y=0)]+[dict(node_id='V'+str(i),node_type='virtual_equipment',x=i+1,y=0)for i in range(3)]
  self.graph['edges']=[dict(edge_id='E'+str(i),start_node_id='T1',end_node_id='V'+str(i),path_points=[[0,0],[i+1,0]])for i in range(3)];self.save();self.assertEqual(check(self.viewer,self.source)['status'],'FAIL')
 def test_missing_path_blocks_gate(self):
  self.node['sourceGeometry']=[];self.save();r=check(self.viewer,self.source);self.assertEqual(r['status'],'FAIL')
 def test_pending_native_component_is_checked_without_creating_connectivity(self):
  self.graph['pendingSourceObjects']=[dict(id='Unassigned',source_device_name='Unassigned',source_handles=self.node['display_source_handles'],sourceGeometry=self.node['sourceGeometry'])];self.save();r=check(self.viewer,self.source);self.assertEqual(r['machine_status'],'PASS');self.assertEqual(r['checked_instances'],2);self.assertEqual(self.graph['edges'],[])
  self.graph['pendingSourceObjects'][0]['sourceGeometry']=[];self.save();self.assertEqual(check(self.viewer,self.source)['machine_status'],'FAIL')
 def test_empty_optional_csv_handle_is_pending_not_a_json_failure(self):
  self.graph['instances']=[dict(id='I1',source_device_name='Unverified legacy instance',source_handles='')];self.save();r=check(self.viewer,self.source);self.assertEqual(r['status'],'AWAITING_VISUAL_CHECK');self.assertEqual(len(r['pending']),1)
 def test_fixed_icon_scale_blocks_native_gate(self):
  self.node['sourceGeometry'][0]['points']=[[0,0],[1,0]];self.save();self.assertEqual(check(self.viewer,self.source)['status'],'FAIL')
 def test_missing_exploded_strokes_blocks_even_if_counts_unchanged(self):
  self.graph['sourceFidelity']=[dict(id='A',status='PASS',required_source_handles=['A','B','C','D'],exported_source_handles=['A'])];self.save();self.assertEqual(check(self.viewer,self.source)['status'],'FAIL')
 def test_source_identity_mismatch_blocks(self):
  self.graph['provenance']['sha256']='wrong';self.save();self.assertEqual(check(self.viewer,self.source)['status'],'FAIL')
 def test_source_head_discovered_but_missing_from_export_blocks(self):
  self.graph['sourceTaggedHeadCoverage']=[dict(source_head_handle='MISSING',source_tag='SFIT-X2',status='represented_source_geometry')];self.save();self.assertEqual(check(self.viewer,self.source)['status'],'FAIL')
 def test_unknown_source_head_is_explicit_pending(self):
  self.graph['sourceTaggedHeadCoverage']=[dict(source_head_handle='MISSING',source_tag='SFIT-X2',status='pending_unrepresented_tagged_head')];self.save();self.assertTrue(any(r['id']=='MISSING'for r in check(self.viewer,self.source)['pending']))
 def test_parent_assembly_cannot_masquerade_as_a_component(self):
  d=ezdxf.readfile(self.source);p=d.blocks.new('PARENT');p.add_line((0,0),(1,0));d.blocks.new('GAUGE');e=d.modelspace().add_blockref('PARENT',(0,0));d.saveas(self.source);self.graph['provenance']['sha256']=digest(self.source);self.graph['instances']=[dict(id='I1',source_device_name='Gauge',source_kind='block_insert',source_block_name='GAUGE',source_handles=[e.dxf.handle],sourceGeometry=[])];self.save();r=check(self.viewer,self.source);self.assertTrue(any(e['check']=='component_source_identity'for e in r['blocking_defects']))
 def test_valid_sensor_body_may_include_its_circle_head(self):
  from instance_geometry import source_paths
  d=ezdxf.readfile(self.source);p=d.blocks.new('SENSOR');p.add_line((10,20),(30,20));body=d.modelspace().add_blockref('SENSOR',(0,0));head=d.modelspace().add_circle((40,20),2);d.saveas(self.source);hs=[body.dxf.handle,head.dxf.handle];paths=[dict(points=[[(q[0]-10)/2,(20-q[1])/2]for q in a['points']],fill=a['fill'])for a in source_paths(d,hs)];self.graph['provenance']['sha256']=digest(self.source);self.graph['instances']=[dict(id='I1',source_device_name='Sensor',source_kind='block_insert',source_top_handle=body.dxf.handle,source_block_name='SENSOR',source_handles=hs,sourceGeometry=paths)];self.save();self.assertEqual(check(self.viewer,self.source)['status'],'AWAITING_VISUAL_CHECK')
 def test_stale_visual_evidence_cannot_pass(self):
  p=self.root/'visual.json';p.write_text(json.dumps({'graph_sha256':'old','regions':[]}),encoding='utf8');self.assertEqual(check(self.viewer,self.source,p)['status'],'FAIL')
 def test_explicit_source_uncertainty_is_preserved(self):
  self.graph['review']=[dict(id='UT',reason='Unproven source terminal')];self.save();r=check(self.viewer,self.source);self.assertEqual(len(r['pending']),1);self.assertEqual(r['status'],'AWAITING_VISUAL_CHECK')
if __name__=='__main__':unittest.main(verbosity=2)
