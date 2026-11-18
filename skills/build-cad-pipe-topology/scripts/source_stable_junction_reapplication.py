"""Reapply native junction readers after a replayed equipment-owner transition.

An old configuration is not rebased by replacing its graph hash. Its original
owner must reconstruct the current graph, the entire local star must be exact,
and both original and current native readers must independently agree.
"""
import argparse,copy,hashlib,importlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require,current_plan_reader
from native_current_junction_reader import make_reader
from source_readability import read_source
from native_replay_session import verify_once

MODE='source_stable_junction_configuration_reapplication_v1'
CONFIG_ERROR='current junction reader needs one exact source/graph configuration'

def value_sha(value):return hashlib.sha256(encode(value)).hexdigest()

def star(graph,nid):
    nodes={n['node_id']:n for n in graph['nodes']}
    require(len(nodes)==len(graph['nodes'])and nid in nodes,'junction node identity is not unique')
    edges=[e for e in graph['edges']if nid in(e.get('start_node_id'),e.get('end_node_id'))]
    require(len(edges)==3 and len({e['edge_id']for e in edges})==3,'exact three-arm junction required')
    node=nodes[nid]
    require(node.get('node_type')in('tee','physical_junction')and node.get('review_required')is not True,'junction semantics need their own source owner')
    require({e['system']for e in edges}=={node.get('system')},'junction systems differ')
    neighbors={e[k]for e in edges for k in('start_node_id','end_node_id')}
    require(neighbors<=nodes.keys(),'junction includes a boundary instead of a proved node')
    return dict(nodes=sorted([nodes[n]for n in neighbors],key=lambda n:n['node_id']),edges=sorted(edges,key=lambda e:e['edge_id']))

def unchanged_star(previous,current,nid):
    require(previous.get('metadata',{}).get('source_sha256')==current.get('metadata',{}).get('source_sha256'),'junction source changed')
    before,after=star(previous,nid),star(current,nid)
    require(before==after,'junction node, neighbor, incidence or source path changed; requalify its own connection')
    return dict(node_id=nid,local_star_sha256=value_sha(after),incident_edges=[e['edge_id']for e in after['edges']],exact_neighbor_and_edge_payloads=True)

def transition(config,source_spec,current_spec,transition_spec):
    """Only a supported, independently replayed native owner may change config."""
    choices=[c for c in config['plans']if c['inputs']['source']==source_spec]
    require(len(choices)==1,'one original source configuration required')
    old=choices[0];require(sha(old['inputs']['graph']['path'])==old['inputs']['graph']['sha256'],'original configuration graph changed')
    require(transition_spec and sha(transition_spec['path'])==transition_spec['sha256'],'pinned native owner transition required')
    audit=load(transition_spec['path']);manifest=load(audit['manifest']['path'])
    require(sha(audit['manifest']['path'])==audit['manifest']['sha256']and audit['mode']=='complete_native_row_order_sideview_ownership_v1','unsupported configuration transition owner')
    require(manifest['inputs']['graph']==old['inputs']['graph']and manifest['inputs']['source']==source_spec,'transition did not start at original configuration')
    require(Path(current_spec['path']).parent==Path(transition_spec['path']).parent and audit['output_graph_sha256']==current_spec['sha256'],'transition did not produce current graph')
    require(manifest['inputs']['devices']==old['inputs']['devices']and sha(manifest['inputs']['devices']['path'])==audit['output_devices_sha256'],'transition changed the source component inventory')
    from rebuild_ordered_sideview_owners import verify_output
    replay=verify_once(Path(transition_spec['path']).parent,verify_output)
    require(replay['output_graph_sha256']==current_spec['sha256'],'native owner replay differs from current graph')
    derived=copy.deepcopy(config);selected=derived['plans'][config['plans'].index(old)];selected['inputs']['graph']=copy.deepcopy(current_spec)
    # This derived configuration remains private to the guarded reader below.
    # The original configuration and its frozen hashes are never overwritten.
    binding=dict(original_graph=old['inputs']['graph'],current_graph=current_spec,native_owner_audit=transition_spec,native_owner_replayed=True,original_configuration_modified=False)
    return old,derived,binding

