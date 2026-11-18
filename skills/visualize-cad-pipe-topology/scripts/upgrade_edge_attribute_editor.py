"""Upgrade a published directional viewer without rewriting data or annotations."""
import argparse,hashlib,json,shutil
from pathlib import Path
ASSETS=Path(__file__).resolve().parents[1]/'assets/viewer'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inventory(root):return {str(p.relative_to(root)):sha(p)for p in Path(root).rglob('*')if p.is_file()}
def upgrade(parent,output,port):
 parent,output=Path(parent).resolve(),Path(output).resolve()
 if output.exists():raise FileExistsError(output)
 before=inventory(parent/'annotations')if(parent/'annotations').exists()else{}
 shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc','startup-logs'))
 files=['hil_server.py','review_backup.py','edge_review_store.py','public/hil.js','public/edge-review.js','public/directional-pipe-attributes.js']
 for rel in files:shutil.copy2(ASSETS/rel,output/rel)
 app=output/'public/app.js';s=app.read_text(encoding='utf8')
 old='reviewCsvValues,reviewCsvFields}';new='reviewCsvValues,reviewCsvFields,reviewAttributeCsvFields}'
 if s.count(old)!=1 or s.count('...directionalCsvFields]')!=1:raise ValueError('Expected complete published directional reader')
 s=s.replace(old,new).replace('...directionalCsvFields]','...directionalCsvFields,...reviewAttributeCsvFields]');app.write_text(s,encoding='utf8');files.append('public/app.js')
 manifest_path=output/'public/data/manifest.json';m=json.loads(manifest_path.read_text(encoding='utf8'));old_bundle=m['bundleId'];hashes={name:sha(output/name)for name in files}
 m['templateHashes'].update(hashes);m['edgeAttributeEditorFix']=dict(source_values_unchanged=True,notes_preserved_and_editable=True,diameter_scopes=['whole_edge','horizontal','vertical'],assets=hashes)
 for section in ['edgeReviewUI','directionalPipeAttributes']:
  if 'assets' in m.get(section,{}):m[section]['assets'].update({name:digest for name,digest in hashes.items()if name in m[section]['assets']})
 m['bundleId']=hashlib.sha256(json.dumps([old_bundle,hashes],sort_keys=True).encode()).hexdigest()[:20];m['preferredPort']=port
 manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(old_bundle,m['bundleId']),encoding='utf8')
 after=inventory(output/'annotations')if(output/'annotations').exists()else{}
 if before!=after:raise ValueError('Review history changed during upgrade')
 for name in ['graph.json','graph-with-directional-attributes.json','directional-pipe-attributes.json','edge-review-queue.json']:
  if sha(parent/'public/data'/name)!=sha(output/'public/data'/name):raise ValueError('Original source data changed')
 report=dict(status='edge_diameter_and_note_editor_upgraded',viewer=str(output),bundleId=m['bundleId'],old_source_values_and_review_identity_unchanged=True,annotations_preserved=len(before),port=port)
 (output/'edge-attribute-editor-fix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--parent',required=True);p.add_argument('--output',required=True);p.add_argument('--port',type=int,default=10567);a=p.parse_args();print(json.dumps(upgrade(a.parent,a.output,a.port),ensure_ascii=False))
