"""Rebuild ordered logical ownership after independently replaying plan topology."""
import argparse,hashlib,importlib,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from reconstruct_reviewed_plan_gaps import verify_output as verify_parent
from native_replay_session import verify_once
from ordered_sideview_equipment_owners import collect,apply,MODE
from crossview_equipment_branch_inventory import service_route,native_tee

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('ordered-owner input changed')
    checked()
    if paths['graph'].name!='graph_with_edges.json'or paths['devices']!=paths['graph'].with_name('assigned_edge_device_instances.csv'):raise ValueError('canonical plan graph/inventory required')
    parent=verify_once(paths['graph'].parent,verify_parent)
    if parent['output_graph_sha256']!=sha(paths['graph'])or parent['inputs']['source']['sha256']!=sha(paths['source']):raise ValueError('native local plan parent differs')
    graph=load(paths['graph']);doc,preflight=read_source(paths['source']);evidence=collect(doc,graph,sha(paths['source']),sha(paths['graph']),manifest.get('minimum_controls',3));out,changes=apply(doc,graph,evidence,sha(paths['source']),sha(paths['graph']))
    gh=hashlib.sha256(encode(out)).hexdigest();new={r['equipment_id']for r in changes['records']};services=[];old=[]
    for n in graph['nodes']:
        if n['node_type']!='equipment':continue
        for system in('supply','return'):
            previous=service_route(graph,n['node_id'],system);now=service_route(out,n['node_id'],system)
            if n['node_id']in new:
                if previous['status']!='missing_service'or now['status']!='unique_graph_service_to_T':raise ValueError('new equipment service does not reach its native T')
                proof=native_tee(doc,out,now['tee'],sha(paths['source']),gh);services.append(dict(equipment_id=n['node_id'],system=system,previous=previous,current=now,native_T=proof))
            else:
                if previous!=now:raise ValueError('inherited equipment service changed')
                old.append(dict(equipment_id=n['node_id'],system=system,trace=now))
    checked()
    return out,dict(mode=MODE,evidence=evidence,changes=changes,source_preflight=preflight,parent_native_graph_replayed=True,parent_graph_sha256=sha(paths['graph']),parent_source_sha256=sha(paths['source']),
        counts=dict(native_row_pairs=sum(len(c['pairs'])for c in evidence['cohorts']),independent_owner_pairs=sum(len(c['fixed_owners'])for c in evidence['cohorts']),new_equipment_owners=len(new),new_service_branches=len(services),nodes_before=len(graph['nodes']),nodes_after=len(out['nodes']),edges_before=len(graph['edges']),edges_after=len(out['edges']),
            inherited_service_traces=len(old),inherited_ready_service_traces=sum(r['trace']['status']=='unique_graph_service_to_T'for r in old)),new_services=services,inherited_services=old,
        equipment_instances_conserved=True,inline_inventory_bytes_conserved=True,source_pipe_paths_unchanged=True,physical_lengths_assigned=0,crossview_mapping_recomputed=False,human_accepted=False)

def implementation_hashes():
    names=('ordered_sideview_equipment_owners','canonicalize_confirmed_sideviews','calibrated_equipment_interface_ownership','native_sideview_equipment_branch_evidence','native_line_path_evidence','edge_endpoint_semantics','crossview_equipment_branch_inventory','reconstruct_reviewed_plan_gaps','source_readability','native_replay_session','native_equipment_body','source_terminal_pair_inventory','cad_ceiling_native_rules','native_proxy_evidence')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    spec=load(manifest);graph,result=compute(spec);output.mkdir(parents=True);(output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copy2(spec['inputs']['devices']['path'],output/'assigned_edge_device_instances.csv');(output/'ordered-owner-evidence.json').write_bytes(encode(result))
    (output/'ordered-owner-audit.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementation_hashes(),output_graph_sha256=sha(output/'graph_with_edges.json'),output_evidence_sha256=sha(output/'ordered-owner-evidence.json'),output_devices_sha256=sha(output/'assigned_edge_device_instances.csv'),human_accepted=False)))
    return result

def verify_output(output):
    output=Path(output);a=load(output/'ordered-owner-audit.json');m=a['manifest']
    if a['mode']!=MODE or a['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']:raise ValueError('ordered-owner implementation or manifest changed')
    graph,result=compute(load(m['path']))
    if sha(output/'graph_with_edges.json')!=a['output_graph_sha256']or encode(graph)!=(output/'graph_with_edges.json').read_bytes()or sha(output/'ordered-owner-evidence.json')!=a['output_evidence_sha256']or encode(result)!=(output/'ordered-owner-evidence.json').read_bytes():raise ValueError('ordered-owner native reconstruction differs')
    devices=Path(load(m['path'])['inputs']['devices']['path'])
    if sha(output/'assigned_edge_device_instances.csv')!=a['output_devices_sha256']or devices.read_bytes()!=(output/'assigned_edge_device_instances.csv').read_bytes():raise ValueError('ordered-owner source component inventory changed')
    return dict(a,counts=result['counts'],physical_lengths_assigned=0,crossview_mapping_recomputed=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('pinned manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
