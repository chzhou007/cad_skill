"""Rebuild a source-bound profile fixture without changing its expected baseline."""
import argparse,json,hashlib,subprocess,sys,tempfile
from pathlib import Path

def run(case,out,expect_source_blockers=False):
 for name,wanted in json.loads((case/'manifest.json').read_text(encoding='utf8')).items():
  assert hashlib.sha256((case/name).read_bytes()).hexdigest()==wanted,'Fixture changed: '+name
 i=case/'inputs';cmd=[sys.executable,'-X','utf8',str(Path(__file__).with_name('build_schematic.py'))]
 for key,p in [('dxf',next(i.glob('*.dxf'))),('bindings',i/'bindings.json'),('profiles',i/'profiles.json'),('materials',i/'materials.json'),('config',i/'source-profile.json'),('previous-graph',i/'previous-graph.json'),('output-dir',out)]:cmd+=['--'+key,str(p)]
 result=subprocess.run(cmd)
 if expect_source_blockers:
  assert result.returncode!=0,'Expected historical source-group defect was not blocked'
  blockers=json.loads((out/'source_group_gap_blockers.json').read_text(encoding='utf8'));assert blockers
  print(json.dumps({'case':case.name,'status':'PASS_EXPECTED_SOURCE_GROUP_BLOCK','blocked_candidates':len(blockers)}));return
 result.check_returncode()
 for expected in (case/'expected').glob('*.json'):
  assert json.loads((out/expected.name).read_text(encoding='utf8'))==json.loads(expected.read_text(encoding='utf8')),'Regression changed: '+expected.name
 print(json.dumps({'case':case.name,'status':'PASS','human_review':'unreviewed'}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--case',type=Path,required=True);parser.add_argument('--output',type=Path);parser.add_argument('--expect-source-blockers',action='store_true');a=parser.parse_args()
 if a.output:run(a.case,a.output,a.expect_source_blockers)
 else:
  with tempfile.TemporaryDirectory(prefix='cad-profile-regression-')as tmp:run(a.case,Path(tmp)/'result',a.expect_source_blockers)
