"""Reuse the common-anchor mapping schema on a freshly replayed wave inventory.

The receipt and independent-group batch have distinct versions. Each group
reuses the established logical schema and native kernels without pretending
that an old receipt validates the new local graph.
"""
import argparse,copy,types
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from wave_rebased_branch_inventory import MODE as INVENTORY_MODE,verify_output as verify_inventory
from match_inherited_circle_crossview_paths import MODE as LOGICAL_MODE,correspond
from native_inherited_duplicate_circle_evidence import collect as circle_tee
from crossview_equipment_branch_inventory import native_tee

MODE='source_checked_wave_rebased_inherited_circle_paths_v2'
BATCH_SCHEMA='independent_native_common_anchor_mapping_groups_v1'


def correspond_current(docs,graphs,inventory,circle_policy,policy,hashes):
    """A private dependency namespace keeps both historical T readers intact."""
    def plan_tee(doc,graph,nid,source_hash,graph_hash,ip):
        node=next(n for n in graph['nodes'] if n['node_id']==nid)
        if node.get('expert_confirmed_circle') or node.get('calibrated_duplicate_circle') or nid in ip.get('external_cases',{}):
            return circle_tee(doc,graph,nid,source_hash,graph_hash,ip)
        return native_tee(doc,graph,nid,source_hash,graph_hash)
    namespace=dict(correspond.__globals__);namespace['inherited_tee']=plan_tee
    matcher=types.FunctionType(correspond.__code__,namespace,correspond.__name__)
    return matcher(docs,graphs,inventory,circle_policy,policy,hashes)


def record_key(row):
    return (row['kind'],row['system'],row['floor'],row.get('equipment_id'),tuple(row.get('endpoint_equipment_ids',[])))


def historical_lineage(mapping,previous,old_plan_hash):
    if (previous.get('plan_graph_sha256')!=old_plan_hash or previous.get('iso_graph_sha256')!=mapping['iso_graph_sha256']
        or previous.get('source_sha256')!=mapping['source_sha256'] or set(previous['equipment_scope'])!=set(mapping['equipment_scope'])):
        raise ValueError('previous mapping source/axis scope is not the wave parent')
    old={record_key(r):r for r in previous['records']};current={record_key(r):r for r in mapping['records']}
    if len(old)!=len(previous['records']) or len(current)!=len(mapping['records']) or set(old)!=set(current):raise ValueError('previous mapped paths lost or duplicated')
    lineage=[]
    for key,row in current.items():
        prior=old[key]
        for name in ('plan_edges','iso_edges','plan_start','plan_end','iso_start','iso_end','plan_snapshot','iso_snapshot'):
            if row[name]!=prior[name]:raise ValueError('previously mapped local scope changed and needs separate reconciliation '+name)
        lineage.append(dict(previous_mapping_id=prior['mapping_id'],current_mapping_id=row['mapping_id'],local_path_semantics_preserved=True,human_confirmation_transferred=False))
    return lineage


