"""Replay an inherited topology normalization before all attribute checks."""
import argparse,copy,csv,importlib,runpy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from axis_continuous_source_vertical_DN import verify_output as verify_prior
from native_air_vent_attribute_items import collect as normalized_items
from axis_direct_endpoint_level_evidence import collect as endpoint_levels

MODE='native_air_vent_attribute_normalization_reapplication_v1'
key=lambda r:(r['edge_id'],r['path_index'],r['segment_index'])


def compute(manifest):
    inputs=manifest['inputs']
    def checked():
        if any(sha(v['path'])!=v['sha256'] for v in inputs.values()):raise ValueError('fixed inherited-rule input changed')
    checked();prior=verify_prior(Path(inputs['base_continuous_proof']['path']).parent)
    current=load(inputs['current_viewer_manifest']['path']);provider=load(inputs['current_provider']['path'])
    if (current['attributeValueContext']['continuous_axis_vertical_DN']['all_current_vertical_domains']!=prior['counts']['current_known']
        or provider['counts']['all_current_vertical_DN_domains']!=prior['counts']['current_known']):raise ValueError('current vertical parent differs')
    doc,preflight=read_source(inputs['axis_source']['path']);graph=load(inputs['axis_graph']['path']);route=load(inputs['routing']['path']);before=encode(graph)
    if inputs['axis_source']['sha256']!=prior['inputs']['axis_source']['sha256'] or inputs['axis_graph']['sha256']!=prior['inputs']['axis_graph']['sha256']:
        raise ValueError('inherited source graph ancestry differs')
    with Path(inputs['canonical_components']['path']).open(encoding='utf-8-sig',newline='') as f:inventory=list(csv.DictReader(f))
    items,normalization=normalized_items(doc,graph,inventory)
    # Keep the original collector byte-exact. Its private dependency namespace
    # receives source-qualified normalized items; no source or graph rewriting.
    original=Path(__file__).with_name('axis_continuous_source_vertical_DN.py');ns=runpy.run_path(str(original))
    def item_reader(actual_doc,actual_graph):
        if actual_doc is not doc or actual_graph is not graph:raise ValueError('normalized attribute items escaped current native scope')
        return copy.deepcopy(items)
    ns['collect'].__globals__['native_items']=item_reader
    base_prior=load(prior['inputs']['prior_omission_DN']['path'])
    fresh=ns['collect'](doc,graph,route,base_prior,inputs['axis_source']['sha256'],inputs['axis_graph']['sha256'])
    old={key(r):r for r in prior['records']};actual={key(r):r for r in fresh['records']}
    if any(k not in actual or encode(v)!=encode(actual[k]) for k,v in old.items()):raise ValueError('already published continuous-source evidence changed')
    pending_keys={key(r) for r in prior['pending']};records=[r for r in fresh['records'] if key(r) in pending_keys]
    pending=[r for r in fresh['pending'] if key(r) in pending_keys]
    if len(records)+len(pending)!=len(prior['pending']):raise ValueError('complete current remaining vertical cohort not screened')
    levels=endpoint_levels(doc,graph,route,fresh['native_seed_qualification'],items,inputs['axis_source']['sha256'],inputs['axis_graph']['sha256'])
    if before!=encode(graph):raise ValueError('original pipe graph changed')
    checked()
    return dict(mode=MODE,inputs=inputs,source_preflight=preflight,inherited_air_vent_normalization=normalization,records=records,pending=pending,
        counts=dict(previous_known=prior['counts']['current_known'],current_remaining_screened=len(prior['pending']),new_vertical_DN=len(records),
            current_known=prior['counts']['current_known']+len(records),remaining_unknown=len(pending),qualified_vent_items=len(normalization['records']),
            qualified_endpoint_level_candidates=len(levels['records']),held_endpoint_level_candidates=len(levels['pending'])),
        endpoint_level_evidence=levels,old_published9_records_exact=True,old_source_collector_sha256=sha(original),complete_current_remaining_cohort_screened=True,
        old_axis_graph_unchanged=True,canonical_components_unchanged=True,physical_lengths_assigned=0,horizontal_values_assigned=0,human_accepted=False,published=False)


def implementations():
    names=('native_air_vent_attribute_items','axis_direct_endpoint_level_evidence','axis_continuous_source_vertical_DN',
        'axis_unbranched_vertical_DN','native_level_evidence','axis_floor_elevation_texts','crossview_equipment_branch_inventory','source_readability')
    return dict(entry=sha(__file__),legacy_geometry=sha(Path(__file__).with_name('legacy_v17')/'analyze_graph.py'),**{n:sha(importlib.import_module(n).__file__) for n in names})


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    r=compute(load(manifest));output.mkdir(parents=True);target=output/'air-vent-attribute-reapplication.json';target.write_bytes(encode(r))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementations(),output_sha256=sha(target))))
    return r


def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'air-vent-attribute-reapplication.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementations() or sha(m['path'])!=m['sha256'] or sha(target)!=receipt['output_sha256']:raise ValueError('inherited rule source/code/evidence changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('independent inherited-rule attribute replay differs')
    return fresh

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(produce(a.manifest,a.output)['counts'],flush=True)
