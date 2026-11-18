"""Reapply existing compound-carrier barriers before physical cycle claims."""
import argparse,copy,importlib,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from compound_carrier_members import carrier_risks
from native_replay_session import verify_once
MODE='native_cycle_compound_carrier_guards_v1'

def reconcile(metrics,proposals,risks,plan):
    holds=[];roles=[];unblocked=[]
    index={}
    for corridor in risks['corridors']:
        for row in corridor['edges']:index.setdefault(row['edge_id'],[]).append(corridor)
    for r in metrics['records']:
        barriers=index.get(r['plan_edge_id'],[])
        if not barriers:unblocked.append(r['mapping_id']);continue
        holds.append(dict(axis_edge_id=r['axis_edge_id'],mapping_id=r['mapping_id'],plan_edge_id=r['plan_edge_id'],floor=r['floor'],system=r['system'],
            prior_complete_centerline_mm=r['complete_horizontal_centerline_mm'],drawing_carrier_projection_mm=r['complete_horizontal_centerline_mm'],
            barriers=copy.deepcopy(barriers),status='physical_member_identity_unproved',complete_physical_horizontal_length_mm=None,physical_correspondence_confirmed=False,
            source_annotation_ownership_inferred=False,human_accepted=False))
    for floor,data in proposals['floors'].items():
        for p,a in data.get('new_junction_mapping',{}).items():
            incident={e['edge_id']for e in plan['edges']if p in(e['start_node_id'],e['end_node_id'])}
            barriers=[c for c in risks['corridors']if any(e['edge_id']in incident for e in c['edges'])]
            # A role inside the same unresolved carrier route is a geometric
            # candidate. Unique graphic Ts are not yet physical member Ts.
            if barriers:roles.append(dict(plan_node=p,axis_node=a,floor=int(floor),barriers=copy.deepcopy(barriers),status='typed_riser_role_candidate_member_identity_unproved',physical_identity_confirmed=False))
    if len({r['axis_edge_id']for r in holds})!=len(holds):raise ValueError('duplicate held cycle edge')
    return dict(records=holds,held_riser_role_candidates=roles,unblocked_metric_mapping_ids=unblocked,
        held_cycle_lengths=len(holds),held_riser_roles=len(roles),physical_lengths_assigned=0,physical_member_ids_assigned=0,
        old_graphs_and_source_values_unchanged=True,compound_declaration_candidate_is_not_ownership=True,human_accepted=False)

def compute(manifest):
    from graph_first_provider_inventory import verify_output as verify_inventory
    from rebuild_typed_cycle_riser_batch import verify_output as verify_risers
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('cycle carrier guard input changed')
    checked();parent=verify_once(paths['inventory'].parent,verify_inventory);proposals=verify_once(paths['riser_proposals'].parent,verify_risers)
    if encode(parent)!=paths['inventory'].read_bytes()or encode(proposals)!=paths['riser_proposals'].read_bytes():raise ValueError('original native ancestry differs')
    if proposals['inputs']['inventory']['sha256']!=sha(paths['inventory'])or parent['inputs']['metric_proof']['sha256']!=sha(paths['metric_proof']):raise ValueError('guard uses another provider or metric cohort')
    for k in('plan_graph_2','plan_source_2'):
        if proposals['inputs'][k]['sha256']!=sha(paths[k]):raise ValueError('guard uses another plan/source')
    graph=load(paths['plan_graph_2']);doc,preflight=__import__('source_readability').read_source(paths['plan_source_2'])
    if graph['metadata']['source_sha256']!=sha(paths['plan_source_2']):raise ValueError('plan source hash differs')
    risks=carrier_risks(doc,graph,sha(paths['plan_source_2']));metrics=load(paths['metric_proof']);result=reconcile(metrics,proposals,risks,graph)
    viewer=load(parent['inputs']['viewer_manifest']['path'])
    checked();result.update(mode=MODE,inputs=manifest['inputs'],source_preflight=preflight,native_carrier_risks=risks,
        source_graph_sha256=viewer['attributeValueContext']['source_graph_sha256'],rendered_graph_sha256=viewer['attributeValueContext']['rendered_graph_sha256'],
        current_cycle_context_source_bindings=viewer['attributeValueContext']['graph_first_extensions']['source_bindings'],
        original_provider_and_riser_sources_independently_replayed=True,original_compound_carrier_reader_reused=True,source_qualification_only=True)
    return result
def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('compound_carrier_members','graph_first_provider_inventory','rebuild_typed_cycle_riser_batch','source_readability')})
def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest_path))
    if code!=implementation_hashes():raise ValueError('carrier guard code changed')
    output.mkdir(parents=True);p=output/'cycle-carrier-guards.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=code,output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];p=output/'cycle-carrier-guards.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=receipt['output_sha256']:raise ValueError('carrier guard receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('carrier guard native replay differs')
    return r
def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(dict(held_cycle_lengths=r['held_cycle_lengths'],held_riser_roles=r['held_riser_roles']),flush=True)
if __name__=='__main__':main()
