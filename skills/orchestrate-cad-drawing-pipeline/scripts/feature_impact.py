"""Resolve curated CAD feature impacts and execute scoped Python regressions.

This is a conservative test selector, not proof of complete source coverage or
expert acceptance. Unknown changes require all registered skills' test suites.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import math
from collections import defaultdict
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=Path(__file__).resolve().parents[1]/'assets/feature-registry.json'

def load_registry(path=REGISTRY,root=ROOT):
 data=json.loads(Path(path).read_text(encoding='utf-8'))
 if data.get('schema_version')!=1 or not isinstance(data.get('features'),list):raise ValueError('Invalid feature registry')
 features={x['id']:x for x in data['features']}
 if not features or len(features)!=len(data['features']):raise ValueError('Empty or duplicate feature IDs')
 for fid,item in features.items():
  if (not item.get('description') or not item.get('origin') or not item.get('acceptance_status') or
      not item.get('evidence_references') or not item.get('families') or not item.get('files') or not item.get('tests')):
   raise ValueError('Incomplete feature: '+fid)
  if not set(item.get('depends_on',[]))<=features.keys() or fid in item.get('depends_on',[]):raise ValueError('Invalid dependency: '+fid)
  for value in item['files']+item['tests']+item['evidence_references']:
   path=PurePosixPath(value)
   if path.is_absolute() or '..' in path.parts or not (root/Path(value)).is_file():raise ValueError('Missing or unsafe asset: '+value)
   if value in item['tests'] and (len(path.parts)!=3 or path.parts[1]!='scripts' or not path.name.startswith('test_') or path.suffix not in ('.py','.mjs')):
    raise ValueError('Unsupported test asset: '+value)
 # Detect dependency cycles; changes must have a well-defined transitive impact.
 active=set();visited=set()
 def visit(fid):
  if fid in active:raise ValueError('Feature dependency cycle: '+fid)
  if fid in visited:return
  active.add(fid)
  for dependency in features[fid].get('depends_on',[]):visit(dependency)
  active.remove(fid);visited.add(fid)
 for fid in features:visit(fid)
 return data,features

def impact(features,changed,root=ROOT):
 if not changed:raise ValueError('At least one changed path is required')
 normalized=[]
 for value in changed:
  path=PurePosixPath(value.replace('\\','/'))
  if path.is_absolute() or '..' in path.parts:raise ValueError('Changed path must be skill-root relative')
  normalized.append(path.as_posix())
 direct={fid for fid,item in features.items() if any(p in item['files'] or p in item['tests'] for p in normalized)}
 unknown=[p for p in normalized if not any(p in x['files'] or p in x['tests'] for x in features.values())]
 listed={p for x in features.values() for p in x['tests']}
 owners={PurePosixPath(p).parts[0] for p in listed}
 discovered={p.relative_to(root).as_posix() for owner in owners for p in (root/owner/'scripts').glob('test_*') if p.suffix in ('.py','.mjs')}
 unmapped_tests=sorted(discovered-listed)
 fallback=bool(unknown or unmapped_tests)
 selected=set(features) if fallback else set(direct)
 if not fallback:
  # First traverse downstream impact; then include prerequisites required to
  # evaluate the selected behavior without expanding sibling consumers again.
  changed_set=True
  while changed_set:
   add={fid for fid,x in features.items() if set(x.get('depends_on',[]))&selected}-selected
   changed_set=bool(add);selected.update(add)
  pending=list(selected)
  while pending:
   for dep in features[pending.pop()].get('depends_on',[]):
    if dep not in selected:selected.add(dep);pending.append(dep)
 tests=sorted({p for fid in selected for p in features[fid]['tests']})
 return {'direct_features':sorted(direct),'impacted_features':sorted(selected),'unknown_changed_paths':unknown,
         'unmapped_test_paths':unmapped_tests,'fallback_full_suites':fallback,'tests':tests,
         'additional_required_checks':['source-bound SH16 and LF20 family rebuilds as applicable','native CAD versus topology comparison','human review is not implied']}

def run_selected(result,root=ROOT,workers=None):
 if workers is None:workers=int(os.environ.get('CAD_TEST_WORKERS',min(22,max(1,(os.cpu_count() or 2)-2))))
 if type(workers)is not int or not 1<=workers<=32:raise ValueError('Test workers must be1..32')
 groups=defaultdict(list);javascript=defaultdict(list)
 for path in result['tests']:
  owner,_,test=PurePosixPath(path).parts
  if test.endswith('.py'):groups[owner].append(Path(test).stem)
  else:javascript[owner].append(test)
 commands=[];discovery=set()
 if result['fallback_full_suites']:
  owners={PurePosixPath(p).parts[0] for p in result['tests']}
  for owner in sorted(owners):
   scripts=root/owner/'scripts'
   # Keep original recursive discovery for package trees and the serial control.
   # Current CAD tests are flat; every discovered flat file is explicitly sharded.
   if workers==1 or any(p.parent!=scripts for p in scripts.rglob('test_*.py')):
    discovery.add(owner);commands.append((owner,[sys.executable,'-m','unittest','discover','-s',str(scripts),'-p','test_*.py']))
   else:groups[owner]=[p.stem for p in scripts.glob('test_*.py')]
   javascript[owner]=[p.name for p in scripts.glob('test_*.mjs')]
 env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
 # Shards must not depend on another test importing a sibling skill first.
 # Give every isolated child the exact tested skill roots before user paths.
 script_paths=[str(p/'scripts')for p in sorted(root.iterdir())if(p/'scripts').is_dir()]
 env['PYTHONPATH']=os.pathsep.join(script_paths+([env['PYTHONPATH']]if env.get('PYTHONPATH')else []))
 env.update(CAD_TEST_WORKERS='1',CAD_NATIVE_WORKERS='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 policy_path=root/'orchestrate-cad-drawing-pipeline/assets/test-execution-policy.json'
 policies=json.loads(policy_path.read_text(encoding='utf8')).get('isolated_method_modules',{})if workers>1 and policy_path.is_file()else{}
 for owner,names in list(groups.items()):
  if owner in discovery:continue
  expanded=[]
  for name in sorted(set(names)):
   module_path=root/owner/'scripts'/(name+'.py');key=owner+'/scripts/'+name+'.py';pin=policies.get(key)
   if not pin or not module_path.is_file()or hashlib.sha256(module_path.read_bytes()).hexdigest()!=pin:
    expanded.append(name);continue
   try:
    found=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('discover_isolated_test_cases.py')),name],cwd=root/owner/'scripts',capture_output=True,text=True,encoding='utf8',errors='strict',env=env)
    enumeration=json.loads(found.stdout)if found.returncode==0 else None
   except (UnicodeDecodeError,json.JSONDecodeError):enumeration=None
   if enumeration is None:
    # Changed/unsupported fixture shapes retain their original whole-module run.
    expanded.append(name);continue
   ids=enumeration.get('test_ids',[])
   if enumeration.get('module_sha256')!=pin or not ids or len(ids)!=len(set(ids))or any(not ident.startswith(name+'.')for ident in ids):raise ValueError('qualified test enumeration differs')
   expanded.extend(ids)
  groups[owner]=expanded
 total_files=sum(len(set(names))for owner,names in groups.items()if owner not in discovery)+sum(len(set(names))for names in javascript.values())
 def shards(names):
  names=sorted(set(names))
  if workers==1:return [names] if names else []
  # Divide the global slots across owners instead of creating 44 chunks for
  # every owner. Re-importing CAD/numerical libraries dominated tiny shards.
  count=min(len(names),max(1,math.ceil(workers*len(names)/max(1,total_files))))
  return [names[i::count]for i in range(count)]
 for owner,names in sorted(groups.items()):
  if owner not in discovery:
   for chunk in shards(names):commands.append((owner,[sys.executable,'-m','unittest',*chunk]))
 node=shutil.which('node')
 for owner,names in sorted(javascript.items()):
  for chunk in shards(names):commands.append((owner,[node or 'node','--test','--test-concurrency=1',*chunk]))
 def execute(item):
  owner,cmd=item;started=time.monotonic()
  try:
   run=subprocess.run(cmd,cwd=root/owner/'scripts',capture_output=True,text=True,encoding='utf-8',errors='strict',env=env)
   return {'skill':owner,'command':cmd,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'elapsed_seconds':time.monotonic()-started}
  except FileNotFoundError as exc:return {'skill':owner,'command':cmd,'exit_code':127,'stdout':'','stderr':str(exc)}
  except UnicodeDecodeError as exc:return {'skill':owner,'command':cmd,'exit_code':1,'stdout':'','stderr':'Test output is not valid UTF-8: '+str(exc)}
 if not commands:return []
 if workers==1:return [execute(item)for item in commands]
 from concurrent.futures import ThreadPoolExecutor
 # Threads only wait on isolated test subprocesses. Geometry owners and their
 # historical Python module namespaces never share these coordinator threads.
 with ThreadPoolExecutor(max_workers=min(workers,len(commands)))as pool:return list(pool.map(execute,commands))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--changed',action='append',required=True);p.add_argument('--run',action='store_true');p.add_argument('--workers',type=int);p.add_argument('--output',type=Path);a=p.parse_args()
 data,features=load_registry();result=impact(features,a.changed)
 result.update(registry_sha256=hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),registry_status=data['status'],status='planned_not_acceptance')
 if a.run:
  result['executions']=run_selected(result,workers=a.workers)
  result['status']='unit_tests_failed' if any(r['exit_code'] for r in result['executions']) else 'unit_tests_passed_full_rebuild_and_review_pending'
 if a.output:
  with a.output.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
  print('UTF-8 report:',a.output)
 else:print(json.dumps(result,ensure_ascii=True,indent=2))
 return 1 if result['status']=='unit_tests_failed' else 0
if __name__=='__main__':sys.exit(main())
