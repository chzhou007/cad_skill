"""Versioned inventory extension for source-checked inherited circle branches.

Replay the complete historical inventory, then independently check only the
declared legacy circle frontiers. Both local graphs and prior ready services
remain unchanged. This is source inventory, not cross-view correspondence.
"""
import argparse,copy,hashlib,sys
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from crossview_equipment_branch_inventory import service_route
from crossview_equipment_branch_inventory_v2 import verify_output as verify_parent
from native_inherited_duplicate_circle_evidence import collect,implementation_hashes as circle_hashes
from source_reviewed_circle_branch_evidence import branch_coverage

MODE='inherited_circle_endpoint_branch_inventory_v3'


def path_evidence(doc,graph,edge,source_hash,graph_hash):
    gaps=edge.get('source_normalized_crossovers',[]);legacy=[i for i,gap in enumerate(gaps) if 'source_gap_id' not in gap and 'source_sha256' not in gap]
    if not legacy:return dict(input_graph_sha256=graph_hash,projection_graph_sha256=None,evidence=branch_coverage(doc,graph,edge,source_hash,graph_hash))
    if not edge.get('source_circle_connection',{}).get('expert_issue'):raise ValueError('legacy crossover needs the selected expert-bound circle contract')
    projected=copy.deepcopy(graph);target=next(e for e in projected['edges'] if e['edge_id']==edge['edge_id']);bindings=[]
    allowed={'source_handles','a','b','crossings','crossing_connectivity','physical_length','relative_elevation'}
    for index in legacy:
        original=gaps[index]
        if set(original)!=allowed or original['physical_length']!='unknown' or original['relative_elevation']!='unknown':raise ValueError('unsupported legacy crossover schema')
        digest=hashlib.sha256(encode(original)).hexdigest();identifier='CURRENT-LEGACY-CROSSOVER:'+edge['edge_id']+':'+str(index)+':'+digest[:12]
        target['source_normalized_crossovers'][index].update(source_gap_id=identifier,source_sha256=source_hash)
        bindings.append(dict(original_gap_index=index,original_gap_sha256=digest,current_projection_gap_id=identifier))
    ph=hashlib.sha256(encode(projected)).hexdigest()
    result=branch_coverage(doc,projected,target,source_hash,ph)
    return dict(input_graph_sha256=graph_hash,projection_graph_sha256=ph,legacy_metadata_projection=bindings,
        projection_scope='current_read_only_schema_projection_not_historical_gap_identity',evidence=result)


def inspect(doc,graph,equipment,system,source_hash,graph_hash,policy):
    trace=service_route(graph,equipment,system)
    if trace['status']!='unique_graph_service_to_T' or len(trace['edges'])!=1:raise ValueError('inherited circle scope needs one current equipment branch to T')
    nodes={n['node_id']:n for n in graph['nodes']};edge=next(e for e in graph['edges'] if e['edge_id']==trace['edges'][0]);node=nodes[equipment]
    owner=edge.get('source_layout_equipment_interface',{});root=graph.get('sourceLayoutEquipmentOwnership',{});snapshot=owner.get('endpoint_snapshot',{})
    if (node.get('node_type') not in ('equipment','physical_equipment') or node.get('floor')!=nodes[trace['tee']].get('floor')
        or owner.get('source_sha256')!=source_hash or owner.get('equipment_id')!=equipment or owner.get('system')!=system
        or owner.get('human_accepted') is not False or owner.get('physical_port_verified') is not False
        or root.get('status')!='native_calibrated_logical_ownership_source_checked' or root.get('records',[]).count(owner)!=1
        or snapshot.get('start_node_id')!=edge['start_node_id'] or snapshot.get('end_node_id')!=edge['end_node_id']
        or snapshot.get('system')!=system or snapshot.get('attribute_paths')!=edge.get('attribute_paths')
        or edge.get('equipment_connector_length_mm') is not None):raise ValueError('inherited branch calibrated owner or unknown connector differs')
    junction=collect(doc,graph,trace['tee'],source_hash,graph_hash,policy);coverage=path_evidence(doc,graph,edge,source_hash,graph_hash)
    return dict(trace=trace,status='native_branch_checks_passed_comparison_pending',ready_for_mapping_comparison=True,junction_evidence=junction,
        reviewed_circle_path_evidence=coverage,logical_ownership_basis='source_calibrated_native_layout_with_inherited_circle_source_evidence',
        physical_ports_verified=False,whole_physical_length_mm=None)


