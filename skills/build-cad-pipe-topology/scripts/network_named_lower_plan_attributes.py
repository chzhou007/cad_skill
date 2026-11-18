"""Reuse native named-domain, through-T DN and mm kernels for mapped prefixes."""
import argparse,copy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from match_network_named_lower_approaches import verify_output as verify_mapping,implementation_hashes as mapping_hashes,MODE as MAPPING_MODE
from named_riser_plan_attributes import named_annotation_domain
from checked_plan_DN_scope_attributes import attribute_checked_scope
from plan_pipe_diameter_scopes import catalog
from crossview_equipment_branch_inventory import index_graph
from source_checked_plan_path_coverage import audit as audit_paths
from native_plan_projection_lengths import unit_evidence,lengths

MODE='network_named_lower_floor_plan_attributes_v1'

def topology_contract(graph,mapping,seeds,source_hash,graph_hash):
    if (mapping.get('mode')!=MAPPING_MODE or mapping.get('source_sha256',{}).get('plan')!=source_hash or mapping.get('graph_sha256',{}).get('plan')!=graph_hash
        or any(mapping.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted','hil_ready'))):raise ValueError('independent named-network mapping required')
    nodes,edges,adj=index_graph(graph);mains=[];excluded=set();junctions={};neighbours=set();services=set()
    if len(mapping['records'])!=2:raise ValueError('two named-network services required')
    for row in mapping['records']:
        eid=row['plan_edges'][0];nid=row['plan_network_T'];rif=row['plan_riser_interface'];edge=edges[eid];role=row['native_T_roles']['plan'];proof=role['native_T']
        if (len(row['plan_edges'])!=1 or row['floor']!=mapping['floor'] or edge['system']!=row['system'] or row['system'] in services
            or {edge['start_node_id'],edge['end_node_id']}!={nid,rif} or len(adj[nid])!=3 or len(adj[rif])!=1
            or any(nodes[n].get('floor')!=mapping['floor'] or nodes[n].get('review_required') is True for n in (nid,rif))
            or eid not in role['through_edges'] or len(role['through_edges'])!=2 or role['off_edge'] in role['through_edges']
            or set(role['through_edges'])|{role['off_edge']}!={e['edge_id'] for e in adj[nid]}
            or proof.get('source_sha256')!=source_hash or proof.get('graph_sha256')!=graph_hash or proof.get('graph_mutated') is not False
            or len(proof.get('junctions',[]))!=1 or proof['junctions'][0]['node_id']!=nid
            or {r['edge_id'] for r in proof['junctions'][0].get('source_rays',[])}!={e['edge_id'] for e in adj[nid]}):raise ValueError('native through approach topology differs')
        peer=next(e for e in role['through_edges'] if e!=eid)
        if edges[peer]['system']!=row['system']:raise ValueError('source main seed changes system')
        neighbours.add(peer);excluded.add(role['off_edge']);mains.append(eid);junctions[nid]=copy.deepcopy(proof);services.add(row['system'])
    if (services!={'supply','return'} or len(set(mains))!=2 or len(seeds)!=2 or {r['edge_id'] for r in seeds}!=neighbours):raise ValueError('both corresponding adjoining mains must supply native DN seeds')
    return dict(main_edges=mains,branches=[],junctions=junctions,verified_taps=sorted(junctions),branch_frontier_edges=sorted(excluded),adjoining_main_edges=sorted(neighbours))

def compute(paths,policy):
    for key in ('mapping','mapping_receipt','metric_policy'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('network plan attribute input changed '+key)
    folder=Path(paths['mapping']).resolve().parent
    if Path(paths['mapping']).name!='mapping.json' or Path(paths['mapping_receipt']).resolve()!=folder/'network-named-lower-mapping-receipt.json':raise ValueError('noncanonical named-network mapping')
    mapping=verify_mapping(folder);receipt=load(paths['mapping_receipt']);main_receipt=load(receipt['inputs']['main_receipt']['path']);inputs=main_receipt['local_inputs']
    sp=Path(inputs['plan_source']['path']);gp=Path(inputs['plan_graph']['path']);sh=sha(sp);gh=sha(gp)
    if sh!=mapping['source_sha256']['plan'] or gh!=mapping['graph_sha256']['plan']:raise ValueError('current plan differs from mapped prefix source')
    graph=load(gp);doc,preflight=read_source(sp);contract=topology_contract(graph,mapping,policy['seeds'],sh,gh)
    # Adapt only the already checked native-name record shape. No old mapping
    # mode, equipment ownership or physical claim is forged by this read view.
    annotation_view=dict(records=[dict(native_names=dict(plan=row['native_plan_name'])) for row in mapping['records']])
    domain=named_annotation_domain(doc,graph,annotation_view,sh,gh);texts,inventory=catalog(doc,graph,contract['main_edges'],sh,gh)
    consumed=set(domain['consumed_text_handles']);texts=[t for t in texts if t['handle'] not in consumed]
    group=dict(group_id='network_named_lower_floor_prefixes',main_edges=contract['main_edges'],branches=[],seeds=policy['seeds'],line_F_frames=[])
    dn=attribute_checked_scope(doc,graph,group,texts,sh,gh,set(inventory['F_text_handles']),junctions=contract['junctions'],verified_taps=contract['verified_taps'],
        branch_frontier_edges=contract['branch_frontier_edges'],path_auditor=audit_paths,verified_nonpipe_annotation_strokes=domain['consumed_stroke_handles'])
    by={r['edge_id']:r for r in dn['records']};metric_policy=load(paths['metric_policy']);units=unit_evidence(doc,metric_policy)
    coverage=audit_paths(doc,graph,dict(source_sha256=sh,graph_sha256=gh,edges=contract['main_edges']),sh,gh);records=[]
    for mapped in mapping['records']:
        eid=mapped['plan_edges'][0];metric=lengths(graph,coverage,mapped,units)
        records.append(dict(mapping_id=mapped['mapping_id'],kind=mapped['kind'],floor=mapped['floor'],system=mapped['system'],identifier=mapped['identifier'],
            plan_edges=mapped['plan_edges'],iso_edges=mapped['iso_edges'],iso_segment_scopes=copy.deepcopy(mapped['iso_segment_scopes']),
            plan_riser_interface=mapped['plan_riser_interface'],plan_network_T=mapped['plan_network_T'],axis_network_T=mapped['axis_network_T'],
            diameter=by[eid],horizontal_projection=metric,whole_axis_DN_selected=False,whole_axis_DN_assigned=False,whole_axis_physical_length_mm=None,
            installed_whole_edge_length_mm=None,physical_port_verified=False,plan_glyph_radius_added_to_length=False,human_accepted=False))
    for key in ('mapping','mapping_receipt','metric_policy'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('network plan attribute dependency changed during replay')
    return dict(mode=MODE,status='source_checked_network_named_lower_plan_DN_XY_not_fused',records=records,mapping_sha256=sha(paths['mapping']),
        source_sha256=mapping['source_sha256'],graph_sha256=mapping['graph_sha256'],source_preflight=preflight,source_annotation_inventory=inventory,
        named_riser_annotation_domain=domain,topology_contract=contract,diameter_scope=dn,unit_evidence=units,path_coverage=coverage,
        known_DN_records=sum(r['diameter']['nominal_mm'] is not None for r in records),unresolved_DN_records=sum(r['diameter']['nominal_mm'] is None for r in records),
        local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,installed_lengths_assigned=0,human_accepted=False,hil_ready=False)

def implementation_hashes():
    result=mapping_hashes()
    for name in (Path(__file__).name,'named_riser_plan_attributes.py','checked_plan_DN_scope_attributes.py','source_checked_plan_path_coverage.py','native_plan_projection_lengths.py','plan_pipe_diameter_scopes.py','diameter_tee_inheritance.py','pipe_annotation_attributes.py','source_direct_dn_evidence.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'network-named-plan-attribute-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('named-network plan attribute implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('named-network plan attribute input changed')
    result=compute({k:r['path'] for k,r in receipt['inputs'].items()},load(receipt['inputs']['policy']['path']))
    if encode(result)!=(directory/'attributes.json').read_bytes() or sha(directory/'attributes.json')!=receipt['output_sha256']:raise ValueError('named-network plan attribute native replay differs')
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ('mapping-run','metric-policy','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();paths=dict(mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'network-named-lower-mapping-receipt.json',metric_policy=a.metric_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    data=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'attributes.json';target.write_bytes(encode(data))
    (a.output/'network-named-plan-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(records=len(data['records']),known_DN=data['known_DN_records'],unresolved=data['unresolved_DN_records']),flush=True)
if __name__=='__main__':main()
