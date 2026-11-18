"""Replay plan DN inheritance and XY metrics for inherited-circle mappings.

Reuse the existing annotation, through-T, crossover and metric kernels. The
canonical provenance view keeps every original native LINE in its manifest;
it does not establish physical multiplicity or an equipment connector length.
"""
import argparse,copy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph
from match_inherited_circle_crossview_paths import MODE as MAPPING_MODE,verify_output as verify_mapping
from match_source_checked_crossview_paths import selected_snapshot
from native_canonical_main_family_view import project,CanonicalLineDocument
from plan_pipe_diameter_scopes import catalog
from checked_plan_DN_scope_attributes import attribute_checked_scope
from calibrated_direct_dn_evidence import collect as calibrated_collect
from source_direct_dn_evidence import collect as strict_collect
from inherited_circle_branch_inventory import path_evidence
from native_path_coverage_audit import audit as line_audit
from native_plan_projection_lengths import unit_evidence,lengths

MODE='inherited_circle_plan_DN_and_XY_scopes_v1'


def topology_contract(doc,graph,mapping,source_hash,graph_hash):
    if (mapping.get('mode')!=MAPPING_MODE or mapping.get('plan_graph_sha256')!=graph_hash
        or mapping.get('source_sha256',{}).get('plan')!=source_hash or mapping.get('local_graphs_mutated') is not False
        or mapping.get('physical_source_identity_resolved') is not False or mapping.get('physical_values_assigned')!=0
        or mapping.get('human_accepted') is not False):raise ValueError('current inherited-circle correspondence required')
    nodes,edges,adj=index_graph(graph);records=mapping['records'];equipment=mapping['equipment_scope'];floor=mapping['floor']
    if len(equipment)<3 or len(set(equipment))!=len(equipment) or len(records)!=4*len(equipment)-2:raise ValueError('complete paired common-anchor scope required')
    branches=[];junctions={};main_edges=[];projections={};excluded=set();all_ids=[]
    for row in records:
        if (row.get('floor')!=floor or row.get('system') not in ('supply','return') or len(row['plan_edges'])!=1
            or row['plan_snapshot']!=selected_snapshot(graph,row['plan_edges']) or row.get('physical_ports_verified') is not False
            or row.get('human_accepted') is not False):raise ValueError('current scoped path snapshot or physical unknowns changed')
        all_ids.extend(row['plan_edges'])
    if len(all_ids)!=len(set(all_ids)):raise ValueError('overlapping plan attribute writers')
    for system in ('supply','return'):
        services=[r for r in records if r['system']==system and r['kind']=='equipment_branch']
        mains=[r for r in records if r['system']==system and r['kind']=='main_between_equipment_branches']
        if len(services)!=len(equipment) or {r['equipment_id'] for r in services}!=set(equipment) or len(mains)!=len(equipment)-1:
            raise ValueError('both complete services and their main intervals required')
        taps={r['equipment_id']:r['plan_start'] for r in services};anchors={}
        for row in services:
            nid=row['plan_start'];eid=row['plan_edges'][0];node=nodes.get(nid,{});edge=edges[eid];did=row['equipment_id']
            proof=row['local_evidence']['plan']['junction_evidence'];state=row['local_evidence']['plan']
            if (nid in junctions or node.get('floor')!=floor or node.get('review_required') is True or len(adj[nid])!=3
                or nodes.get(did,{}).get('floor')!=floor or edge['system']!=system
                or {edge['start_node_id'],edge['end_node_id']}!={did,nid}
                or state.get('ready_for_mapping_comparison') is not True or state['trace']['edges']!=[eid]
                or state['trace']['tee']!=nid):raise ValueError('source branch, native through T or owner differs')
            branches.append(dict(edge_id=eid,tee=nid,equipment_id=did,system=system));junctions[nid]=proof
            anchors[nid]=dict(evidence=proof,branch_edges=[eid])
        family=mapping['evidence']['native_source_families'][system]['plan']['canonical_source_projection']
        view,corridor,basis=project(doc,graph,taps,system,floor,dict(canonical_source_handle=family['canonical_source_handle'],
            coincident_source_family=family['coincident_source_family']),anchors,source_hash,graph_hash)
        if basis!=mapping['evidence']['native_source_families'][system]['plan']:raise ValueError('native main provenance projection changed')
        expected={r['plan_edges'][0] for r in mains}
        between={e['edge_id'] for e in corridor['edges'] if {e['start_node_id'],e['end_node_id']}<=set(taps.values())}
        if between!=expected:raise ValueError('through-main scope differs from mapped intervals')
        main_edges.extend(sorted(expected));excluded.update(view.excluded);projections[system]=basis
    return CanonicalLineDocument(doc,excluded),dict(main_edges=main_edges,branches=branches,junctions=junctions,
        verified_taps=sorted(junctions),source_main_projections=projections)