def extend(doc,graph,parent,policy,source_hash,graph_hash):
    selections=policy.get('selections',[]);keys=[(r['equipment_id'],r['system']) for r in selections]
    if not selections or len(set(keys))!=len(keys):raise ValueError('nonempty unique inherited circle service scope required')
    result=copy.deepcopy(parent);before={r['equipment_id']:r for r in parent['records']};after={r['equipment_id']:r for r in result['records']};proof=[]
    for selected in selections:
        equipment,system=selected['equipment_id'],selected['system'];row=before.get(equipment)
        if not row or system not in ('supply','return'):raise ValueError('selected equipment/service missing')
        previous=row['views'].get('plan',{}).get('services',{}).get(system,{})
        if previous.get('ready_for_mapping_comparison') is not False or previous.get('trace',{}).get('tee')!=selected['node_id']:
            raise ValueError('selected frontier is ready already or its T changed')
        current=inspect(doc,graph,equipment,system,source_hash,graph_hash,policy)
        if current['trace']!=previous.get('trace') or current['trace']['edges']!=[selected['edge_id']]:raise ValueError('inherited current branch route differs')
        after[equipment]['views']['plan']['services'][system]=current
        proof.append(dict(equipment_id=equipment,system=system,node_id=selected['node_id'],edge_id=selected['edge_id'],previous_status=previous.get('status'),source_evidence=current))
    for row in result['records']:
        row['ready_for_mapping_comparison']=all(row['views'].get(v,{}).get('services',{}).get(s,{}).get('ready_for_mapping_comparison',False) for v in ('plan','iso') for s in ('supply','return'))
    result['counts']=dict(parent['counts'],ready_for_mapping_comparison=sum(r['ready_for_mapping_comparison'] for r in result['records']))
    result['status']='source_comparison_inventory_not_mapping'
    result['inherited_circle_branch_extension']=dict(mode=MODE,records=proof,local_graphs_mutated=False,mapped_paths=0,physical_ports_verified=False,human_accepted=False)
    for equipment,row in before.items():
        expected=copy.deepcopy(after[equipment]);expected['ready_for_mapping_comparison']=row['ready_for_mapping_comparison']
        for eid,system in keys:
            if eid==equipment:expected['views']['plan']['services'][system]=row['views']['plan']['services'][system]
        if expected!=row:raise ValueError('unselected inventory evidence changed')
    return result,proof


def compute(paths,policy):
    for key in ('parent_inventory','parent_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('inherited inventory input changed '+key)
    directory=Path(paths['parent_inventory']).resolve().parent
    if Path(paths['parent_inventory']).resolve()!=directory/'inventory.json' or Path(paths['parent_receipt']).resolve()!=directory/'inventory-receipt.json':raise ValueError('noncanonical parent inventory')
    owner=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_replay_session import verify_once
    parent=verify_once(directory,verify_parent);receipt=load(paths['parent_receipt']);inputs=receipt['inputs']
    source=Path(inputs['plan_source']['path']);graph_path=Path(inputs['plan_graph']['path']);graph=load(graph_path);doc,preflight=read_source(source)
    if sha(source)!=policy['plan_source_sha256'] or sha(graph_path)!=policy['plan_graph_sha256']:raise ValueError('inherited inventory source or local plan changed')
    result,proof=extend(doc,graph,parent,policy,sha(source),sha(graph_path))
    return result,dict(records=proof,source_preflight=preflight,prior_inventory_sha256=sha(paths['parent_inventory']),
        local_plan_graph_sha256=sha(graph_path),local_axis_graph_sha256=inputs['iso_graph']['sha256'],
        prior_ready_equipment=parent['counts']['ready_for_mapping_comparison'],current_ready_equipment=result['counts']['ready_for_mapping_comparison'],
        local_graphs_mutated=False,mapped_paths=0,physical_values_assigned=0,physical_ports_verified=False)


def implementation_hashes():
    result=circle_hashes()
    for name in (Path(__file__).name,'crossview_equipment_branch_inventory.py','crossview_equipment_branch_inventory_v2.py','source_reviewed_circle_branch_evidence.py','reconstruct_native_block_branches.py','correct_plan_crossover_lengths.py','source_readability.py'):
        result[name]=sha(Path(__file__).with_name(name))
    result['native_replay_session.py']=sha(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts/native_replay_session.py')
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'inventory-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('inherited branch inventory implementation changed')
    for value in receipt['inputs'].values():
        if sha(value['path'])!=value['sha256']:raise ValueError('inherited branch inventory dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result,proof=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'inventory.json').read_bytes() or sha(directory/'inventory.json')!=receipt['output_sha256'] or any(receipt.get(k)!=v for k,v in proof.items()):
        raise ValueError('inherited branch inventory native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('parent-inventory','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(parent_inventory=a.parent_inventory/'inventory.json',parent_receipt=a.parent_inventory/'inventory-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result,proof=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'inventory.json';target.write_bytes(encode(result))
    receipt=dict(proof,mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)
    (a.output/'inventory-receipt.json').write_bytes(encode(receipt));print(dict(scoped_services=len(proof['records']),ready_equipment=result['counts']['ready_for_mapping_comparison'],mapped_paths=0),flush=True)


if __name__=='__main__':main()
