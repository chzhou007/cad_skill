import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import detail_frame_context

class DetailFrameGate(unittest.TestCase):
 def test_frame_context_keeps_each_relation_unverified_and_rejects_stale(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'reports';p.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();row={'system':'supply','rank':1,'upper_edge':'A','detail_edge':'B'}
   glyph=p/'source-detail-glyph-ambiguity.json';glyph.write_text(json.dumps({'rows':[row]}),encoding='utf8')
   e={'status':'source_dashed_frame_context_not_mapping','source_sha256':'S','graph_sha256':'G','glyphs_sha256':sha(glyph),'policy_sha256':'P','mapping_ready':False,'human_accepted':False,'graph_mutated':False,'hil_ready':False,'frames':[{'frame_id':'L'}],'candidate_rows':[{**row,'status':'source_frame_context_not_individual_mapping','shared_frame_candidates':['L']}]}
   screen=p/'source-detail-frame-context.json';screen.write_text(json.dumps(e),encoding='utf8');s={'status':e['status'],'source_sha256':'S','graph_sha256':'G','evidence_sha256':sha(screen),'policy_sha256':'P','mapping_ready':False,'hil_ready':False,'candidate_count':1};(p/'source-detail-frame-context-stage.json').write_text(json.dumps(s),encoding='utf8')
   out=detail_frame_context(root,'G','S');self.assertEqual(out[0]['status'],'individual_mapping_unverified')
   rel={'status':'frame_relative_position_not_mapping','source_sha256':'S','graph_sha256':'G','glyphs_sha256':sha(glyph),'frames_sha256':sha(screen),'script_sha256':'R','mapping_ready':False,'human_accepted':False,'graph_mutated':False,'records':[{'system':'supply','rank':1,'upper_edge':'A','proposed_detail_edge':'B','status':'regional_position_evidence_not_mapping'}]};rp=p/'source-detail-frame-relative-candidates.json';rp.write_text(json.dumps(rel),encoding='utf8');s['relative_evidence_sha256']=sha(rp);s['relative_script_sha256']='R';(p/'source-detail-frame-context-stage.json').write_text(json.dumps(s),encoding='utf8');self.assertEqual(len(detail_frame_context(root,'G','S')),1)
   rp.write_text('{}',encoding='utf8')
   with self.assertRaises(ValueError):detail_frame_context(root,'G','S')
   rp.write_text(json.dumps(rel),encoding='utf8')
   scope=p/'detail-scope-coverage.json';scope.write_text('{}',encoding='utf8');br={'system':'return','upper_glyph':'U','detail_boundary':'D','detail_edge':'E'};bound=p/'detail-boundary-coverage.json';bound.write_text(json.dumps({'rows':[br]}),encoding='utf8');v={'status':'frame_boundary_candidates_not_mapping','source_sha256':'S','graph_sha256':'G','frames_sha256':sha(screen),'scope_sha256':sha(scope),'boundaries_sha256':sha(bound),'script_sha256':'Z','mapping_ready':False,'human_accepted':False,'graph_mutated':False,'records':[{**br,'status':'source_frame_boundary_context_not_mapping','boundary_kind':'expert_non_node_source_boundary','frame_id':'L'}]};bp=p/'source-detail-frame-boundary-candidates.json';bp.write_text(json.dumps(v),encoding='utf8');s['boundary_evidence_sha256']=sha(bp);s['boundary_script_sha256']='Z';(p/'source-detail-frame-context-stage.json').write_text(json.dumps(s),encoding='utf8');self.assertEqual(len(detail_frame_context(root,'G','S')),2)
   bp.write_text('{}',encoding='utf8')
   with self.assertRaises(ValueError):detail_frame_context(root,'G','S')
   glyph.write_text('{}',encoding='utf8')
   with self.assertRaises(ValueError):detail_frame_context(root,'G','S')
if __name__=='__main__':unittest.main()
