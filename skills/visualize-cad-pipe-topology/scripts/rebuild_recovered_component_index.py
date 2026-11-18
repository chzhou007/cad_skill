"""Replay complete providers and native component ownership before indexing."""
import argparse,copy,csv,importlib,sys
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    path=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if path not in sys.path:sys.path.insert(0,path)
from confirm_crossview_paths import load,sha,encode
from cohort_member_provider_inventory import verify_output as parent_owner
from rebuild_native_balancing_valves import verify_output as valve_owner
from source_readability import read_source
from anchor_bounded_main_paths import component_profiles
from compound_riser_header_members import profile
from recovered_component_graph_bridge import build,edge_bases,MODE
from build_visualization import normalize_legacy_component_inventory


def affected_profiles(provider,inventory,plan_components,member,member_components,native_axis):
    rows={r['edge_id']:r for r in provider['records']};axis={e['edge_id']:e for e in native_axis['edges']};out=[]
    for added in inventory['added_components']:
        eid=added['edge_id'];observations=rows[eid]['correspondence_observations']
        if not observations:
            out.append(dict(axis_edge_id=eid,source_handle=added['source_top_handle'],status='previous_unmatched_scope_retained',new_correspondence=False));continue
        if len(observations)!=1:raise ValueError('component change requires an explicit competing-provider reconciliation')
        observation=observations[0]
        if observation['grouped_axis_edges']!=[eid]:raise ValueError('changed component requires a native grouped interval profile owner')
        if observation['domain']=='ordinary_local_graph':
            if len(observation['plan_edges'])!=1:raise ValueError('changed component needs its original multi-edge profile owner')
            edge=axis[eid];floor=str(edge.get('floor_start'))
            if rows[eid]['classification']!='horizontal_only'or floor!=str(edge.get('floor_end'))or floor not in plan_components or str(observation.get('floor',floor))!=floor:raise ValueError('ordinary component profile requires its exact horizontal floor source scope')
            expected=component_profiles(plan_components[floor],observation['plan_edges']);actual=component_profiles(inventory['components'],[eid])
        elif observation['domain']=='reconstructed_member_graph':
            matches=[e for g in member['records']for e in g['scoped_graph']['edges']if e['edge_id']in observation['plan_edges']]
            if len(matches)!=1 or matches[0]['candidate_axis_edge']!=eid:raise ValueError('changed member component lacks its independently checked original allocation')
            selected=[r for r in member_components if r['device_name']in matches[0]['component_ids']]
            if {r['device_name']for r in selected}!=set(matches[0]['component_ids']):raise ValueError('member component source population incomplete')
            expected=[dict(profile(selected))];actual=component_profiles(inventory['components'],[eid])
        else:raise ValueError('unsupported changed component correspondence domain')
        if expected!=actual:raise ValueError('native recovered component conflicts with the plan profile '+eid)
        out.append(dict(axis_edge_id=eid,source_handle=added['source_top_handle'],mapping_id=observation['mapping_id'],plan_edges=observation['plan_edges'],domain=observation['domain'],plan_profile=expected,axis_profile=actual,status='current_native_component_profiles_agree',new_correspondence=False,**(dict(plan_floor=floor)if observation['domain']=='ordinary_local_graph'else{})))
    return out


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as stream:return list(csv.DictReader(stream))


