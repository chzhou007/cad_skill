"""Refine path correspondence at native Ts matched through their branch targets.

Local graph edges already end at these Ts. Only the mapping layer is refined;
DN, physical lengths, equipment ports and human acceptance are not assigned.
"""
import argparse,copy,json
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from match_paired_service_crossview_paths import verify_output as verify_base,implementation_hashes as base_hashes
from match_source_checked_crossview_paths import selected_snapshot
from native_paired_junction_correspondence import collect
from native_path_coverage_audit import audit as audit_paths
from source_readability import read_source

MODE='paired_service_junction_refined_paths_v1'


def refine(mapping,proof,graphs,required_groups):
    if proof.get('graph_mutated') is not False or proof.get('physical_lengths_assigned')!=0 or proof.get('human_accepted') is not False:raise ValueError('unsupported junction proof state')
    keys=[(g['parent_pair_id'],g['system']) for g in required_groups];rows={(r['parent_pair_id'],r['system']):r for r in proof['records']}
    if not keys or len(keys)!=len(set(keys)) or len(rows)!=len(proof['records']):raise ValueError('duplicate or empty junction refinement scope')
    for key in keys:
        if key not in rows or rows[key].get('complete') is not True or any(rows[key]['unmatched_nodes'].values()) or not rows[key]['matches']:
            raise ValueError('required interior junction correspondence is incomplete')
    pairs={tuple(p['equipment_ids']):p for p in mapping['evidence']['paired_services']};records=[];retired=[];done=set()
    for record in mapping['records']:
        pair=pairs.get(tuple(record.get('endpoint_equipment_ids',[]))) if record['kind']=='main_between_equipment_branches' else None
        key=(pair['pair_id'],record['system']) if pair else None
        if key not in keys:records.append(copy.deepcopy(record));continue
        if key in done:raise ValueError('duplicate parent interval')
        done.add(key);state=pair['services'][record['system']];matches=rows[key]['matches'];route=state['routes'];places={}
        for view in graphs:
            if record[view+'_edges']!=route[view]['edges']:raise ValueError('refined parent route differs')
            expected={r['node_id'] for r in state['internal_native_junctions'][view]};actual=[m['views'][view]['parent_node'] for m in matches]
            if set(actual)!=expected or len(actual)!=len(set(actual)):raise ValueError('matched interior T set differs')
            places[view]={m['junction_mapping_id']:route[view]['nodes'].index(m['views'][view]['parent_node']) for m in matches}
        ordered=sorted(matches,key=lambda m:places['plan'][m['junction_mapping_id']])
        iso_order=[places['iso'][m['junction_mapping_id']] for m in ordered]
        if iso_order!=sorted(set(iso_order)):raise ValueError('matched native junction order disagrees')
        cuts={v:[0]+[places[v][m['junction_mapping_id']] for m in ordered]+[len(route[v]['edges'])] for v in graphs}
        if any(len(set(c))!=len(c) or c!=sorted(c) for c in cuts.values()):raise ValueError('junction cut is not strictly interior')
        retired.append(copy.deepcopy(record))
        for i in range(len(ordered)+1):
            row=copy.deepcopy(record);row.update(mapping_id=record['mapping_id']+f'-J{i+1:02d}',derived_from_mapping_id=record['mapping_id'],
                decision_basis='paired_services_and_native_branch_target_junction_correspondence',status='source_checked_junction_refined_path_not_human_accepted')
            row['context_equipment_ids']=row.pop('endpoint_equipment_ids');row['kind']='main_between_matched_junctions'
            for view in graphs:
                start,end=cuts[view][i:i+2];ids=route[view]['edges'][start:end]
                row.update({view+'_edges':ids,view+'_start':route[view]['nodes'][start],view+'_end':route[view]['nodes'][end],view+'_snapshot':selected_snapshot(graphs[view],ids)})
            row['junction_correspondence_ids']=[m['junction_mapping_id'] for m in ordered[max(0,i-1):i+1]];records.append(row)
    if done!=set(keys):raise ValueError('required parent main interval is missing')
    for key in keys:
        for match in rows[key]['matches']:
            row=dict(mapping_id='LINK-'+match['junction_mapping_id'],kind='main_between_matched_junctions',system=key[1],floor=mapping['floor'],
                parent_pair_id=key[0],target_pair_id=match['target_pair_id'],target_equipment_id=match['target_equipment_id'],junction_correspondence_ids=[match['junction_mapping_id']],
                decision_basis='native_offcorridor_branch_to_first_independently_checked_equipment_T',
                status='source_checked_junction_link_path_not_human_accepted',physical_ports_verified=False,human_accepted=False)
            for view in graphs:
                route=match['views'][view]['route'];row.update({view+'_edges':route['edges'],view+'_start':route['start'],view+'_end':route['end'],view+'_snapshot':selected_snapshot(graphs[view],route['edges'])})
            records.append(row)
    for view in graphs:
        ids=[eid for r in records for eid in r[view+'_edges']]
        if len(ids)!=len(set(ids)):raise ValueError('refined correspondence overlaps '+view)
    if len({r['mapping_id'] for r in records})!=len(records):raise ValueError('duplicate refined mapping IDs')
    output=copy.deepcopy(mapping);output.update(mode=MODE,status='source_checked_junction_refined_correspondence_attributes_pending',records=records,superseded_path_records=retired)
    output['evidence']['native_junction_correspondence']=copy.deepcopy(proof)
    output['limitations']=list(mapping.get('limitations',[]))+['Only correspondence is refined; recompute affected DN extents, source lengths and attributes before publishing.']
    output.update(local_graphs_mutated=False,physical_values_fused=False,expert_confirmation_claimed=False,human_accepted=False,hil_ready=False)
    return output


