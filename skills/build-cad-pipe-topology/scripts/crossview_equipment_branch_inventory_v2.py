"""Extend the inherited inventory with replayed exploded endpoint evidence.

The original inventory remains immutable and independently replayable. This
entry adds source readers, not connections, equipment owners or physical values.
"""
import argparse,copy,csv,json
from pathlib import Path
import crossview_equipment_branch_inventory as inherited
from confirm_crossview_paths import load,sha,encode
from native_exploded_endpoint_evidence import collect
from source_readability import read_source

MODE='source_endpoint_branch_inventory_v2'
UNSUPPORTED='axis endpoint needs supported native joint-chain evidence'
DEPENDENCIES=('crossview_equipment_branch_inventory.py','native_exploded_endpoint_evidence.py',
    'native_exploded_device_joint_evidence.py','native_nested_joint_evidence.py',
    'repair_upstream_joint_systems.py','classify_device_anchor_spans.py')


def extend(result,evidence):
    """Compose an already replayed base with independently replayed endpoints."""
    if (result.get('status')!='source_comparison_inventory_not_mapping'
        or result.get('local_graphs_mutated') is not False or result.get('mapped_paths')!=0
        or result.get('human_accepted') is not False or result.get('hil_ready') is not False):
        raise ValueError('unsupported inherited inventory state')
    if (evidence.get('status')!='native_exploded_endpoint_chains_replayed_not_physical_ports'
        or evidence.get('graph_mutated') is not False or evidence.get('component_owners_changed') is not False
        or evidence.get('hil_ready') is not False or evidence.get('human_accepted') is not False):
        raise ValueError('unsupported endpoint evidence state')
    rows=evidence['records'];by_edge={r['edge_id']:r for r in rows}
    if len(by_edge)!=len(rows):raise ValueError('duplicate endpoint evidence')
    output=copy.deepcopy(result);changes=[]
    for record in output['records']:
        services=record['views'].get('iso',{}).get('services',{})
        for system,service in services.items():
            trace=service.get('trace',{});route=trace.get('edges',[])
            proof=by_edge.get(route[0]) if len(route)==1 else None
            if proof is None:continue
            if (proof['equipment_id']!=record['equipment_id'] or proof['system']!=system
                or proof.get('physical_port_verified') is not False or proof.get('physical_length_mm') is not None
                or proof.get('human_accepted') is not False):raise ValueError('endpoint evidence owner or uncertainty differs')
            if service.get('ready_for_mapping_comparison'):
                # An additive reader never replaces an existing passed branch.
                continue
            if (trace.get('status')!='unique_graph_service_to_T' or service.get('reason')!=UNSUPPORTED
                or service.get('status')!='source_check_pending'):raise ValueError('endpoint reader cannot bypass a different defect')
            if service.get('coverage')!=proof['coverage'] or service.get('junction_evidence')!=proof['upstream_junction_evidence']:
                raise ValueError('endpoint coverage or source T differs from inherited check')
            updated=dict(service)
            updated.pop('reason')
            updated.update(status='native_branch_checks_passed_comparison_pending',ready_for_mapping_comparison=True,
                endpoint_joint_evidence=proof,logical_ownership_basis='existing_logical_owner_with_replayed_native_exploded_chain',
                physical_ports_verified=False)
            services[system]=updated
            changes.append(dict(equipment_id=record['equipment_id'],system=system,edge_id=proof['edge_id'],
                previous_reason=UNSUPPORTED,new_mapping_confirmed=False))
        record['ready_for_mapping_comparison']=all(record['views'].get(view,{}).get('services',{}).get(system,{}).get('ready_for_mapping_comparison',False)
            for view in ('plan','iso') for system in ('supply','return'))
    before={r['equipment_id']:r for r in result['records']}
    for record in output['records']:
        if before[record['equipment_id']]['ready_for_mapping_comparison'] and record!=before[record['equipment_id']]:
            raise ValueError('previously ready equipment evidence changed')
    output.update(inventory_mode=MODE,exploded_endpoint_source_evidence=evidence,endpoint_reader_changes=changes)
    output['counts']=dict(equipment=len(output['records']),ready_for_mapping_comparison=sum(r['ready_for_mapping_comparison'] for r in output['records']))
    output['source_evidence_implementation_sha256'].update({name:sha(Path(__file__).with_name(name)) for name in DEPENDENCIES})
    return output


def build(paths,policy):
    if sha(paths['endpoint_policy'])!=policy.get('endpoint_policy_sha256'):raise ValueError('stale endpoint policy')
    result=inherited.build(paths,policy)
    doc,preflight=read_source(paths['iso_source'])
    with Path(paths['iso_devices']).open(encoding='utf-8-sig',newline='') as stream:inventory=list(csv.DictReader(stream))
    hashes=dict(source_sha256=sha(paths['iso_source']),graph_sha256=sha(paths['iso_graph']),inventory_sha256=sha(paths['iso_devices']))
    evidence=collect(doc,load(paths['iso_graph']),inventory,load(paths['endpoint_policy']),hashes)
    evidence.update(policy_sha256=sha(paths['endpoint_policy']),source_preflight=preflight,
        implementation_sha256=sha(Path(__file__).with_name('native_exploded_endpoint_evidence.py')))
    return extend(result,evidence)


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'inventory-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=sha(__file__):raise ValueError('stale or unsupported inventory v2 entry')
    for key,item in receipt['inputs'].items():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale inventory v2 input '+key)
    paths={k:v['path'] for k,v in receipt['inputs'].items() if k!='policy'}
    result=build(paths,load(receipt['inputs']['policy']['path']))
    if encode(result)!=(directory/'inventory.json').read_bytes() or sha(directory/'inventory.json')!=receipt['output_sha256']:
        raise ValueError('native inventory v2 replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('plan-source','iso-source','plan-graph','iso-graph','iso-devices','endpoint-policy','policy','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();paths={k:getattr(args,k) for k in ('plan_source','iso_source','plan_graph','iso_graph','iso_devices','endpoint_policy')}
    if args.output.exists():raise FileExistsError(args.output)
    result=build(paths,load(args.policy));args.output.mkdir(parents=True)
    (args.output/'inventory.json').write_bytes(encode(result));paths['policy']=args.policy
    receipt=dict(mode=MODE,inputs={k:dict(path=str(Path(v).resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=sha(__file__),output_sha256=sha(args.output/'inventory.json'))
    (args.output/'inventory-receipt.json').write_bytes(encode(receipt));print(json.dumps(result['counts']))


if __name__=='__main__':main()
