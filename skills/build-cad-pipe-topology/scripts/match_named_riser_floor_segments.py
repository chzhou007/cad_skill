"""Map an upper-floor riser suffix and one native bridge to a checked device T.

Mixed edges retain their vertical segment. Named source leaders, inherited
display normalization, exact floor-plan chunk coverage and independent device
services jointly establish correspondence; no nearest-path or DN matching.
"""
import argparse,copy,dataclasses,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph,native_tee,service_route
from crossview_equipment_branch_inventory_v2 import verify_output as verify_inventory
from native_axis_riser_DN_scopes import verify_output as verify_riser
from native_touching_plan_path_chunks import verify_output as verify_touching,collect as collect_touching
from native_named_riser_evidence import collect as collect_names
from match_named_riser_floor_paths import vent_normalization
from native_path_coverage_audit import audit as audit_paths
from native_line_path_evidence import LAYERS,_on

MODE='source_checked_named_upper_floor_segment_paths_v1'


def through_role(doc,graph,nid,system,source_hash,graph_hash):
    nodes,edges,adj=index_graph(graph);node=nodes[nid]
    if (node.get('node_type') not in ('tee','physical_junction') or node.get('review_required') is True or len(adj[nid])!=3
        or {e['system'] for e in adj[nid]}!={system}):raise ValueError('unresolved or mixed-system network T')
    proof=native_tee(doc,graph,nid,source_hash,graph_hash);rows=proof.get('junctions',[])
    if len(rows)!=1 or len(rows[0]['source_rays'])!=3:raise ValueError('three native source rays required')
    rays=rows[0]['source_rays'];pairs=[]
    for i,a in enumerate(rays):
        for b in rays[i+1:]:
            if sum(x*y for x,y in zip(a['direction'],b['direction']))<=-math.cos(math.radians(2)):pairs.append((a,b))
    if len(pairs)!=1:raise ValueError('native T lacks one unique opposing through pair')
    chosen=pairs[0];contacts=[]
    for ray in chosen:
        line=doc.entitydb.get(ray.get('source_line_handle'))
        if not line or line not in doc.modelspace() or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[system]:
            raise ValueError('through ray lacks a same-system native LINE')
        a,b=list(line.dxf.start),list(line.dxf.end);p=[node['x'],node['y']]
        if not _on(p,a[:2],b[:2],.05):raise ValueError('native through LINE misses existing T')
        length2=sum((b[i]-a[i])**2 for i in (0,1))
        if length2<=.0025:raise ValueError('degenerate source through LINE')
        fraction=sum((p[i]-a[i])*(b[i]-a[i]) for i in (0,1))/length2
        contacts.append(dict(edge_id=ray['edge_id'],handle=line.dxf.handle,XYZ=[a,b],contact_XYZ=[*p,a[2]+fraction*(b[2]-a[2])],
                             endpoint_contact=min(math.dist(p,a[:2]),math.dist(p,b[:2]))<=.05))
    if math.dist(contacts[0]['contact_XYZ'],contacts[1]['contact_XYZ'])>.05:
        raise ValueError('through source LINE contacts disagree in native XYZ')
    if contacts[0]['handle']!=contacts[1]['handle'] and not all(c['endpoint_contact'] for c in contacts):
        raise ValueError('different through LINEs must meet at existing source endpoints')
    through={r['edge_id'] for r in chosen};off={e['edge_id'] for e in adj[nid]}-through
    if len(off)!=1:raise ValueError('native through pair has no unique third arm')
    return dict(native_T=proof,through_edges=sorted(through),off_edge=next(iter(off)),native_through_contacts=contacts,
                rule='unique_opposing_native_rays_same_LINE_or_coincident_XYZ_LINE_endpoints')


