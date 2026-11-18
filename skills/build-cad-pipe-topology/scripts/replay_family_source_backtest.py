"""Run unchanged family entries on explicit native/prepared test lanes."""
import argparse,collections,csv,hashlib,json,os,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from source_readability import read_source
MODE='pinned_native_and_historical_prepared_family_backtest_v1'
ENTRIES={'schematic':'build_schematic.py','profiled_schematic':'rebuild_profiled_schematic.py'}
ROLES={'primary_non_T3','historical_prepared_reference_separate'}
def load(p):return json.loads(Path(p).read_text('utf-8-sig'))
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def encode(d):return(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def check(spec):
 p=Path(spec['path']).resolve()
 if not p.is_file()or sha(p)!=spec['sha256']:raise ValueError('fixed family input changed: '+str(p))
 return p

def validate_manifest(manifest):
 if manifest.get('schema')!=MODE or not manifest.get('cases'):raise ValueError('explicit family backtest lanes required')
 names=set();fixed={}
 for row in manifest['cases']:
  name=row['id']
  if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'for c in name)or name.casefold()in names:raise ValueError('unique simple case identity required')
  names.add(name.casefold())
  if row['entry']not in ENTRIES or row['input_role']not in ROLES:raise ValueError('explicit original entry and source role required')
  source=check(row['inputs']['source'])
  if row['input_role']=='primary_non_T3'and('t3'in source.stem.lower()or source.suffix.lower()!='.dxf'):raise ValueError('native production lane requires non-T3 DXF')
  for k,spec in row['inputs'].items():
   if k not in ('source','config','bindings','profiles','materials'):raise ValueError('unknown family input role')
   path=str(check(spec))
   if path in fixed and fixed[path]!=spec['sha256']:raise ValueError('mixed input versions')
   fixed[path]=spec['sha256']
  if not {'source','config','bindings','profiles'}<=row['inputs'].keys():raise ValueError('complete original family arguments required')
  if row.get('baseline'):
   for name,spec in row['baseline'].items():
    if name not in ('graph','components'):raise ValueError('unknown baseline comparison role')
    path=str(check(spec));fixed[path]=spec['sha256']
 return fixed

def edge_key(e):
 paths=[]
 for path in e['attribute_paths']:
  p=tuple(tuple(q[:2])for q in path);paths.append(min(p,p[::-1]))
 return e['system'],tuple(sorted(e['source_handles'])),tuple(sorted(paths))
def node_key(n):return tuple(sorted(n.get('source_handles',[]))),n['x'],n['y']
def exact_map(before,after,key,field):
 a=collections.defaultdict(list);b=collections.defaultdict(list)
 for row in before:a[key(row)].append(row[field])
 for row in after:b[key(row)].append(row[field])
 if a.keys()!=b.keys()or any(len(a[k])!=1 or len(b[k])!=1 for k in a):raise ValueError('source identities missing or ambiguous; numeric IDs and nearest coordinates cannot substitute')
 return {a[k][0]:b[k][0]for k in a}
def components(path,mapping=None):
 with Path(path).open(encoding='utf-8-sig',newline='')as f:rows=list(csv.DictReader(f))
 return collections.Counter((x['equipment_type'],tuple(sorted(json.loads(x['source_handles']))),mapping[x['edge_id']]if mapping else x['edge_id'])for x in rows)

def compare(baseline,folder):
 old=load(check(baseline['graph']));new=load(folder/'graph_with_edges.json');em=exact_map(old['edges'],new['edges'],edge_key,'edge_id');nm=exact_map(old['nodes'],new['nodes'],node_key,'node_id');by={x['edge_id']:x for x in new['edges']}
 for e in old['edges']:
  other=by[em[e['edge_id']]]
  if {nm[e['start_node_id']],nm[e['end_node_id']]}!={other['start_node_id'],other['end_node_id']}:raise ValueError('native adjacency changed')
  if e.get('path_length')!=other.get('path_length'):raise ValueError('source drawn length changed')
 before={n['node_id']:n for n in old['nodes']};after={n['node_id']:n for n in new['nodes']};diff=[]
 for nid,target in nm.items():
  changes={k:[before[nid].get(k),after[target].get(k)]for k in('node_type','subtype','boundary_type','system')if before[nid].get(k)!=after[target].get(k)}
  if changes:diff.append(dict(old_node=nid,new_node=target,changes=changes))
 result=dict(exact_native_geometry_and_adjacency=True,source_drawn_lengths_exact=True,old_to_new_edges=em,old_to_new_nodes=nm,node_role_differences=diff,numeric_ID_equality_used=False,historical_annotations_transferred=False)
 if 'components'in baseline:
  a=components(check(baseline['components']),em);b=components(folder/'edge_device_instances.csv');result.update(component_ownership_exact=a==b,missing_components=sum((a-b).values()),extra_components=sum((b-a).values()))
 return result

def run(manifest_path,output,workers):
 manifest_path=Path(manifest_path).resolve();output=Path(output).resolve();m=load(manifest_path);fixed=validate_manifest(m)
 if output.exists():raise FileExistsError(output)
 snapshot=check(m['skills_snapshot']);spec=load(snapshot);skills=Path(m['skills_root']).resolve()
 if any(sha(skills/n)!=h for n,h in spec['files'].items()):raise ValueError('frozen skill snapshot changed')
 # Decode every source before starting any geometry experiment.
 readability=[]
 for row in m['cases']:
  doc,preflight=read_source(row['inputs']['source']['path']);readability.append(dict(case=row['id'],input_role=row['input_role'],source_preflight=preflight));del doc
 output.mkdir();(output/'preflight.json').write_bytes(encode(dict(mode=MODE,manifest_sha256=sha(manifest_path),readability=readability,all_top_level_inputs_fixed=True,native_and_prepared_lanes_separate=True)))
 def execute(row):
  folder=output/row['id'];entry=skills/'build-cad-pipe-topology/scripts'/ENTRIES[row['entry']];cmd=[sys.executable,'-X','utf8','-B',str(entry)]
  for name,flag in [('source','dxf'),('bindings','bindings'),('profiles','profiles'),('materials','materials'),('config','config')]:
   if name in row['inputs']:cmd.extend(['--'+flag,row['inputs'][name]['path']])
  cmd.extend(['--output-dir',str(folder),'--no-overwrite']);start=time.monotonic();logs=output/('run-'+row['id']);logs.mkdir()
  with(logs/'stdout.log').open('w',encoding='utf8')as so,(logs/'stderr.log').open('w',encoding='utf8')as se:
   child=subprocess.Popen(cmd,stdout=so,stderr=se,cwd=skills.parent,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg'),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));(logs/'process.json').write_bytes(encode(dict(pid=child.pid,launch_ns=time.time_ns(),command=cmd)));code=child.wait()
  result=dict(case=row['id'],drawing=row['drawing'],input_role=row['input_role'],entry=row['entry'],command=cmd,exit_code=code,elapsed_seconds=time.monotonic()-start,graph_present=(folder/'graph_with_edges.json').exists(),whole_drawing_acceptance=False)
  if code==0 and result['graph_present']:
   graph=load(folder/'graph_with_edges.json');result.update(nodes=len(graph['nodes']),edges=len(graph['edges']),graph_sha256=sha(folder/'graph_with_edges.json'))
   if row.get('baseline'):
    try:
     comparison=compare(row['baseline'],folder);(folder/'comparison.json').write_bytes(encode(comparison));result['baseline_comparison']='exact_native_paths_adjacency_and_lengths';result['node_role_differences']=len(comparison['node_role_differences']);result['component_ownership_exact']=comparison.get('component_ownership_exact')
    except ValueError as exc:result['baseline_comparison']='difference_requires_stage_or_source_analysis';result['comparison_reason']=str(exc)
   else:result['baseline_comparison']='no_same_stage_baseline_declared'
  (logs/'execution-result.json').write_bytes(encode(result));return result
 with ThreadPoolExecutor(max_workers=max(1,min(int(workers),32)))as pool:rows=list(pool.map(execute,m['cases']))
 if any(sha(p)!=h for p,h in fixed.items())or any(sha(skills/n)!=h for n,h in spec['files'].items()):raise ValueError('fixed inputs or skills changed during batch')
 result=dict(mode=MODE,status='all_original_family_entries_executed'if all(r['exit_code']==0 and r['graph_present']for r in rows)else'one_or_more_family_entries_failed',cases=rows,top_level_inputs_after_exact=True,frozen_skills_after_exact=True,baseline_correctness_or_HIL_not_inferred=True,prepared_source_is_not_native_source_proof=True,transitive_raw_input_delivery_closure_not_claimed=True,human_accepted=False,whole_goal_complete=False)
 (output/'backtest-report.json').write_bytes(encode(result));return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=6);a=p.parse_args();r=run(a.manifest,a.output,a.workers);print(json.dumps(dict(status=r['status'],cases=[{k:v for k,v in row.items()if k in('case','exit_code','nodes','edges','baseline_comparison','comparison_reason','component_ownership_exact','node_role_differences')}for row in r['cases']]),ensure_ascii=False),flush=True);return 0 if r['status']=='all_original_family_entries_executed'else 1
if __name__=='__main__':raise SystemExit(main())
