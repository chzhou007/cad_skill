"""Match through-main floor RIFs to named lower-column horizontal prefixes.

The full checked main network replaces a guessed nearest equipment bridge.
This separate mode does not relax the earlier off-branch named-riser reader.
"""
import argparse,copy,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from match_anchored_floor_main_network import verify_output as verify_main,implementation_hashes as main_hashes,MODE as MAIN_MODE
from match_named_riser_floor_paths import verify_output as verify_column,implementation_hashes as column_hashes,MODE as COLUMN_MODE
from native_named_riser_evidence import collect as collect_names
from match_named_riser_floor_segments import through_role
from native_path_coverage_audit import audit
from native_line_path_evidence import _on,LAYERS
from crossview_equipment_branch_inventory import index_graph

MODE='source_checked_network_named_lower_approaches_v1'

def select_structure(graphs,main,named_columns,riser,plan_names,identifiers):
    if (main.get('mode')!=MAIN_MODE or named_columns.get('mode')!=COLUMN_MODE or len(identifiers)!=2 or len(set(identifiers))!=2
        or named_columns['graph_sha256']['iso']!=main['iso_graph_sha256'] or riser['graph_sha256']!=main['iso_graph_sha256']
        or named_columns['source_sha256']['iso']!=main['source_sha256']['iso'] or riser['source_sha256']!=main['source_sha256']['iso']):
        raise ValueError('independently checked network and named column versions required')
    floor=main['floor'];indices={v:index_graph(g) for v,g in graphs.items()};node_map=main['evidence']['structure']['node_mapping'];rows=[];services=set();writers=set()
    for identifier in identifiers:
        names=[r for r in plan_names['records'] if r['identifier']==identifier];columns=[r for r in named_columns['records'] if r['identifier']==identifier]
        if len(names)!=1 or len(columns)!=1:raise ValueError('one native floor RIF and one checked column per identifier required')
        name=names[0];column=columns[0];system=name['system'];rif=name['target'].get('node_id')
        if (system not in LAYERS or system in services or column['system']!=system or column['floor']!=floor+1
            or name['target_kind']!='plan_riser_circle' or name['target']['floor']!=floor):raise ValueError('named floor or separate services differ')
        services.add(system);incident=indices['plan'][2].get(rif,[])
        if len(incident)!=1 or incident[0]['system']!=system:raise ValueError('native RIF path is not unique')
        pe=incident[0];pn=pe['end_node_id'] if pe['start_node_id']==rif else pe['start_node_id'];an=node_map.get(pn)
        if an is None:raise ValueError('RIF network T is outside complete anchored correspondence')
        contracts=[c for c in riser['through_contracts'] if c['corridor_id']==identifier and c['system']==system and c['middle_T']==column['iso_riser_junction']]
        if len(contracts)!=1:raise ValueError('named column core is not unique')
        contract=contracts[0];lower=[s for s in contract['segments'] if s['side']=='lower' and s['floor_pair']==[floor,floor+1]]
        if len(lower)!=1:raise ValueError('one checked lower vertical segment required')
        vertical=lower[0];ae=indices['iso'][1][vertical['edge_id']]
        if ae['start_node_id']!=an or ae['end_node_id']!=contract['middle_T'] or ae['system']!=system or len(ae['attribute_paths'])!=1:
            raise ValueError('named lower column does not reach the already mapped axis T')
        path=ae['attribute_paths'][0];si=vertical['segment_index']
        if (isinstance(si,bool) or not isinstance(si,int) or si<1 or si!=len(path)-2 or path[si:si+2]!=vertical['scope_points']
            or vertical['source_line_handle']!=contract['through_source_LINE']
            or any(abs(a[0]-b[0])<=.05 for a,b in zip(path[:si],path[1:si+1]))):raise ValueError('lower prefix or original vertical boundary differs')
        if (indices['plan'][0][pn].get('floor')!=floor or indices['iso'][0][an].get('floor')!=floor
            or indices['plan'][0][pn].get('review_required') is True or indices['iso'][0][an].get('review_required') is True):raise ValueError('network T floor or local status differs')
        key=(ae['edge_id'],0,tuple(range(si)))
        if key in writers:raise ValueError('named lower prefix writers overlap')
        writers.add(key)
        rows.append(dict(mapping_id=f'NET-RIFL-{floor}-{identifier}',kind='network_anchored_named_lower_floor_approach',floor=floor,system=system,identifier=identifier,
            plan_edges=[pe['edge_id']],iso_edges=[ae['edge_id']],plan_riser_interface=rif,plan_network_T=pn,axis_network_T=an,
            iso_segment_scopes=[dict(edge_id=ae['edge_id'],path_index=0,segment_indices=list(range(si)),scope_paths=[copy.deepcopy(path[:si+1])],whole_local_edge=False)],
            native_plan_name=name,native_named_column_proof=column,retained_vertical_scope=vertical,
            whole_axis_DN_assigned=False,whole_axis_length_assigned=False,physical_port_verified=False,physical_length_mm=None,human_accepted=False))
    if services!={'supply','return'}:raise ValueError('two separate named services required')
    return rows

def check_through_neighbours(row,roles,main):
    pair={}
    for view,eid in (('plan',row['plan_edges'][0]),('iso',row['iso_edges'][0])):
        role=roles[view]
        if eid not in role['through_edges'] or eid==role['off_edge'] or len(role['through_edges'])!=2:raise ValueError('this named-network mode requires a through approach in both views')
        pair[view]=next(e for e in role['through_edges'] if e!=eid)
    matches=[m for m in main['records'] if m['plan_edges']==[pair['plan']] and m['iso_edges']==[pair['iso']] and m['system']==row['system']]
    if len(matches)!=1:raise ValueError('independent adjoining main correspondence differs')
    return matches[0]['mapping_id']

