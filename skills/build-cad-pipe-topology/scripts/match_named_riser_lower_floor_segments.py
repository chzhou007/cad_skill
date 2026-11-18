"""Map a named riser's lower-floor prefix and native bridge to a checked device T.

Reuse source naming, full-column, native T/XYZ, branch-inventory and path
coverage owners. No nearest-path matching or vertical attribute propagation.
"""
import argparse,copy,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from match_named_riser_floor_segments import through_role,implementation_hashes as inherited_hashes
from crossview_equipment_branch_inventory import index_graph,service_route
from crossview_equipment_branch_inventory_v2 import verify_output as verify_inventory
from native_axis_riser_DN_scopes import verify_output as verify_riser
from native_named_riser_evidence import collect as collect_names
from native_touching_plan_path_chunks import collect as collect_touching
from native_path_coverage_audit import audit as audit_paths
from native_line_path_evidence import LAYERS,_on

MODE='source_checked_named_lower_floor_segment_paths_v1'


def correspond(docs,graphs,inventory,named,riser,policy,hashes):
    floor=policy['floor'];equipment=policy['equipment_id'];specs=policy['services']
    if isinstance(floor,bool) or not isinstance(floor,int) or len(specs)!=2 or len({s['identifier'] for s in specs})!=2:
        raise ValueError('one explicit lower floor and two named services required')
    owners=[r for r in inventory['records'] if r['equipment_id']==equipment]
    if len(owners)!=1 or owners[0].get('ready_for_mapping_comparison') is not True or owners[0]['floor']!=floor:
        raise ValueError('independent equipment services not source-ready')
    owner=owners[0];indices={v:index_graph(g) for v,g in graphs.items()};records=[];interfaces=[];junctions=[];used=set();plan_ids=[]
    for spec in specs:
        identifier=spec['identifier'];names={v:[r for r in named[v]['records'] if r['identifier']==identifier] for v in graphs}
        if any(len(rows)!=1 for rows in names.values()):raise ValueError('lower-floor source name missing or repeated')
        names={v:rows[0] for v,rows in names.items()};system=names['plan']['system']
        if system in used or system not in LAYERS or names['iso']['system']!=system:raise ValueError('lower-floor services differ')
        used.add(system);pn=names['plan'];rif=pn['target']['node_id']
        if pn['target_kind']!='plan_riser_circle' or pn['target']['floor']!=floor:raise ValueError('named floor RIF differs')
        incident=indices['plan'][2][rif]
        if len(incident)!=1 or incident[0]['system']!=system:raise ValueError('named lower RIF incidence differs')
        approach=incident[0];network=approach['end_node_id'] if approach['start_node_id']==rif else approach['start_node_id']
        target=names['iso']['target'];handles=target.get('source_line_handles',[target.get('source_line_handle')])
        if names['iso']['target_kind'] not in ('axis_source_line','axis_source_corner','axis_source_junction'):raise ValueError('axis name lacks a native pipe target')
        contracts=[c for c in riser['through_contracts'] if c['corridor_id']==identifier and c['system']==system and c['through_source_LINE'] in handles]
        if len(contracts)!=1:raise ValueError('native name does not identify one checked source column')
        contract=contracts[0];mixed=indices['iso'][1][spec['axis_mixed_edge']]
        vertical=[s for s in contract['segments'] if s['side']=='lower' and s['edge_id']==mixed['edge_id'] and s['floor_pair']==[floor,floor+1]]
        if len(vertical)!=1 or mixed['system']!=system or len(mixed['attribute_paths'])!=1:raise ValueError('named lower riser segment missing')
        vertical=vertical[0];si=vertical['segment_index'];points=mixed['attribute_paths'][0]
        if (isinstance(si,bool) or not isinstance(si,int) or si<1 or si!=len(points)-2
            or mixed['end_node_id']!=contract['middle_T'] or points[si:si+2]!=vertical['scope_points']
            or any(abs(a[0]-b[0])<=.05 for a,b in zip(points[:si],points[1:si+1]))):raise ValueError('unsupported lower prefix or another plumb segment')
        source=docs['iso'].entitydb.get(contract['through_source_LINE'])
        if (not source or source not in docs['iso'].modelspace() or source.dxftype()!='LINE' or source.dxf.layer!=LAYERS[system]
            or vertical['source_line_handle']!=source.dxf.handle
            or any(not _on(p,list(source.dxf.start)[:2],list(source.dxf.end)[:2],.05) for p in vertical['scope_points'])):
            raise ValueError('lower column no longer has the named native LINE')
        networks=dict(plan=network,iso=mixed['start_node_id']);traces={v:service_route(graphs[v],equipment,system) for v in graphs};roles={};bridges={}
        for view in graphs:
            graph=graphs[view];nodes,edges,adj=indices[view];net=networks[view];trace=traces[view]
            if trace!=owner['views'][view]['services'][system]['trace'] or trace['status']!='unique_graph_service_to_T' or len(trace['edges'])!=1:
                raise ValueError('independent lower-floor equipment service changed')
            bridge=edges[spec['plan_bridge_edge' if view=='plan' else 'axis_bridge_edge']];target_T=trace['tee'];bridges[view]=bridge
            if (net==target_T or bridge['system']!=system or {bridge['start_node_id'],bridge['end_node_id']}!={net,target_T}
                or any(nodes[n].get('floor')!=floor or nodes[n].get('review_required') is True for n in (net,target_T))):raise ValueError('lower-floor bridge no longer reaches independent equipment T')
            h=hashes[view];a=through_role(docs[view],graph,net,system,h['source_sha256'],h['graph_sha256'])
            b=through_role(docs[view],graph,target_T,system,h['source_sha256'],h['graph_sha256'])
            incoming=approach['edge_id'] if view=='plan' else mixed['edge_id']
            if a['off_edge']!=incoming or bridge['edge_id'] not in a['through_edges'] or b['off_edge']!=trace['edges'][0] or bridge['edge_id'] not in b['through_edges']:
                raise ValueError('lower-floor native branch/through roles disagree')
            roles[view]=dict(network=a,equipment=b)
        private=copy.deepcopy(graphs['iso']);next(e for e in private['edges'] if e['edge_id']==mixed['edge_id'])['attribute_paths']=[copy.deepcopy(points[:si+1])]
        ph=__import__('hashlib').sha256(encode(private)).hexdigest();h=hashes['iso']
        coverage=audit_paths(docs['iso'],private,dict(source_sha256=h['source_sha256'],graph_sha256=ph,edges=[mixed['edge_id'],bridges['iso']['edge_id']]),h['source_sha256'],ph)
        if any(s['status']!='single_source_line_covers' for e in coverage['edges'] for s in e['segments']):raise ValueError('lower prefix or bridge lacks unique native source coverage')
        if len(bridges['iso']['attribute_paths'])!=1:raise ValueError('lower axis bridge needs one native continuous path')
        scopes=[dict(edge_id=mixed['edge_id'],path_index=0,segment_indices=list(range(si)),scope_paths=[copy.deepcopy(points[:si+1])],whole_local_edge=False),
                dict(edge_id=bridges['iso']['edge_id'],path_index=0,segment_indices=list(range(len(bridges['iso']['attribute_paths'][0])-1)),scope_paths=copy.deepcopy(bridges['iso']['attribute_paths']),whole_local_edge=True)]
        common=dict(floor=floor,system=system,identifier=identifier,equipment_id=equipment,plan_riser_interface=rif,
            plan_network_T=network,iso_network_T=networks['iso'],plan_equipment_T=traces['plan']['tee'],iso_equipment_T=traces['iso']['tee'],
            physical_port_verified=False,physical_length_mm=None,human_accepted=False)
        for kind,pe,scope in [('approach',approach,scopes[0]),('network_link',bridges['plan'],scopes[1])]:
            records.append(dict(common,mapping_id=f'RIFL-{floor}-{identifier}-{kind}',kind='named_riser_lower_floor_segment_'+kind,
                plan_edges=[pe['edge_id']],plan_scope_paths=copy.deepcopy(pe['attribute_paths']),iso_edges=[scope['edge_id']],iso_segment_scopes=[scope],
                axis_bend_is_attribute_limit_not_new_physical_node=True,whole_axis_DN_assigned=False,whole_axis_length_assigned=False))
            plan_ids.append(pe['edge_id'])
        interfaces.append(dict(common,axis_bend_point=copy.deepcopy(points[si]),axis_mixed_edge=mixed['edge_id'],retained_vertical_scope=vertical,
            native_names=names,native_roles=roles,axis_coverage=coverage,private_axis_projection_sha256=ph,
            physical_nodes_added=0,graphic_circle_radius_added_to_length=False))
        junctions.extend([dict(system=system,kind=kind,plan_node=networks['plan'] if kind=='network' else traces['plan']['tee'],
            iso_node=networks['iso'] if kind=='network' else traces['iso']['tee']) for kind in ('network','equipment')])
    if used!={'supply','return'} or len(set(plan_ids))!=len(plan_ids):raise ValueError('lower-floor scopes overlap or lack separate services')
    h=hashes['plan'];path_evidence=collect_touching(docs['plan'],graphs['plan'],dict(view_kind='floor_plan',floor=floor,edges=plan_ids,**h),h['source_sha256'],h['graph_sha256'])
    return dict(records=records,floor_interface_correspondences=interfaces,junction_correspondences=junctions,plan_touching_path_evidence=path_evidence,
        local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,DN_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)