def compute(manifest):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=s['sha256']for k,s in inputs.items()):raise ValueError('recovered index input changed')
    checked();provider=parent_owner(paths['parent_provider'].parent)
    if encode(provider)!=paths['parent_provider'].read_bytes()or provider['inputs']['viewer_manifest']!=inputs['parent_viewer_manifest']:raise ValueError('complete current provider parent differs')
    inventory=valve_owner(paths['native_inventory'].parent)
    if encode(inventory)!=paths['native_inventory'].read_bytes()or inventory['inputs']['graph']!=inputs['native_axis_graph']or inventory['inputs']['source']!=inputs['axis_source']:raise ValueError('native valve source/graph differs')
    original=load(paths['parent_viewer_manifest']);context=original['attributeValueContext'];application=context['riser_header_application'];member=load(paths['member_proof'])
    if context['rendered_graph_sha256']!=inputs['parent_rendered_graph']['sha256']or application['inputs']['member_proof']!=inputs['member_proof']or member['inputs']['valve_inventory']!=inputs['native_inventory']or member['inputs']['plan_components']!=inputs['member_plan_components']:raise ValueError('recovered index is outside qualified parent ancestry')
    scopes=manifest.get('ordinary_plans',[dict(graph='ordinary_plan_graph',components='ordinary_plan_components')]);components_by_floor={};edges_by_floor={};adapted_by_floor={}
    for spec in scopes:
        plan=load(paths[spec['graph']]);floors={str(n['floor'])for n in plan['nodes']}
        if len(floors)!=1:raise ValueError('ordinary profile input must identify one local plan floor')
        floor=next(iter(floors))
        if floor in components_by_floor or provider['original_provider_inventory_inputs'].get('plan_graph_'+floor)!=inputs[spec['graph']]:raise ValueError('ordinary profile floor graph differs from complete parent')
        components_by_floor[floor]=read_csv(paths[spec['components']]);edges_by_floor[floor]={e['edge_id']:e for e in plan['edges']};adapted_by_floor[floor]=normalize_legacy_component_inventory(copy.deepcopy(plan),components_by_floor[floor])
    # Source graph and canonical CSV must agree on all selected component IDs;
    # preserve independent parent topology/mapping evidence instead of rematching
    # devices from their component counts.
    native=load(paths['native_axis_graph']);observed=affected_profiles(provider,inventory,components_by_floor,member,read_csv(paths['member_plan_components']),native)
    for r in observed:
        if r.get('domain')=='ordinary_local_graph':
            for eid in r['plan_edges']:
                if eid not in edges_by_floor[r['plan_floor']]or eid not in adapted_by_floor[r['plan_floor']]:raise ValueError('mapped component plan edge lacks exact canonical inventory agreement')
    parent=load(paths['parent_rendered_graph']);doc,preflight=read_source(paths['axis_source'])
    graph,audit=build(parent,native,inventory,doc,load(paths['display_type_policy']),inputs['native_inventory']['sha256'],inputs['parent_rendered_graph']['sha256']);checked()
    proof=dict(mode=MODE,inputs=inputs,audit=audit,affected_component_profiles=observed,protected_edge_bases=edge_bases(parent),source_preflight=preflight,complete_parent_and_native_inventory_replayed=True,pipe_graph_restoration_exact=True,all_old_effective_pipe_attributes_must_be_preserved=True,component_rows_added=len(inventory['added_components']),unresolved_native_components=[r for r in inventory['records']if r['status']!='recovered_unique_native_ports_and_graph_segment'and r['status']!='already_in_inventory'],new_correspondences_assigned=0,physical_parameters_assigned=0,human_accepted=False,whole_goal_complete=False)
    return graph,proof


def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('recovered_component_graph_bridge','cohort_member_provider_inventory','rebuild_native_balancing_valves','source_readability','anchor_bounded_main_paths','compound_riser_header_members','build_visualization','instance_geometry','source_evidence')})


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();graph,proof=compute(load(manifest))
    if code!=implementation_hashes():raise ValueError('recovered index implementation changed')
    output.mkdir(parents=True);g=output/'graph.json';g.write_bytes(encode(graph));proof['rendered_graph_sha256']=sha(g);p=output/'component-index-bridge.json';p.write_bytes(encode(proof));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p),graph_sha256=sha(g))))
    return proof


def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'component-index-bridge.json';g=output/'graph.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']or sha(g)!=rc['graph_sha256']:raise ValueError('recovered index receipt/code changed')
    graph,proof=compute(load(m['path']));proof['rendered_graph_sha256']=sha(g)
    if encode(graph)!=g.read_bytes()or encode(proof)!=p.read_bytes():raise ValueError('recovered index independent native replay differs')
    return proof


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:r=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
        r=produce(a.manifest,a.output)
    print(r['audit']['output_instances'],flush=True)
if __name__=='__main__':main()