def compute(paths,policy):
    for key in ('main_mapping','main_receipt','column_mapping','column_receipt','plan_name_policy'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('named network input changed '+key)
    md=Path(paths['main_mapping']).resolve().parent;cd=Path(paths['column_mapping']).resolve().parent
    if Path(paths['main_mapping']).name!='mapping.json' or Path(paths['main_receipt']).resolve()!=md/'source-mapping-receipt.json':raise ValueError('noncanonical complete network input')
    if Path(paths['column_mapping']).name!='mapping.json' or Path(paths['column_receipt']).resolve()!=cd/'named-riser-mapping-receipt.json':raise ValueError('noncanonical checked column input')
    main=verify_main(md);column=verify_column(cd);inputs=load(paths['main_receipt'])['local_inputs'];cr=load(paths['column_receipt']);rp=Path(cr['inputs']['riser_scope']['path'])
    if sha(rp)!=cr['inputs']['riser_scope']['sha256']:raise ValueError('replayed column scope changed')
    riser=load(rp);graphs={v:load(inputs[v+'_graph']['path']) for v in ('plan','iso')};docs={};preflight={};hashes={}
    for view in graphs:
        docs[view],preflight[view]=read_source(inputs[view+'_source']['path']);hashes[view]=dict(source_sha256=sha(inputs[view+'_source']['path']),graph_sha256=sha(inputs[view+'_graph']['path']))
        if hashes[view]['source_sha256']!=main['source_sha256'][view] or hashes[view]['graph_sha256']!=main[view+'_graph_sha256']:raise ValueError('named-network local inputs changed')
    origin=load(paths['plan_name_policy']);selected=policy['native_plan_label_handles']
    if len(selected)!=2 or len(set(selected))!=2:raise ValueError('two explicit source labels required')
    scoped=dict(origin,selections=[s for s in origin['selections'] if s['text_handle'] in selected])
    if len(scoped['selections'])!=2:raise ValueError('named floor label absent from native source policy')
    names=collect_names(docs['plan'],graphs['plan'],scoped,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
    rows=select_structure(graphs,main,column,riser,names,policy['identifiers'])
    for row in rows:
        roles={};coverage={}
        for view,nid in (('plan',row['plan_network_T']),('iso',row['axis_network_T'])):
            h=hashes[view];roles[view]=through_role(docs[view],graphs[view],nid,row['system'],h['source_sha256'],h['graph_sha256'])
            graph=graphs[view];eid=row[view+'_edges'][0];gh=h['graph_sha256']
            if view=='iso':
                graph=copy.deepcopy(graph);next(e for e in graph['edges'] if e['edge_id']==eid)['attribute_paths']=copy.deepcopy(row['iso_segment_scopes'][0]['scope_paths']);gh=__import__('hashlib').sha256(encode(graph)).hexdigest()
                source=docs[view].entitydb.get(row['retained_vertical_scope']['source_line_handle'])
                if source is None or source.dxftype()!='LINE' or source.dxf.layer!=LAYERS[row['system']] or not all(_on(p,list(source.dxf.start)[:2],list(source.dxf.end)[:2],.05) for p in row['retained_vertical_scope']['scope_points']):raise ValueError('retained column native LINE differs')
            proof=audit(docs[view],graph,dict(source_sha256=h['source_sha256'],graph_sha256=gh,edges=[eid]),h['source_sha256'],gh)
            if any(s['status']!='single_source_line_covers' for e in proof['edges'] for s in e['segments']):raise ValueError('named lower prefix lacks native LINE coverage')
            coverage[view]=proof
        row['independent_adjoining_main_mapping_id']=check_through_neighbours(row,roles,main);row['native_T_roles']=roles;row['native_path_coverage']=coverage
        row['graphic_circle_radius_added_to_length']=False;row['axis_bend_is_attribute_limit_not_new_physical_node']=True
    for key in ('main_mapping','main_receipt','column_mapping','column_receipt','plan_name_policy'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('named network dependency changed during replay')
    return dict(mode=MODE,status='source_checked_network_named_lower_approaches_attributes_pending',floor=main['floor'],records=rows,source_sha256=main['source_sha256'],
        graph_sha256={v:h['graph_sha256'] for v,h in hashes.items()},source_preflight=preflight,main_mapping_sha256=sha(paths['main_mapping']),named_column_mapping_sha256=sha(paths['column_mapping']),
        local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,DN_values_assigned=0,physical_lengths_assigned=0,human_accepted=False,hil_ready=False)

def implementation_hashes():
    result=main_hashes();result.update(column_hashes())
    for name in (Path(__file__).name,'match_named_riser_floor_segments.py','native_line_path_evidence.py','native_path_coverage_audit.py','native_named_riser_evidence.py','source_readability.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'network-named-lower-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('named-network implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('named-network input changed')
    result=compute({k:r['path'] for k,r in receipt['inputs'].items()},load(receipt['inputs']['policy']['path']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256']:raise ValueError('named-network native replay differs')
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ('main-mapping-run','column-mapping-run','plan-name-policy','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();paths=dict(main_mapping=a.main_mapping_run/'mapping.json',main_receipt=a.main_mapping_run/'source-mapping-receipt.json',column_mapping=a.column_mapping_run/'mapping.json',column_receipt=a.column_mapping_run/'named-riser-mapping-receipt.json',plan_name_policy=a.plan_name_policy,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'mapping.json';target.write_bytes(encode(result))
    (a.output/'network-named-lower-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,implementation_sha256=implementation_hashes(),inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(named_network_approaches=len(result['records']),physical_values_fused=False),flush=True)
if __name__=='__main__':main()
