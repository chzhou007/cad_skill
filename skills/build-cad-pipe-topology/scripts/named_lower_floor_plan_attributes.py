"""Replay plan DN/XY for checked lower-floor prefix correspondences only."""
import argparse,copy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from match_named_riser_lower_floor_segments import MODE as MAPPING_MODE,verify_output as verify_mapping,implementation_hashes as mapping_hashes
from match_named_riser_floor_segments import through_role
from crossview_equipment_branch_inventory import index_graph
from source_readability import read_source
from named_riser_plan_attributes import named_annotation_domain
from plan_pipe_diameter_scopes import catalog,implementation_hashes as DN_hashes
from checked_plan_DN_scope_attributes import attribute_checked_scope
from touching_plan_path_coverage import audit as audit_paths
from native_touching_plan_path_chunks import measured_scopes

MODE='named_lower_floor_plan_DN_and_XY_scopes_v1'


def attribute(doc,graph,mapping,policy,source_hash,graph_hash):
    if (mapping.get('mode')!=MAPPING_MODE or mapping['source_sha256']['plan']!=source_hash or mapping['graph_sha256']['plan']!=graph_hash
        or any(mapping.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted'))):
        raise ValueError('current native lower-floor mapping required')
    nodes,edges,adj=index_graph(graph);mains=[];branches=[];junctions={}
    for interface in mapping['floor_interface_correspondences']:
        system=interface['system'];network=interface['plan_network_T'];target=interface['plan_equipment_T']
        for nid,role_name in ((network,'network'),(target,'equipment')):
            if nid in junctions or nodes[nid]['floor']!=mapping['floor']:raise ValueError('shared or wrong-floor lower DN T')
            fresh=through_role(doc,graph,nid,system,source_hash,graph_hash)
            if fresh!=interface['native_roles']['plan'][role_name]:raise ValueError('lower-floor native through/branch role changed')
            branch=edges[fresh['off_edge']]
            if branch['system']!=system:raise ValueError('lower DN branch system differs')
            branches.append(dict(edge_id=branch['edge_id'],tee=nid,system=system,role='named_RIF' if role_name=='network' else 'equipment_context'))
            junctions[nid]=fresh['native_T']
        rows=[r for r in mapping['records'] if r['system']==system and r['kind']=='named_riser_lower_floor_segment_network_link']
        if len(rows)!=1 or len(rows[0]['plan_edges'])!=1:raise ValueError('one existing lower plan bridge required per service')
        eid=rows[0]['plan_edges'][0]
        if {edges[eid]['start_node_id'],edges[eid]['end_node_id']}!={network,target}:raise ValueError('lower plan bridge endpoints changed')
        mains.append(eid)
    if len(mains)!=2 or len(branches)!=4 or len({b['edge_id'] for b in branches})!=4:raise ValueError('two lower mains and four independent branches required')
    ids=mains+[b['edge_id'] for b in branches];texts,inventory=catalog(doc,graph,ids,source_hash,graph_hash)
    domain=named_annotation_domain(doc,graph,dict(records=[dict(native_names=i['native_names']) for i in mapping['floor_interface_correspondences']]),source_hash,graph_hash)
    texts=[t for t in texts if t['handle'] not in set(domain['consumed_text_handles'])]
    group=dict(group_id='named_lower_floor_plan_scope',floor=mapping['floor'],main_edges=mains,branches=branches,
        seeds=policy['seeds'],line_F_frames=policy.get('line_F_frames',[]))
    diameter=attribute_checked_scope(doc,graph,group,texts,source_hash,graph_hash,set(inventory['F_text_handles']),
        junctions=junctions,verified_taps=sorted(junctions),path_auditor=audit_paths,verified_nonpipe_annotation_strokes=domain['consumed_stroke_handles'])
    return diameter,dict(topology_contract=dict(main_edges=mains,branches=branches,junctions=junctions,verified_taps=sorted(junctions)),
        named_riser_annotation_domain=domain,source_annotation_inventory=inventory)


def compute(paths,policy):
    for key in ('source','graph','mapping','mapping_receipt','metric_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('lower-floor attribute input changed '+key)
    folder=Path(paths['mapping']).resolve().parent
    if Path(paths['mapping']).resolve()!=folder/'mapping.json' or Path(paths['mapping_receipt']).resolve()!=folder/'named-lower-segment-mapping-receipt.json':
        raise ValueError('noncanonical lower-floor mapping input')
    mapping=verify_mapping(folder);graph=load(paths['graph']);doc,preflight=read_source(paths['source']);sh,gh=sha(paths['source']),sha(paths['graph'])
    diameter,proof=attribute(doc,graph,mapping,policy,sh,gh)
    specs=[dict(scope_id=r['mapping_id'],floor=r['floor'],system=r['system'],plan_edges=r['plan_edges']) for r in mapping['records']]
    ids=[eid for r in specs for eid in r['plan_edges']]
    metric=measured_scopes(doc,graph,dict(view_kind='floor_plan',floor=mapping['floor'],edges=ids,records=specs,source_sha256=sh,graph_sha256=gh),load(paths['metric_policy']),sh,gh)
    dn={r['edge_id']:r for r in diameter['records']};length={r['scope_id']:r for r in metric['measured_scopes']};rows=[]
    for r in mapping['records']:
        if len(r['plan_edges'])!=1:raise ValueError('one normalized lower-floor edge required per mapped scope')
        d=dn[r['plan_edges'][0]]
        if d['nominal_mm'] is None:raise ValueError('lower-floor mapped DN remains conflicted or unknown')
        rows.append(dict(mapping_id=r['mapping_id'],kind=r['kind'],floor=r['floor'],system=r['system'],plan_edges=r['plan_edges'],iso_edges=r['iso_edges'],
            iso_segment_scopes=copy.deepcopy(r['iso_segment_scopes']),diameter=d,horizontal_projection=length[r['mapping_id']]['horizontal_projection'],
            whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,physical_port_verified=False,human_accepted=False))
    mapped={eid for r in rows for eid in r['plan_edges']}
    return dict(mode=MODE,status='source_checked_lower_floor_plan_DN_and_XY_scopes_not_fused',source_sha256=sh,graph_sha256=gh,mapping_sha256=sha(paths['mapping']),
        records=rows,source_preflight=preflight,diameter_scope=diameter,metric_scope=metric,**proof,
        unmapped_equipment_branch_context=[r for r in diameter['records'] if r['edge_id'] not in mapped],local_graphs_mutated=False,
        physical_values_fused=False,physical_ports_verified=False,whole_axis_DN_assigned=0,installed_lengths_assigned=0,human_accepted=False)


def implementation_hashes():
    result=mapping_hashes();result.update(DN_hashes())
    for name in ('named_lower_floor_plan_attributes.py','named_riser_plan_attributes.py','touching_plan_path_coverage.py','checked_plan_DN_scope_attributes.py','source_checked_plan_path_coverage.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'lower-floor-plan-attribute-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('lower-floor attribute implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('lower-floor attribute dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']));target=directory/'lower-floor-plan-attributes.json'
    if encode(result)!=target.read_bytes() or sha(target)!=receipt['output_sha256']:raise ValueError('lower-floor plan attribute native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','mapping-run','metric-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(source=a.source,graph=a.graph,mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'named-lower-segment-mapping-receipt.json',metric_policy=a.metric_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'lower-floor-plan-attributes.json';target.write_bytes(encode(result))
    (a.output/'lower-floor-plan-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(dict(mapped_DN_XY_scopes=len(result['records']),whole_axis_DN_assigned=0,installed_lengths_assigned=0),flush=True)


if __name__=='__main__':main()
