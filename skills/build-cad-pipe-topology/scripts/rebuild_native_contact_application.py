"""Compose conserved owner corrections, old-scope replay and new native paths."""
import argparse,copy,csv,hashlib,importlib,json,subprocess,sys,tempfile
from pathlib import Path
_root=Path(__file__).resolve().parents[2]
for name in ('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=str(_root/name/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
from confirm_crossview_paths import load,sha,encode
from rebuild_native_ball_contact_owners import verify_output as inventory_owner
from source_readability import read_source
from native_current_junction_reader import make_reader
from contact_owner_scope_requalification import requalify
from equivalent_member_source_support import qualify_cohort,bounded_apply,ObservationDocument
from native_plan_projection_lengths import unit_evidence
from native_main_interval_metrics import measure
from rebuild_equivalent_member_bounded_batch import metric_state
from ordered_anchor_branch_paths import qualified_local_DN
from equivalent_member_plan_attributes import apply as attribute_application
from native_contact_rendered_graph import apply as graph_application,restore
from recovered_component_graph_bridge import edge_bases
from build_visualization import normalize_legacy_component_inventory

MODE='native_contact_owner_scope_and_path_attribute_application_v1'

def checked_parent(manifest,announce):
    spec=manifest['inputs']['current_provider'];runtime=manifest['inputs']['published_parent_snapshot'];root=Path(runtime['path']).parent/'skills'
    worker=_root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_contact_parent.py'
    announce('Rechecking the complete original published provider in its fixed runtime')
    with tempfile.TemporaryDirectory(prefix='cad-contact-parent-')as temporary:
        output=Path(temporary)/'checked'
        command=[sys.executable,'-X','utf8','-B',str(worker),'--skills-root',str(root),'--snapshot',runtime['path'],'--native-run',str(Path(spec['path']).parent),'--expected-sha256',spec['sha256'],'--output',str(output)]
        run=subprocess.run(command,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf8')
        if run.returncode:raise ValueError('complete fixed parent failed: '+run.stderr[-5000:])
        raw=(output/'proof.json').read_bytes();execution=load(output/'execution.json')
        if raw!=Path(spec['path']).read_bytes()or execution['proof_sha256']!=spec['sha256']or execution['owner']!='recovered_component_provider_inventory':raise ValueError('fixed complete parent identity differs')
        announce('Complete published parent source and transitive dependencies checked')
        return json.loads(raw)

def compute(manifest,announce=lambda message:None):
    inputs=manifest['inputs'];paths={key:Path(value['path'])for key,value in inputs.items()}
    def checked():
        if any(sha(paths[key])!=value['sha256']for key,value in inputs.items()):raise ValueError('contact application input changed')
        runtime=load(paths['runtime_snapshot'])
        if any(sha(_root/name)!=value for name,value in runtime['files'].items()):raise ValueError('contact application complete runtime changed')
    checked();provider=checked_parent(manifest,announce);inventory=inventory_owner(paths['native_owner_proof'].parent)
    if encode(inventory)!=paths['native_owner_proof'].read_bytes():raise ValueError('native owner inventory replay differs')
    added=load(inventory['inputs']['original_inventory']['path']);legacy=load(added['inputs']['original_inventory']['path'])
    if added['inputs']['original_inventory']!=provider['current_component_inventory']['native_inventory']or added['components'][:len(legacy['components'])]!=legacy['components']:raise ValueError('contact inventory is outside the original rendered component ancestry')
    parent=load(paths['parent_viewer_manifest']);rendered=load(paths['parent_rendered_graph'])
    if provider['inputs']['viewer_manifest']!=inputs['parent_viewer_manifest']or provider['current_component_inventory']['rendered_graph_sha256']!=inputs['parent_rendered_graph']['sha256']or parent['attributeValueContext']['current_rendered_graph_sha256']!=inputs['parent_rendered_graph']['sha256']:raise ValueError('contact application uses another published viewer')
    predecessor=load(provider['inputs']['original_inventory']['path']);batch_parent=load(predecessor['inputs']['batch_proof']['path']);receipt=load(Path(predecessor['inputs']['batch_proof']['path']).parent/'receipt.json')
    if receipt['manifest']!=inputs['source_batch_manifest']:raise ValueError('native source-cohort configuration differs from complete published parent')
    source_manifest=load(paths['source_batch_manifest']);bi=source_manifest['inputs'];floor=manifest['floor'];f=str(floor)
    for item in bi.values():
        if sha(item['path'])!=item['sha256']:raise ValueError('original native source-batch dependency changed')
    if source_manifest['floor']!=floor or any(inventory['inputs'][key]!=bi[other]for key,other in [('source','axis_source'),('graph','axis_graph')])or provider['original_provider_inventory_inputs']['plan_graph_'+f]!=bi['plan_graph']:raise ValueError('contact application source graph/floor differs')
    if predecessor['inputs']['original_inventory']!=batch_parent['inputs']['parent_inventory']:raise ValueError('source batch complete original provider differs')
    graphs={view:load(bi[key]['path'])for view,key in [('plan','plan_graph'),('iso','axis_graph')]};raw=load(bi['raw_axis_graph']['path']);docs={};preflight={}
    for view,key in [('plan','plan_source'),('iso','axis_source')]:docs[view],preflight[view]=read_source(bi[key]['path'])
    hashes={view:dict(source_sha256=bi[source]['sha256'],graph_sha256=bi[graph]['sha256'])for view,source,graph in [('plan','plan_source','plan_graph'),('iso','axis_source','axis_graph')]}
    for view in graphs:
        if graphs[view]['metadata']['source_sha256']!=hashes[view]['source_sha256']:raise ValueError('native local graph/source differs')
    with Path(bi['plan_components']['path']).open(encoding='utf-8-sig',newline='')as handle:pc=list(csv.DictReader(handle))
    normalize_legacy_component_inventory(copy.deepcopy(graphs['plan']),pc)
    reader=make_reader(load(bi['current_T_source_config']['path']),hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
    oldbatch=load(provider['original_provider_inventory_inputs']['batch']['path'])
    scopes=requalify(provider,inventory,docs,graphs,pc,hashes,reader,oldbatch,floor)
    announce(str(scopes['counts']['old_axis_edges'])+' old affected edge scopes requalified with original logical-port or path-profile owners')
    axis={edge['edge_id']:edge for edge in graphs['iso']['edges']};prior=[]
    for row in provider['records']:
        for observation in row['correspondence_observations']:
            same=str(observation.get('floor',axis[row['edge_id']]['floor_start']))==f
            prior.append(dict(plan_edges=observation['plan_edges']if same and observation['domain']=='ordinary_local_graph'else[],iso_edges=observation.get('grouped_axis_edges',[row['edge_id']])))
    previous=dict(junction_mapping=copy.deepcopy(provider['ordinary_junction_mappings'][f]),records=prior)
    cohorts=[qualify_cohort(docs,graphs,previous['junction_mapping'],provider,floor,spec['system'],spec['source_family'],hashes,reader)for spec in source_manifest['member_cohorts']]
    origins=load(bi['native_atom_origins']['path']);compound={row['source_LINE']for row in origins['floors'][f]['corridors']}
    bounded=bounded_apply(docs,graphs,previous,floor,dict(plan=pc,iso=inventory['components']),hashes,source_manifest['horizontal_directions_degrees'],dict(plan=reader),cohorts,compound)
    units=unit_evidence(docs['plan'],load(bi['unit_policy']['path']));pe={edge['edge_id']:edge for edge in graphs['plan']['edges']};records=[]
    for row in bounded['records']:
        if set(pe[row['plan_edges'][0]].get('source_handles',[]))&compound:raise ValueError('new path needs its physical compound-member reconstruction owner')
        group=next(group for group in bounded['groups']if group['mapping_id']in row['source_group_ids']);coverage=group['native']['plan']['path_coverage'];excluded={handle for path in coverage.get('equivalent_member_observations',[])if path['edge_id']in row['plan_edges']for handle in path['excluded_handles']}
        metric=measure(ObservationDocument(docs['plan'],excluded),graphs['plan'],pc,coverage,row,units,dict(hashes['plan'],inventory_sha256=bi['plan_components']['sha256']),load(bi['inline_origin']['path']))
        state=metric_state(pe[row['plan_edges'][0]],metric,graphs['plan'],row);observations=sorted({support['scope_id']for path in coverage.get('equivalent_member_observations',[])if path['edge_id']in row['plan_edges']for support in path['equivalent_support']})
        records.append(dict(row,**state,native_metric=metric,source_member_observation_ids=observations))
    dn=qualified_local_DN(raw,load(paths['DN_result']),paths['DN_receipt'],paths['DN_result'],{f:graphs['plan']},{f:bi['plan_source']['sha256']},{f:bi['plan_graph']['sha256']})[f]
    source_batch=dict(records=records,native_bounded_batch=bounded,complete_parent_rechecked=True,source_graphs_mutated=False,physical_pipe_count_inferred=False,DN_used_for_mapping=False,human_accepted=False,counts=dict(new_axis_intervals=len(records)))
    attributes=attribute_application(source_batch,dn,graphs['plan'],graphs['iso'],raw,rendered,source_manifest['horizontal_directions_degrees'])
    graph,audit=graph_application(rendered,graphs['iso'],inventory,added,docs['iso'],load(paths['display_type_policy']),inputs['native_owner_proof']['sha256'],inputs['parent_rendered_graph']['sha256'])
    checked();proof=dict(mode=MODE,inputs=inputs,source_batch_inputs=bi,floor=floor,source_preflight=preflight,existing_scope_requalification=scopes,source_batch=source_batch,attribute_records=attributes,graph_audit=audit,protected_edge_bases=edge_bases(rendered),rendered_graph_sha256=hashlib.sha256(encode(graph)).hexdigest(),complete_current_parent_replayed=True,native_owner_inventory_replayed=True,all_affected_old_scopes_requalified=True,pipe_graph_restoration_exact=restore(graph,audit)==rendered,all_original_pipe_attributes_must_be_retained=True,counts=dict(reassigned_components=len(inventory['changes']),added_components=len(added['added_components']),output_components=len(graph['instances']),old_affected_edge_scopes=scopes['counts']['old_axis_edges'],new_axis_intervals=len(attributes),new_ordinary_junctions=len(bounded['new_junction_mapping']),new_plan_DN=sum(row['nominal_mm']is not None for row in attributes),new_complete_horizontal_lengths=sum(row['complete_horizontal_centerline_mm']is not None for row in attributes)),units=units,source_graphs_mutated=False,physical_pipe_count_inferred=False,DN_used_for_mapping=False,unknown_physical_parameters_filled=0,related_confirmation_inherited=False,human_accepted=False,whole_goal_complete=False)
    announce('Native conserved component index and '+str(len(attributes))+' source-qualified path attributes computed')
    return proof,graph

def implementation_hashes():
    names=('contact_owner_scope_requalification','native_contact_rendered_graph','rebuild_native_ball_contact_owners','equivalent_member_source_support','native_main_interval_metrics','rebuild_equivalent_member_bounded_batch','ordered_anchor_branch_paths','equivalent_member_plan_attributes','native_current_junction_reader')
    return dict(entry=sha(__file__),fixed_parent_worker=sha(_root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_contact_parent.py'),**{name:sha(importlib.import_module(name).__file__)for name in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    before=implementation_hashes();proof,graph=compute(load(manifest),lambda value:print(value,flush=True))
    if before!=implementation_hashes():raise ValueError('contact application code changed')
    output.mkdir(parents=True);path=output/'native-contact-application.json';path.write_bytes(encode(proof));gp=output/'graph.json';gp.write_bytes(encode(graph))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256=sha(path),graph_sha256=sha(gp))))
    return proof

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');manifest=receipt['manifest'];path=output/'native-contact-application.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(manifest['path'])!=manifest['sha256']or sha(path)!=receipt['output_sha256']or sha(output/'graph.json')!=receipt['graph_sha256']:raise ValueError('contact application receipt or code changed')
    proof,graph=compute(load(manifest['path']))
    if encode(proof)!=path.read_bytes()or encode(graph)!=(output/'graph.json').read_bytes():raise ValueError('native contact application independent replay differs')
    return proof

def main():
    parser=argparse.ArgumentParser()
    for key in ('manifest','output','verify-output'):parser.add_argument('--'+key,type=Path)
    args=parser.parse_args()
    if args.verify_output:proof=verify_output(args.verify_output)
    else:
        if not args.manifest or not args.output:parser.error('fixed manifest and fresh output required')
        proof=produce(args.manifest,args.output)
    print(proof['counts'],flush=True)

if __name__=='__main__':main()
