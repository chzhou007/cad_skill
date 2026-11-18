"""Upgrade backup and directory isolation without touching CAD or annotations."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
ASSETS=Path(__file__).resolve().parents[1]/'assets/viewer'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inventory(root):return {p.relative_to(root).as_posix():sha(p)for p in Path(root).rglob('*')if p.is_file()}
def upgrade(parent,output,port):
 parent,output=Path(parent).resolve(),Path(output).resolve()
 if output.exists():raise FileExistsError(output)
 shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc','startup-logs'))
 files=['hil_server.py','review_backup.py','serve.py','public/hil.js','public/edge-review.js']
 for name in files:shutil.copy2(ASSETS/name,output/name)
 mpath=output/'public/data/manifest.json';m=json.loads(mpath.read_text('utf8'));old=m['bundleId'];hashes={name:sha(output/name)for name in files}
 m['templateHashes'].update(hashes)
 for section in ['edgeReviewUI','edgeAttributeEditorFix']:
  if 'assets'in m.get(section,{}):m[section]['assets'].update({n:h for n,h in hashes.items()if n in m[section]['assets']})
 m['offlineReviewSafety']=dict(backup_restores_manual_attributes_and_notes=True,isolated_extraction_directories=True,assets=hashes)
 m['bundleId']=hashlib.sha256(json.dumps([old,hashes],sort_keys=True).encode()).hexdigest()[:20];m['preferredPort']=port
 mpath.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 index=output/'public/index.html';index.write_text(index.read_text('utf8').replace(old,m['bundleId']),encoding='utf8')
 assert inventory(parent/'annotations')==inventory(output/'annotations')
 assert inventory(parent/'public/data')=={**inventory(output/'public/data'),'manifest.json':sha(parent/'public/data/manifest.json')}
 return dict(viewer=str(output),bundleId=m['bundleId'],source_and_annotations_unchanged=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--parent',required=True);p.add_argument('--output',required=True);p.add_argument('--port',type=int,default=10571);a=p.parse_args();print(json.dumps(upgrade(a.parent,a.output,a.port),ensure_ascii=False))