def coverage_reader(original,branch_ids,original_hash):
    """Read unchanged branches in the replayed local graph, not a fake repair."""
    original_edges={e['edge_id']:e for e in original['edges']};branch_ids=set(branch_ids)
    def audit(doc,graph,policy,source_hash,graph_hash,tol=.05):
        if (policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or tol!=.05
            or not policy.get('edges') or len(set(policy['edges']))!=len(policy['edges'])):raise ValueError('inherited path scope or hash differs')
        current={e['edge_id']:e for e in graph['edges']};rows=[]
        for eid in policy['edges']:
            if eid not in branch_ids:
                rows.extend(line_audit(doc,graph,dict(policy,edges=[eid]),source_hash,graph_hash,tol)['edges']);continue
            if current[eid]!=original_edges[eid]:raise ValueError('DN projection changed a source-checked equipment branch')
            proof=path_evidence(doc,original,original_edges[eid],source_hash,original_hash)
            evidence=proof['evidence'];segments=[dict(segment,path_index=path['original_path_index']) for path in evidence['paths'] for segment in path['coverage']['segments']]
            rows.append(dict(edge_id=eid,system=current[eid]['system'],segments=segments,
                coverage_mode='native_plan_paths_excluding_replayed_crossovers',source_path_evidence=evidence,
                source_covered_drawing_length=sum(s['drawing_length'] for s in segments),unverified_drawing_length=0,
                original_branch_graph_sha256=original_hash,original_branch_evidence=proof,
                unchanged_branch_in_read_only_DN_projection=True,physical_length='unknown',status='source_geometry_audit_unreviewed'))
        return dict(status='partial_source_coverage_not_physical_length',source_sha256=source_hash,graph_sha256=graph_hash,
            edges=rows,graph_mutated=False,hil_ready=False)
    return audit