def compute(paths,policy):
    for key in ('inventory','inventory_receipt','riser_scope','riser_receipt','plan_name_policy','iso_name_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('lower-prefix mapping input changed '+key)
    invdir=Path(paths['inventory']).resolve().parent;rdir=Path(paths['riser_scope']).resolve().parent
    for key,directory,name in [('inventory',invdir,'inventory.json'),('inventory_receipt',invdir,'inventory-receipt.json'),('riser_scope',rdir,'axis-riser-DN-scopes.json'),('riser_receipt',rdir,'axis-riser-DN-scope-receipt.json')]:
        if Path(paths[key]).resolve()!=directory/name:raise ValueError('noncanonical lower-floor source input')
    inventory=verify_inventory(invdir);riser=verify_riser(rdir);inputs=load(paths['inventory_receipt'])['inputs']
    graphs={v:load(inputs[v+'_graph']['path']) for v in ('plan','iso')};docs={v:read_source(inputs[v+'_source']['path'])[0] for v in graphs}
    hashes={v:dict(source_sha256=sha(inputs[v+'_source']['path']),graph_sha256=sha(inputs[v+'_graph']['path'])) for v in graphs}
    if riser['source_sha256']!=hashes['iso']['source_sha256'] or riser['graph_sha256']!=hashes['iso']['graph_sha256']:raise ValueError('lower-prefix source stages use different axis graphs')
    named={}
    for view in graphs:
        p=load(paths[view+'_name_policy']);selected=policy['native_label_handles'][view]
        if len(selected)!=2 or len(set(selected))!=2:raise ValueError('explicit main-view source names required')
        p['selections']=[r for r in p['selections'] if r['text_handle'] in selected]
        if len(p['selections'])!=2:raise ValueError('lower-floor source labels missing')
        named[view]=collect_names(docs[view],graphs[view],p,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
    result=correspond(docs,graphs,inventory,named,riser,policy,hashes)
    return dict(result,mode=MODE,status='source_checked_named_lower_floor_segment_correspondence_attributes_pending',floor=policy['floor'],
        source_sha256={v:h['source_sha256'] for v,h in hashes.items()},graph_sha256={v:h['graph_sha256'] for v,h in hashes.items()})


def implementation_hashes():
    result=inherited_hashes();result['match_named_riser_lower_floor_segments.py']=sha(__file__);return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'named-lower-segment-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('lower-prefix mapping implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('lower-prefix mapping dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']));target=directory/'mapping.json'
    if encode(result)!=target.read_bytes() or sha(target)!=receipt['output_sha256']:raise ValueError('lower-prefix native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('inventory-run','riser-run','plan-name-policy','iso-name-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(inventory=a.inventory_run/'inventory.json',inventory_receipt=a.inventory_run/'inventory-receipt.json',
        riser_scope=a.riser_run/'axis-riser-DN-scopes.json',riser_receipt=a.riser_run/'axis-riser-DN-scope-receipt.json',plan_name_policy=a.plan_name_policy,iso_name_policy=a.iso_name_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'mapping.json';target.write_bytes(encode(result))
    (a.output/'named-lower-segment-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(dict(mapping_records=4,floor_interfaces=2,physical_values_fused=False),flush=True)


if __name__=='__main__':main()