def groups_correspond(docs,graphs,inventory,circle_policy,policy,hashes):
    settings=policy.get('groups',[]);group_ids=[g['group_id'] for g in settings]
    if not settings or len(group_ids)!=len(set(group_ids)):raise ValueError('explicit independent mapping groups required')
    groups=[];all_rows=[];equipment=[];used={v:set() for v in graphs};old_hash=inventory['wave_reconstruction_inventory_rebase']['old_plan_graph_sha256']
    for group in settings:
        spec=group['previous_mapping'];previous=load(spec['path'])
        if sha(spec['path'])!=spec['sha256']:raise ValueError('previous mapping artifact changed')
        result=correspond_current(docs,graphs,inventory,circle_policy,group,hashes)
        lineage=historical_lineage(result,previous,old_hash)
        for view in graphs:
            ids={eid for row in result['records'] for eid in row[view+'_edges']}
            if used[view]&ids:raise ValueError('independent corridor groups overlap local writers')
            used[view].update(ids)
        if set(equipment)&set(result['equipment_scope']):raise ValueError('equipment appears in more than one independent group')
        equipment.extend(result['equipment_scope']);result.update(group_id=group['group_id'],historical_mapping_lineage=lineage,previous_mapping_sha256=spec['sha256'])
        groups.append(result);all_rows.extend(dict(row,group_id=group['group_id']) for row in result['records'])
    if len({r['mapping_id'] for r in all_rows})!=len(all_rows):raise ValueError('group mapping IDs are not globally distinct')
    return dict(mode=BATCH_SCHEMA,status='source_checked_path_correspondence_attributes_pending',groups=groups,records=all_rows,equipment_scope=equipment,
        plan_graph_sha256=hashes['plan']['graph_sha256'],iso_graph_sha256=hashes['iso']['graph_sha256'],source_sha256={v:h['source_sha256'] for v,h in hashes.items()},
        evidence=dict(native_wave_inventory_rebase=copy.deepcopy(inventory['wave_reconstruction_inventory_rebase'])),
        local_graphs_mutated=False,expert_confirmation_claimed=False,physical_source_identity_resolved=False,physical_values_assigned=0,human_accepted=False,hil_ready=False)


def compute(paths,policy):
    for key in ('inventory','inventory_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('wave mapping inventory input changed '+key)
    folder=Path(paths['inventory']).resolve().parent
    if Path(paths['inventory']).resolve()!=folder/'inventory.json' or Path(paths['inventory_receipt']).resolve()!=folder/'inventory-receipt.json':raise ValueError('noncanonical wave inventory')
    receipt=load(paths['inventory_receipt'])
    if receipt.get('mode')!=INVENTORY_MODE:raise ValueError('new native wave inventory receipt required')
    inventory=verify_inventory(folder);local=receipt['local_inputs']
    old=load(receipt['inputs']['parent_receipt']['path']);circle_policy=load(old['inputs']['policy']['path'])
    docs={};graphs={};hashes={}
    for key,item in local.items():
        if sha(item['path'])!=item['sha256']:raise ValueError('new local wave/axis dependency changed '+key)
    for view in ('plan','iso'):
        graphs[view]=load(local[view+'_graph']['path']);docs[view],_=read_source(local[view+'_source']['path'])
        hashes[view]=dict(source_sha256=local[view+'_source']['sha256'],graph_sha256=local[view+'_graph']['sha256'])
    result=groups_correspond(docs,graphs,inventory,circle_policy,policy,hashes)
    if result['plan_graph_sha256']!=inventory['wave_reconstruction_inventory_rebase']['plan_graph_sha256']:
        raise ValueError('mapping did not consume the current wave graph')
    result['evidence'].update(inventory_sha256=sha(paths['inventory']),inventory_receipt_sha256=sha(paths['inventory_receipt']),
        native_wave_inventory_rebase=copy.deepcopy(inventory['wave_reconstruction_inventory_rebase']))
    return result,copy.deepcopy(local)


def implementation_hashes():
    from wave_rebased_branch_inventory import implementation_hashes as inventory_hashes
    from match_inherited_circle_crossview_paths import implementation_hashes as mapping_hashes
    result=inventory_hashes();result.update(mapping_hashes());result[Path(__file__).name]=sha(__file__)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'source-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt.get('logical_mapping_schema')!=BATCH_SCHEMA or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('wave mapping owner or implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('wave mapping input changed')
    paths={k:item['path'] for k,item in receipt['inputs'].items()};result,local=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256'] or local!=receipt['local_inputs']:
        raise ValueError('wave mapping native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('inventory-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(inventory=a.inventory_run/'inventory.json',inventory_receipt=a.inventory_run/'inventory-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result,local=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'mapping.json';target.write_bytes(encode(result))
    (a.output/'source-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,logical_mapping_schema=BATCH_SCHEMA,
        inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},local_inputs=local,
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(groups=len(result['groups']),paths=len(result['records']),equipment=len(result['equipment_scope']),physical_values_assigned=0),flush=True)


if __name__=='__main__':main()
