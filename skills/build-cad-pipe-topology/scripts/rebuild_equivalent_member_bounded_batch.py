"""Batch native bounded main correspondence through complete member cohorts."""
import argparse,copy,csv,importlib,json,subprocess,sys,tempfile
from pathlib import Path
_root=Path(__file__).resolve().parents[2]
for n in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=str(_root/n/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_current_junction_reader import make_reader
from native_plan_projection_lengths import unit_evidence
from native_main_interval_metrics import measure
from equivalent_member_source_support import MODE as KERNEL_MODE,qualify_cohort,bounded_apply,ObservationDocument
MODE='native_complete_cohort_equivalent_member_bounded_batch_v1'

def checked_parent(manifest,announce):
    """Recheck the complete original parent with its immutable exact runtime.

    A child process avoids mixing new adapters with frozen parent imports. Its
    original content-checked cache validates the complete dependency closure;
    a miss executes the original native owner. A receipt alone is never enough.
    """
    spec=manifest['parent_replay'];source=manifest['inputs']['parent_inventory'];script=_root/'orchestrate-cad-drawing-pipeline/scripts/reuse_riser_provider_artifact.py'
    announce('Checking complete original provider inventory and transitive source dependencies')
    with tempfile.TemporaryDirectory(prefix='cad-equivalent-member-parent-')as tmp:
        output=Path(tmp)/'checked'
        command=[sys.executable,'-X','utf8','-B',str(script),'--skills-root',spec['skills_root'],'--native-run',str(Path(source['path']).parent),'--cache-root',spec['cache_root'],'--output',str(output)]
        run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8',cwd=spec['cwd'])
        if run.returncode:raise ValueError('complete original parent check failed: '+run.stderr[-3000:])
        report=load(output/'execution.json');raw=(output/'proof.json').read_bytes()
        if report['owner']!='riser_header_provider_inventory'or report['proof_sha256']!=source['sha256']or raw!=Path(source['path']).read_bytes()or report['native_replay_performed']==report['dependency_checked_reuse']or report.get('source_graphs_mutated')is not False:raise ValueError('complete parent replay or checked reuse differs')
        announce('Complete parent '+('reused after fresh content checks'if report['dependency_checked_reuse']else'natively replayed'))
        return json.loads(raw)

def _prior_inventory(provider,axis,floor):
    by={e['edge_id']:e for e in axis['edges']};prior=[]
    for row in provider['records']:
        for obs in row['correspondence_observations']:
            same=str(obs.get('floor',by[row['edge_id']]['floor_start']))==str(floor)
            prior.append(dict(plan_edges=obs['plan_edges']if same else[],iso_edges=obs.get('grouped_axis_edges',[row['edge_id']])))
    return dict(junction_mapping=copy.deepcopy(provider['ordinary_junction_mappings'][str(floor)]),records=prior)

def metric_state(edge,metric,plan,row):
    """Prove complete T extents separately from visible fragment lengths."""
    projection=metric.get('projection');known=projection.get('value_mm')if projection else None;complete=None;reasons=[]
    if not projection:reasons.append('native_metric_reader_did_not_qualify_source_projection')
    if edge.get('path_length_complete')is False:reasons.append(edge.get('path_length_scope','source_length_explicitly_incomplete'))
    if edge.get('source_flexible_joints'):reasons.append('inline_joint_length_unknown')
    if edge.get('source_normalized_crossovers'):reasons.append('crossing_omission_physical_length_unknown')
    paths=edge['attribute_paths']
    if any(a[-1]!=b[0]for a,b in zip(paths,paths[1:])):reasons.append('discontinuous_source_paths')
    nodes={n['node_id']:n for n in plan['nodes']};ends=[nodes[n]for n in(row['plan_start'],row['plan_end'])];p,q=paths[0][0],paths[-1][-1]
    import math
    if not(any(all(math.dist(v,[n['x'],n['y']])<=.05 for v,n in zip(pair,ends))for pair in((p,q),(q,p)))):reasons.append('source_does_not_cover_both_T_centres')
    if not reasons:complete=known
    return dict(drawn_plan_projection_mm=known,complete_horizontal_centerline_mm=complete,incomplete_reasons=sorted(set(reasons)),installed_length_mm=None,net_pipe_cut_length_mm=None,unknown_length_filled_with_zero=False)

def compute(manifest,announce=lambda message:None):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in inputs.items()):raise ValueError('equivalent member batch input changed')
    checked();provider=checked_parent(manifest,announce)
    if encode(provider)!=paths['parent_inventory'].read_bytes():raise ValueError('complete parent bytes differ')
    graphs={v:load(paths[k])for v,k in [('plan','plan_graph'),('iso','axis_graph')]};docs={};pre={};hashes={}
    for v,s,g in [('plan','plan_source','plan_graph'),('iso','axis_source','axis_graph')]:
        docs[v],pre[v]=read_source(paths[s]);hashes[v]=dict(source_sha256=inputs[s]['sha256'],graph_sha256=inputs[g]['sha256'])
        if graphs[v].get('metadata',{}).get('source_sha256')!=inputs[s]['sha256']:raise ValueError('local graph native source differs')
    if provider['inputs']['viewer_manifest']!=inputs['parent_viewer_manifest']:raise ValueError('new batch is not based on the complete parent viewer')
    bound=load(paths['parent_viewer_manifest'])['attributeValueContext'];application=bound['riser_header_application']
    if bound['source_graph_sha256']!=inputs['raw_axis_graph']['sha256']:raise ValueError('provider raw axis graph differs')
    for k in('axis_source','axis_graph'):
        if application['source_bindings'][k]!=inputs[k]['sha256']:raise ValueError('native axis differs from complete parent')
    if application['source_bindings']['atom_proof']!=inputs['native_atom_origins']['sha256']:raise ValueError('compound origin parent proof differs')
    parent_member=application['inputs']['member_proof']
    if sha(parent_member['path'])!=parent_member['sha256']or load(parent_member['path'])['inputs']['valve_inventory']!=inputs['native_axis_components']:raise ValueError('native component inventory differs from rechecked parent ancestry')
    floor=manifest['floor'];parent=_prior_inventory(provider,graphs['iso'],floor);reader=make_reader(load(paths['current_T_source_config']),hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
    origins=load(paths['native_atom_origins']);origin=origins['floors'][str(floor)];compound={r['source_LINE']for r in origin['corridors']}
    for key,ancestor in [('plan_graph','plan_graph_'+str(floor)),('plan_source','plan_source_'+str(floor))]:
        if origins['inputs'][ancestor]['sha256']!=inputs[key]['sha256']:raise ValueError('compound origin source differs')
    balancing=load(paths['native_axis_components'])
    if balancing['inputs']['graph']['sha256']!=inputs['axis_graph']['sha256']or balancing['inputs']['source']['sha256']!=inputs['axis_source']['sha256']:raise ValueError('native axis component ancestry differs')
    with paths['plan_components'].open(encoding='utf-8-sig',newline='')as stream:pc=list(csv.DictReader(stream))
    cohorts=[qualify_cohort(docs,graphs,parent['junction_mapping'],provider,floor,s['system'],s['source_family'],hashes,reader)for s in manifest['member_cohorts']]
    announce(str(sum(len(c['branches'])for c in cohorts))+' independent native equipment branches qualified')
    result=bounded_apply(docs,graphs,parent,floor,dict(plan=pc,iso=balancing['components']),hashes,manifest['horizontal_directions_degrees'],dict(plan=reader),cohorts,compound)
    units=unit_evidence(docs['plan'],load(paths['unit_policy']));pe={e['edge_id']:e for e in graphs['plan']['edges']};records=[];metrics=[];blocked=[]
    for row in result['records']:
        edge=pe[row['plan_edges'][0]]
        if set(edge.get('source_handles',[]))&compound:blocked.append(dict(mapping=row,reason='compound_carrier_member_requires_its_own_reconstruction'));continue
        group=next(g for g in result['groups']if g['mapping_id']in row['source_group_ids']);cov=group['native']['plan']['path_coverage'];excluded={h for p in cov.get('equivalent_member_observations',[])if p['edge_id']in row['plan_edges']for h in p['excluded_handles']}
        metric=measure(ObservationDocument(docs['plan'],excluded),graphs['plan'],pc,cov,row,units,dict(hashes['plan'],inventory_sha256=inputs['plan_components']['sha256']),load(paths['inline_origin']))
        state=metric_state(edge,metric,graphs['plan'],row);metrics.append(metric);records.append(dict(row,**state,native_metric=metric,source_member_observation_ids=sorted({s['scope_id']for p in cov.get('equivalent_member_observations',[])if p['edge_id']in row['plan_edges']for s in p['equivalent_support']}),nominal_mm=None,DN_status='existing_native_plan_DN_provider_application_pending',axis_values_fused=False,human_accepted=False))
    if len({e for r in records for e in r['iso_edges']})!=len(records):raise ValueError('new native axis intervals have competing writers')
    checked();return dict(mode=MODE,kernel_mode=KERNEL_MODE,inputs=inputs,floor=floor,records=records,native_bounded_batch=result,metric_records=metrics,blocked_member_records=blocked,source_preflight=pre,units=units,source_hashes=hashes,counts=dict(native_cohorts=len(cohorts),native_independent_equipment_branches=sum(len(c['branches'])for c in cohorts),source_checked_groups=len(result['groups']),new_axis_intervals=len(records),new_junctions=len(result['new_junction_mapping']),known_drawn_projections=sum(r['drawn_plan_projection_mm']is not None for r in records),complete_horizontal_lengths=sum(r['complete_horizontal_centerline_mm']is not None for r in records),DN_values_assigned=0),complete_parent_rechecked=True,old_provider_observations_preserved=True,source_graphs_mutated=False,physical_pipe_count_inferred=False,DN_used_for_mapping=False,unknown_length_filled_with_zero=False,viewer_publication_pending=True,human_accepted=False,whole_goal_complete=False)

def implementation_hashes():
    names=('equivalent_member_source_support','native_canonical_main_family_view','anchor_bounded_main_paths','native_current_junction_reader','crossview_equipment_branch_inventory','batch_native_path_coverage','native_path_coverage_audit','native_main_interval_metrics','native_plan_projection_lengths','source_readability','inherited_batch_plan_metrics','reuse_riser_provider_artifact','reuse_verified_native_artifact','checked_bounded_parent_observer_runtime','observed_vertical_DN_workers')
    return dict(entry=sha(__file__),worker_environment_policy=sha(_root/'orchestrate-cad-drawing-pipeline/assets/riser-provider-worker-environment.json'),**{n:sha(importlib.import_module(n).__file__)for n in names})
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest),lambda message:print(message,flush=True))
    if code!=implementation_hashes():raise ValueError('equivalent member implementation changed')
    output.mkdir(parents=True);p=output/'equivalent-member-bounded-batch.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'equivalent-member-bounded-batch.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('equivalent member receipt or code changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('independent equivalent member replay differs')
    return r
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:r=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
        r=produce(a.manifest,a.output)
    print(json.dumps(r['counts'],ensure_ascii=False),flush=True)
if __name__=='__main__':main()