def compute(paths,policy):
    for key in ('base_mapping','base_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('refinement base input changed '+key)
    directory=Path(paths['base_mapping']).resolve().parent
    if Path(paths['base_mapping']).resolve()!=directory/'mapping.json' or Path(paths['base_receipt']).resolve()!=directory/'source-mapping-receipt.json':raise ValueError('noncanonical paired base mapping')
    mapping=verify_base(directory);receipt=load(paths['base_receipt']);graphs={v:load(receipt['inputs'][v+'_graph']['path']) for v in ('plan','iso')}
    docs={v:read_source(receipt['inputs'][v+'_source']['path'])[0] for v in graphs}
    hashes={v:dict(source_sha256=mapping['source_sha256'][v],graph_sha256=mapping[v+'_graph_sha256']) for v in graphs}
    proof=collect(docs,graphs,mapping,hashes);result=refine(mapping,proof,graphs,policy['required_groups'])
    result['previous_mapping_sha256']=sha(paths['base_mapping'])
    for view in graphs:
        ids=[eid for r in result['records'] if r['kind']!='equipment_branch' for eid in r[view+'_edges']]
        coverage=audit_paths(docs[view],graphs[view],dict(hashes[view],edges=ids),hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
        if any(s['status']!='single_source_line_covers' for e in coverage['edges'] for s in e['segments']):raise ValueError('refined main lacks unique native coverage')
        result['evidence'].setdefault('refined_main_coverage',{})[view]=coverage
    return result


def implementation_hashes():
    hashes=base_hashes()
    for name in ('refine_paired_service_path_correspondence.py','native_paired_junction_correspondence.py'):hashes[name]=sha(Path(__file__).with_name(name))
    return hashes


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'source-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('junction refinement implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('junction refinement dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or receipt['output_sha256']!=sha(directory/'mapping.json'):raise ValueError('native junction refinement replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('base-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(base_mapping=a.base_run/'mapping.json',base_receipt=a.base_run/'source-mapping-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'mapping.json').write_bytes(encode(result))
    (a.output/'source-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(a.output/'mapping.json'),human_accepted=False)))
    print(dict(refined_paths=len(result['records']),retired_intervals=len(result['superseded_path_records']),physical_values_fused=False),flush=True)


if __name__=='__main__':main()
