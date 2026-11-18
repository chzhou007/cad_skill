"""Explain the complete current attribute backlog before requesting image HIL."""
import argparse,collections,copy,json
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from axis_floor_elevation_texts import collect as floor_elevations

MODE='current_axis_attribute_failure_diagnosis_v1'

def vertical_failures(proof,route,graph,annotations):
    scopes={(r['edge_id'],r['path_index'],r['segment_index']):r for r in route['records']};edges={e['edge_id']:e for e in graph['edges']};seeds=collections.defaultdict(set)
    for r in annotations['records']+proof['records']:seeds[r['edge_id']].add(r['nominal_mm'])
    rows=[]
    for item in proof['pending']:
        key=item['edge_id'],item['path_index'],item['segment_index'];scope=scopes[key];edge=edges[key[0]];original=item.get('original_reason')
        if original=='no_qualified_axis_annotation_on_this_vertical_segment':
            category='same_edge_other_path_seed_requires_native_omission_or_inline_composition'if len(seeds[key[0]])==1 else'no_qualified_vertical_seed_on_current_edge'if not seeds[key[0]]else'conflicting_other_path_seeds'
        else:category=original or item['reason']
        rows.append(dict(item,diagnosis=category,scope_points=scope['scope_points'],system=scope['system'],floor_start=scope['floor_start'],floor_end=scope['floor_end'],edge_type=edge['edge_type'],connection_mode=edge.get('connection_mode'),
            other_path_vertical_seed_values=sorted(seeds[key[0]]),native_source_status=scope['native_source_status'],native_omission_branch_evidence_present=bool(edge.get('source_native_block_branch')),physical_values_assigned=0))
    return rows

def compute(manifest):
    inputs=manifest['inputs']
    if any(sha(v['path'])!=v['sha256']for v in inputs.values()):raise ValueError('current diagnostic input changed')
    graph=load(inputs['axis_graph']['path']);route=load(inputs['routing']['path']);proof=load(inputs['vertical_DN_proof']['path']);annotations=load(inputs['vertical_annotations']['path']);provider=load(inputs['provider']['path'])
    source_hash=inputs['axis_source']['sha256'];graph_hash=inputs['axis_graph']['sha256']
    if graph['metadata']['source_sha256']!=source_hash or proof['inputs']['source']['sha256']!=source_hash or proof['inputs']['graph']['sha256']!=graph_hash or route['inputs']['source']['sha256']!=source_hash or route['inputs']['graph']['sha256']!=graph_hash:raise ValueError('diagnostic source/graph scope differs')
    doc,preflight=read_source(inputs['axis_source']['path']);levels=floor_elevations(doc,source_hash)
    rows=vertical_failures(proof,route,graph,annotations);horizontal=copy.deepcopy(provider['remaining_horizontal_attributes']);groups=collections.defaultdict(list)
    for r in horizontal:groups[r['next_scope']].append(r['edge_id'])
    return dict(mode=MODE,status='complete_current_failure_population_and_native_floor_elevation_texts_read_not_attribute_adoption',inputs=inputs,source_preflight=preflight,
        current_bundle_id=load(inputs['viewer_manifest']['path'])['bundleId'],axis_edges=len(graph['edges']),vertical_DN_counts=proof['counts'],vertical_DN_failures=rows,
        vertical_DN_failure_groups=dict(collections.Counter(r['diagnosis']for r in rows)),axis_floor_elevation_evidence=levels,
        horizontal_remaining=len(horizontal),horizontal_failure_groups=dict(groups),horizontal_unmatched=len(groups.get('apply_existing_native_crossview_discovery_to_unmatched_horizontal_path',[])),
        horizontal_mapped_but_attributes_incomplete=sum(len(v)for k,v in groups.items()if k!='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path'),
        existing_DN_proofs_independently_replayed_this_diagnostic=False,existing_DN_proofs_hash_checked=True,native_floor_elevation_TEXT_LINE_reexecuted=True,
        graph_mutated=False,physical_values_assigned=0,new_HIL_questions=0,human_accepted=False)

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);(output/'attribute-failure-diagnosis.json').write_bytes(encode(result))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=produce(a.manifest,a.output)
    print(dict(status=result['status'],vertical_failure_groups=result['vertical_DN_failure_groups'],native_floor_elevations=len(result['axis_floor_elevation_evidence']['records']),horizontal_unmatched=result['horizontal_unmatched'],horizontal_mapped_incomplete=result['horizontal_mapped_but_attributes_incomplete']),flush=True)

if __name__=='__main__':main()