def attribute(doc,graph,mapping,policy,calibration,metric_policy,source_hash,graph_hash):
    view,contract=topology_contract(doc,graph,mapping,source_hash,graph_hash)
    ids=contract['main_edges']+[b['edge_id'] for b in contract['branches']]
    texts,inventory=catalog(doc,graph,ids,source_hash,graph_hash)
    seeds=policy['seeds'];allowed={s['text_handle']:s for s in calibration['selections']}
    if not policy.get('expert_T_inheritance_rule') or seeds!=calibration['selections']:raise ValueError('explicit through-T rule and calibrated seed scope required')
    def direct(document,current,selection,sh,gh):
        rows=selection['selections'];observations=[];calibrated=None
        for row in rows:
            if row['text_handle'] in allowed:
                if row!=allowed[row['text_handle']]:raise ValueError('calibrated source seed changed')
                # Parallel service captions can compete with each other. Replay
                # their complete explicitly declared calibration together; do
                # not hide the second caption when requesting one observation.
                if calibrated is None:calibrated=calibrated_collect(document,current,calibration,sh,gh)
                result=dict(observations=[o for o in calibrated['observations'] if o['source_text']['handle']==row['text_handle']])
            else:result=strict_collect(document,current,dict(selection,selections=[row]),sh,gh)
            observations.extend(result['observations'])
        return dict(observations=observations)
    reader=coverage_reader(graph,[b['edge_id'] for b in contract['branches']],graph_hash)
    group=dict(group_id=policy['group_id'],floor=mapping['floor'],main_edges=contract['main_edges'],branches=contract['branches'],
        seeds=seeds,line_F_frames=policy.get('line_F_frames',[]))
    diameter=attribute_checked_scope(view,graph,group,texts,source_hash,graph_hash,set(inventory['F_text_handles']),
        junctions=contract['junctions'],verified_taps=contract['verified_taps'],direct_collector=direct,path_auditor=reader)
    coverage=reader(view,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=ids),source_hash,graph_hash)
    units=unit_evidence(doc,metric_policy);dn={row['edge_id']:row for row in diameter['records']};records=[]
    for row in mapping['records']:
        value=dn[row['plan_edges'][0]]
        if value['nominal_mm'] is None:raise ValueError('mapped plan DN conflict or unknown must return to source comparison')
        records.append(dict(mapping_id=row['mapping_id'],kind=row['kind'],floor=row['floor'],system=row['system'],
            plan_edges=row['plan_edges'],iso_edges=row['iso_edges'],diameter=copy.deepcopy(value),
            horizontal_projection=lengths(graph,coverage,row,units),physical_source_identity_resolved=False,
            whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,physical_ports_verified=False,human_accepted=False))
    return dict(mode=MODE,status='source_checked_inherited_circle_plan_DN_and_XY_not_fused',source_sha256=source_hash,graph_sha256=graph_hash,
        floor=mapping['floor'],equipment_scope=list(mapping['equipment_scope']),physical_ports_verified=False,
        records=records,topology_contract=contract,diameter_scope=diameter,metric_scope=dict(units=units,coverage=coverage),
        source_annotation_inventory=inventory,expert_rule=policy['expert_T_inheritance_rule'],local_graphs_mutated=False,
        physical_values_fused=False,physical_source_identity_resolved=False,whole_axis_DN_assigned=0,installed_lengths_assigned=0,human_accepted=False)


def compute(paths,policy):
    for key in ('source','graph','mapping','mapping_receipt','calibration_policy','metric_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('inherited plan attribute input changed '+key)
    folder=Path(paths['mapping']).resolve().parent
    if Path(paths['mapping']).resolve()!=folder/'mapping.json' or Path(paths['mapping_receipt']).resolve()!=folder/'source-mapping-receipt.json':
        raise ValueError('noncanonical inherited mapping')
    mapping=verify_mapping(folder);source_hash=sha(paths['source']);graph_hash=sha(paths['graph'])
    graph=load(paths['graph']);doc,preflight=read_source(paths['source'])
    result=attribute(doc,graph,mapping,policy,load(paths['calibration_policy']),load(paths['metric_policy']),source_hash,graph_hash)
    result.update(source_preflight=preflight,mapping_sha256=sha(paths['mapping']))
    return result


def implementation_hashes():
    from match_inherited_circle_crossview_paths import implementation_hashes as mapping_hashes
    from plan_calibrated_DN_scopes import implementation_hashes as DN_hashes
    result=mapping_hashes();result.update(DN_hashes())
    for name in (Path(__file__).name,'checked_plan_DN_scope_attributes.py','native_plan_projection_lengths.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'circle-plan-attribute-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('inherited plan attribute implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('inherited plan attribute dependency changed')
    paths={key:item['path'] for key,item in receipt['inputs'].items()};result=compute(paths,load(paths['policy']));target=directory/'circle-plan-attributes.json'
    if encode(result)!=target.read_bytes() or sha(target)!=receipt['output_sha256']:raise ValueError('inherited plan attribute native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','mapping-run','calibration-policy','metric-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(source=a.source,graph=a.graph,mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'source-mapping-receipt.json',
        calibration_policy=a.calibration_policy,metric_policy=a.metric_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'circle-plan-attributes.json';target.write_bytes(encode(result))
    (a.output/'circle-plan-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(dict(mapped_DN_XY_scopes=len(result['records']),installed_lengths_assigned=0,physical_values_fused=False),flush=True)


if __name__=='__main__':main()
