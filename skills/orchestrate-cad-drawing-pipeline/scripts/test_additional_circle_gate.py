import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import check

class AdditionalCircleGateTest(unittest.TestCase):
 def test_extra_radius_blocks_and_missing_evidence_fails(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);reports=root/'reports';reports.mkdir();gp=root/'graph.json';gp.write_text(json.dumps({'metadata':{'source_sha256':'SRC'},'nodes':[],'edges':[]}),encoding='utf8');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();h=sha(gp)
   primary=reports/'source-circle-rim-screen.json';screen={'status':'source_shape_comparison_not_connectivity','source_sha256':'SRC','graph_sha256':h,'candidates':[],'ambiguous_native_geometry':[],'unsupported_circle_transforms':[]};primary.write_text(json.dumps(screen),encoding='utf8');(reports/'source-circle-rim-screen-stage.json').write_text(json.dumps({'source_sha256':'SRC','graph_sha256':h,'evidence_sha256':sha(primary)}),encoding='utf8')
   extra=reports/'source-circle-rim-extra-1.json';screen.update(circle_radius=100,policy_sha256='a'*64,graph_mutated=False,hil_ready=False,candidates=[{'circle_handle':'C100','line_system':'supply','status':'source_shape_graph_connection_not_established'}]);extra.write_text(json.dumps(screen),encoding='utf8')
   stage={'status':'additional_circle_screens_required','source_sha256':'SRC','graph_sha256':h,'policy_map_sha256':'b'*64,'hil_ready':False,'screens':[{'path':'reports/source-circle-rim-extra-1.json','radius':100,'policy_sha256':'a'*64,'evidence_sha256':sha(extra)}]};(reports/'source-circle-rim-additional-stage.json').write_text(json.dumps(stage),encoding='utf8');other=root/'source.png';other.write_bytes(b'source');report={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'x','status':'resolved','source_handles':['C100'],'disposition':'scope reviewed'}],'native_comparisons':[{'path':'source.png','sha256':sha(other)}]}
   result=check(report,h,root,gp);self.assertEqual(result['status'],'pending');self.assertEqual([x['circle_handle'] for x in result['circle_rim_screen_blockers']],['C100'])
   extra.unlink();self.assertEqual(check(report,h,root,gp)['status'],'failed')
if __name__=='__main__':unittest.main()
