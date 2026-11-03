"""Verify or deliberately regenerate the building-owned portable viewer dependency."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VERSIONS={'orchestrate-cad-drawing-pipeline':'1.0.5','build-cad-pipe-topology':'1.12.2',
          'extract-cad-building-context':'1.1.2','visualize-cad-pipe-topology':'2.8.4-HIL'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(sync=False):
    canonical=ROOT/'extract-cad-building-context/scripts/architecture_context.py'
    vendor=ROOT/'visualize-cad-pipe-topology/scripts/architecture_context.py'
    lock=vendor.with_name('architecture-dependency-lock.json')
    if sync:
        shutil.copy2(canonical,vendor)
        lock.write_text(json.dumps({'owner':'extract-cad-building-context','version':'1.1.1','sha256':digest(canonical)},indent=2),encoding='utf8')
    if not lock.is_file()or digest(canonical)!=digest(vendor)or json.loads(lock.read_text())['sha256']!=digest(canonical):raise ValueError('Building vendor/canonical/lock mismatch; update canonical, deliberately sync, then run regression')
    for name,version in VERSIONS.items():
        s=(ROOT/name/'SKILL.md').read_text(encoding='utf8')
        match=re.search(r'(?m)^(?:Current release:\s*\*\*v|Version:\s*\*\*)([^*]+)\*\*',s)
        if not match or match[1].replace(' HIL','-HIL')!=version:raise ValueError('Installed version differs: '+name)
        version_file=ROOT/name/'VERSION'
        if version_file.exists() and version_file.read_text(encoding='utf8').strip().replace(' HIL','-HIL')!=version:
            raise ValueError('VERSION file differs from current release: '+name)
    return {'status':'completed','versions':VERSIONS,'building_engine_version':json.loads(lock.read_text())['version'],'building_sha256':digest(canonical)}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sync',action='store_true');a=p.parse_args()
    try:print(json.dumps(verify(a.sync),indent=2))
    except (OSError,ValueError)as e:p.exit(1,str(e)+'\n')