def prepare(config,source_spec,current_spec,current_graph,transition_spec=None):
    require(sha(source_spec['path'])==source_spec['sha256']and sha(current_spec['path'])==current_spec['sha256'],'junction source/current graph changed')
    require(value_sha(current_graph)==value_sha(load(current_spec['path'])),'reader graph differs from pinned current graph')
    direct=current_plan_reader(config,source_spec['sha256'],current_spec['sha256'])
    exact=[c for c in config['plans']if c['inputs']['source']==source_spec and c['inputs']['graph']==current_spec]
    fallback=[];initial_hash=value_sha(current_graph)
    def reader(doc,graph,nid,sh,gh):
        require(sh==source_spec['sha256']and gh==current_spec['sha256']and value_sha(graph)==initial_hash,'junction reader escaped pinned current graph')
        try:return direct(doc,graph,nid,sh,gh)
        except ValueError as exc:
            if str(exc)!=CONFIG_ERROR or exact:raise
        if not fallback:
            old,derived,binding=transition(config,source_spec,current_spec,transition_spec)
            previous=load(old['inputs']['graph']['path'])
            fallback.append((previous,current_plan_reader(config,sh,old['inputs']['graph']['sha256']),make_reader(derived,sh,gh),binding))
        previous,old_reader,new_reader,binding=fallback[0]
        scope=unchanged_star(previous,graph,nid)
        original=old_reader(doc,previous,nid,sh,binding['original_graph']['sha256'])
        current=new_reader(doc,graph,nid,sh,gh)
        require(original['junctions']==current['junctions'],'native source rays changed across configuration transition')
        require(len(current['junctions'])==1 and len(current['junctions'][0]['source_rays'])==3,'configuration reuse lacks three native source rays')
        return dict(current,configuration_lineage=dict(binding,**scope),native_prior_and_current_rays_equal=True,physical_values_assigned=0,human_accepted=False)
    return reader

def compute(manifest,announce=lambda value:None):
    inputs=manifest['inputs']
    def checked():require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'junction batch input changed')
    checked();config=load(inputs['configuration']['path']);floors={}
    for floor in(1,2,3):
        f=str(floor);source=inputs['plan_source_'+f];gs=inputs['plan_graph_'+f];graph=load(gs['path']);doc,preflight=read_source(source['path'])
        reader=prepare(config,source,gs,graph,inputs.get('transition_'+f));direct=current_plan_reader(config,source['sha256'],gs['sha256']);records=[];held=[]
        nodes=sorted([n for n in graph['nodes']if n.get('node_type')in('tee','physical_junction')],key=lambda n:n['node_id'])
        for node in nodes:
            nid=node['node_id'];prior_error=None
            try:direct(doc,graph,nid,source['sha256'],gs['sha256'])
            except ValueError as exc:prior_error=str(exc)
            try:
                proof=reader(doc,graph,nid,source['sha256'],gs['sha256']);records.append(dict(node_id=nid,previous_error=prior_error,evidence=proof,recovered_configuration=bool(proof.get('configuration_lineage'))))
            except (ValueError,KeyError)as exc:held.append(dict(node_id=nid,previous_error=prior_error,reason=str(exc),incident_edges=sorted(e['edge_id']for e in graph['edges']if nid in(e.get('start_node_id'),e.get('end_node_id'))),include_in_confirmed_mapping=False))
        floors[f]=dict(source_preflight=preflight,records=records,held=held,counts=dict(screened=len(nodes),qualified=len(records),recovered_configuration=sum(r['recovered_configuration']for r in records),held=len(held)))
        announce('Floor '+f+': '+str(floors[f]['counts']))
    checked();return dict(mode=MODE,inputs=inputs,floors=floors,counts={k:sum(v['counts'][k]for v in floors.values())for k in('screened','qualified','recovered_configuration','held')},all_current_plan_Ts_screened=True,original_and_current_native_rays_replayed=True,source_graphs_changed=False,source_configuration_changed=False,DN_values_assigned=0,length_values_assigned=0,mapping_values_assigned=0,human_accepted=False,whole_goal_complete=False)

def implementations():
    names=('native_current_junction_reader','legacy_named_provider_inventory','rebuild_ordered_sideview_owners','ordered_sideview_equipment_owners','current_circle_main_lineage','source_reviewed_circle_branch_evidence','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'choose a fresh junction replay output');before=implementations();proof=compute(load(manifest),lambda v:print(v,flush=True));require(before==implementations(),'junction implementation changed');output.mkdir(parents=True);(output/'source-stable-junctions.json').write_bytes(encode(proof));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256=sha(output/'source-stable-junctions.json'))));return proof

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and sha(output/'source-stable-junctions.json')==receipt['output_sha256'],'junction replay receipt changed');proof=compute(load(receipt['manifest']['path']));require(encode(proof)==(output/'source-stable-junctions.json').read_bytes(),'independent native junction replay differs');return proof

def main():
    parser=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):parser.add_argument('--'+n,type=Path)
    args=parser.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if args.verify_output:r=verify_output(args.verify_output)
        else:
            if not args.manifest or not args.output:parser.error('fixed manifest and fresh output required')
            r=produce(args.manifest,args.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