def correspond(docs,graphs,inventory,named,riser,touching,removed,policy,hashes):
    floor=policy['floor'];equipment=policy['equipment_id'];specs=policy['services']
    if isinstance(floor,bool) or not isinstance(floor,int) or len(specs)!=2 or len({s['identifier'] for s in specs})!=2:
        raise ValueError('one explicit floor and two named services required')
    owners=[r for r in inventory['records'] if r['equipment_id']==equipment]
    if len(owners)!=1 or owners[0].get('ready_for_mapping_comparison') is not True or owners[0]['floor']!=floor:
        raise ValueError('independent equipment services not ready in both views')
    owner=owners[0];indices={v:index_graph(g) for v,g in graphs.items()};records=[];interfaces=[];junctions=[];used=set();plan_ids=[]
    if touching.get('local_graph_mutated') is not False or touching.get('physical_connections_added')!=0 or touching.get('human_accepted') is not False:
        raise ValueError('unsupported touching path source scope')
    for spec in specs:
        identifier=spec['identifier'];ns={v:[r for r in named[v]['records'] if r['identifier']==identifier] for v in graphs}
        if any(len(v)!=1 for v in ns.values()):raise ValueError('named source is missing or repeated in selected main views')
        ns={v:rows[0] for v,rows in ns.items()};system=ns['plan']['system']
        if system in used or ns['iso']['system']!=system or system not in LAYERS:raise ValueError('named segment services differ')
        used.add(system);traces={v:service_route(graphs[v],equipment,system) for v in graphs}
        if any(traces[v]!=owner['views'][v]['services'][system]['trace'] or traces[v]['status']!='unique_graph_service_to_T' or len(traces[v]['edges'])!=1 for v in graphs):
            raise ValueError('independent equipment main T changed')
        pn=ns['plan'];rif=pn['target']['node_id']
        if pn['target_kind']!='plan_riser_circle' or pn['target']['floor']!=floor:raise ValueError('named plan interface differs')
        incidence=indices['plan'][2][rif]
        if len(incidence)!=1 or incidence[0]['system']!=system:raise ValueError('named RIF incidence differs')
        approach=incidence[0];plan_network=approach['end_node_id'] if approach['start_node_id']==rif else approach['start_node_id']
        mixed=indices['iso'][1][spec['axis_mixed_edge']];paths=mixed['attribute_paths'];tip=ns['iso']['leader']['target_point']
        matches=[r for r in removed if r.system==system and _on(tip[:2],list(r.vent_port),list(r.junction),.05)]
        if len(matches)!=1:raise ValueError('axis name lacks unique inherited display-leg normalization')
        candidates=[]
        for contract in riser['through_contracts']:
            if contract['system']!=system:continue
            for segment in contract['segments']:
                if (segment['side']=='upper' and segment['edge_id']==mixed['edge_id'] and segment['floor_pair'][1]==floor
                    and math.dist(segment['scope_points'][-1],matches[0].junction)<=.05):candidates.append((contract,segment))
        if len(candidates)!=1 or mixed['system']!=system or len(paths)!=1:raise ValueError('name does not identify one checked upper riser')
        contract,vertical=candidates[0];si=vertical['segment_index'];points=paths[0]
        if (si!=0 or mixed['start_node_id']!=contract['middle_T'] or len(points)<3
            or vertical['scope_points']!=points[:2] or any(abs(a[0]-b[0])<=.05 for a,b in zip(points[1:],points[2:]))):
            raise ValueError('unsupported upper suffix or another plumb segment')
        axis_network=mixed['end_node_id'];networks=dict(plan=plan_network,iso=axis_network)
        bridges=dict(plan=indices['plan'][1][spec['plan_bridge_edge']],iso=indices['iso'][1][spec['axis_bridge_edge']])
        roles={}
        for view in graphs:
            graph=graphs[view];nodes,edges,adj=indices[view];network=networks[view];target=traces[view]['tee'];bridge=bridges[view]
            if (network==target or bridge['system']!=system or {bridge['start_node_id'],bridge['end_node_id']}!={network,target}
                or any(nodes[n].get('floor')!=floor or nodes[n].get('review_required') is True for n in (network,target))):
                raise ValueError('network bridge is not an existing same-floor link to the independent device T')
            h=hashes[view];a=through_role(docs[view],graph,network,system,h['source_sha256'],h['graph_sha256'])
            b=through_role(docs[view],graph,target,system,h['source_sha256'],h['graph_sha256'])
            incoming=approach['edge_id'] if view=='plan' else mixed['edge_id']
            if a['off_edge']!=incoming or bridge['edge_id'] not in a['through_edges'] or b['off_edge']!=traces[view]['edges'][0] or bridge['edge_id'] not in b['through_edges']:
                raise ValueError('native through/branch roles do not corroborate the selected path')
            roles[view]=dict(network=a,equipment=b)
        private=copy.deepcopy(graphs['iso']);next(e for e in private['edges'] if e['edge_id']==mixed['edge_id'])['attribute_paths']=[copy.deepcopy(points[1:])]
        ph=__import__('hashlib').sha256(encode(private)).hexdigest()
        coverage=audit_paths(docs['iso'],private,dict(source_sha256=hashes['iso']['source_sha256'],graph_sha256=ph,edges=[mixed['edge_id'],bridges['iso']['edge_id']]),hashes['iso']['source_sha256'],ph)
        if any(s['status']!='single_source_line_covers' for row in coverage['edges'] for s in row['segments']):raise ValueError('axis suffix or bridge lacks unique native coverage')
        scopes=[dict(edge_id=mixed['edge_id'],path_index=0,segment_indices=list(range(1,len(points)-1)),scope_paths=[copy.deepcopy(points[1:])],whole_local_edge=False),
                dict(edge_id=bridges['iso']['edge_id'],path_index=0,segment_indices=list(range(len(bridges['iso']['attribute_paths'][0])-1)),scope_paths=copy.deepcopy(bridges['iso']['attribute_paths']),whole_local_edge=True)]
        if len(bridges['iso']['attribute_paths'])!=1:raise ValueError('axis bridge needs one continuous native path')
        common=dict(floor=floor,system=system,identifier=identifier,equipment_id=equipment,plan_riser_interface=rif,
            plan_network_T=plan_network,iso_network_T=axis_network,plan_equipment_T=traces['plan']['tee'],iso_equipment_T=traces['iso']['tee'],
            physical_port_verified=False,physical_length_mm=None,human_accepted=False)
        for kind,pe,scope in [('approach',approach,scopes[0]),('network_link',bridges['plan'],scopes[1])]:
            records.append(dict(common,mapping_id=f'RIFS-{floor}-{identifier}-{kind}',kind='named_riser_floor_segment_'+kind,
                plan_edges=[pe['edge_id']],plan_scope_paths=copy.deepcopy(pe['attribute_paths']),iso_edges=[scope['edge_id']],iso_segment_scopes=[scope],
                axis_bend_is_attribute_limit_not_new_physical_node=True,whole_axis_DN_assigned=False,whole_axis_length_assigned=False))
            plan_ids.append(pe['edge_id'])
        interfaces.append(dict(common,axis_bend_point=copy.deepcopy(points[1]),axis_mixed_edge=mixed['edge_id'],retained_vertical_scope=vertical,
            native_names=ns,inherited_display_leg_normalization=dataclasses.asdict(matches[0]),native_roles=roles,axis_coverage=coverage,
            private_axis_projection_sha256=ph,physical_nodes_added=0,graphic_circle_radius_added_to_length=False))
        junctions.extend([dict(system=system,kind=kind,plan_node=networks['plan'] if kind=='network' else traces['plan']['tee'],
            iso_node=networks['iso'] if kind=='network' else traces['iso']['tee']) for kind in ('network','equipment')])
    if used!={'supply','return'} or len(set(plan_ids))!=len(plan_ids):raise ValueError('overlapping or unpaired service scopes')
    cp=dict(view_kind='floor_plan',floor=floor,edges=plan_ids,**hashes['plan'])
    fresh=collect_touching(docs['plan'],graphs['plan'],cp,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
    for key in ('normalizations','coverage','source_sha256','graph_sha256','private_projection_sha256'):
        if touching.get(key)!=fresh[key]:raise ValueError('native touching plan scope differs from selected correspondence')
    return dict(records=records,floor_interface_correspondences=interfaces,junction_correspondences=junctions,
                plan_touching_path_evidence=fresh,local_graphs_mutated=False,physical_values_fused=False,
                physical_ports_verified=False,DN_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)


def compute(paths,policy):
    for key in ('inventory','inventory_receipt','riser_scope','riser_receipt','touching_scope','touching_receipt','plan_name_policy','iso_name_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('named segment input changed '+key)
    invdir=Path(paths['inventory']).resolve().parent;rdir=Path(paths['riser_scope']).resolve().parent;tdir=Path(paths['touching_scope']).resolve().parent
    for key,directory,name in [('inventory',invdir,'inventory.json'),('inventory_receipt',invdir,'inventory-receipt.json'),('riser_scope',rdir,'axis-riser-DN-scopes.json'),('riser_receipt',rdir,'axis-riser-DN-scope-receipt.json'),('touching_scope',tdir,'touching-path-evidence.json'),('touching_receipt',tdir,'touching-path-receipt.json')]:
        if Path(paths[key]).resolve()!=directory/name:raise ValueError('noncanonical named segment evidence input')
    inventory=verify_inventory(invdir);riser=verify_riser(rdir);touching=verify_touching(tdir)
    inputs=load(paths['inventory_receipt'])['inputs'];graphs={v:load(inputs[v+'_graph']['path']) for v in ('plan','iso')};docs={v:read_source(inputs[v+'_source']['path'])[0] for v in graphs}
    hashes={v:dict(source_sha256=sha(inputs[v+'_source']['path']),graph_sha256=sha(inputs[v+'_graph']['path'])) for v in graphs}
    if touching['source_sha256']!=hashes['plan']['source_sha256'] or touching['graph_sha256']!=hashes['plan']['graph_sha256'] or riser['source_sha256']!=hashes['iso']['source_sha256'] or riser['graph_sha256']!=hashes['iso']['graph_sha256']:
        raise ValueError('named segment source stages use different local graphs')
    named={}
    for view in graphs:
        original=load(paths[view+'_name_policy']);selected=policy['native_label_handles'][view]
        if len(selected)!=2 or len(set(selected))!=2:raise ValueError('exact main-view source labels required')
        original['selections']=[s for s in original['selections'] if s['text_handle'] in selected]
        if len(original['selections'])!=2:raise ValueError('main-view named labels missing')
        named[view]=collect_names(docs[view],graphs[view],original,**dict(source_hash=hashes[view]['source_sha256'],graph_hash=hashes[view]['graph_sha256']))
    result=correspond(docs,graphs,inventory,named,riser,touching,vent_normalization(docs['iso']),policy,hashes)
    return dict(result,mode=MODE,status='source_checked_named_upper_floor_segment_correspondence_attributes_pending',floor=policy['floor'],
                source_sha256={v:h['source_sha256'] for v,h in hashes.items()},graph_sha256={v:h['graph_sha256'] for v,h in hashes.items()})


def implementation_hashes():
    from match_named_riser_floor_paths import implementation_hashes as inherited
    from native_touching_plan_path_chunks import implementation_hashes as touching_hashes
    result=inherited();result.update(touching_hashes());result['match_named_riser_floor_segments.py']=sha(__file__);return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'named-segment-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('named segment mapping implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('named segment mapping dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']));target=directory/'mapping.json'
    if encode(result)!=target.read_bytes() or sha(target)!=receipt['output_sha256']:raise ValueError('named segment native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('inventory-run','riser-run','touching-run','plan-name-policy','iso-name-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(inventory=a.inventory_run/'inventory.json',inventory_receipt=a.inventory_run/'inventory-receipt.json',
        riser_scope=a.riser_run/'axis-riser-DN-scopes.json',riser_receipt=a.riser_run/'axis-riser-DN-scope-receipt.json',
        touching_scope=a.touching_run/'touching-path-evidence.json',touching_receipt=a.touching_run/'touching-path-receipt.json',
        plan_name_policy=a.plan_name_policy,iso_name_policy=a.iso_name_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'mapping.json';target.write_bytes(encode(result))
    (a.output/'named-segment-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(dict(mapping_records=len(result['records']),floor_interfaces=len(result['floor_interface_correspondences']),physical_values_fused=False),flush=True)


if __name__=='__main__':main()
