"""Attach source-plan attributes through native matched-junction paths.

The historical horizontal-main classifier is reused for its physical T-to-T
checks. Its legacy equipment-branch category is an internal classifier alias;
stored mapping kinds and evidence always retain the actual junction identities.
"""
import argparse,copy,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from refined_paired_plan_DN_scopes import verify_output as verify_DN,implementation_hashes as DN_hashes
from refine_paired_service_path_correspondence import MODE as MAPPING_MODE
from attach_crossview_plan_attributes import verify_output as verify_parent
from attach_source_checked_plan_attributes import attach,native_local_diameters,metric_context
from source_checked_plan_path_coverage import audit as audit_paths
from source_readability import read_source
from fuse_plan_DN_scopes import apply as fuse_DN

MODE='paired_service_junction_refined_attribute_scope_v1'
BASIS='native_paired_service_junction_correspondence'


def attach_checked_scope(parent,mapping,plan,coverage,units,diameters,sources,mapping_hash,DN,DN_hash,angles):
    if (mapping.get('mode')!=MAPPING_MODE or mapping.get('status')!='source_checked_junction_refined_correspondence_attributes_pending'
        or mapping.get('human_accepted') is not False or mapping.get('local_graphs_mutated') is not False
        or mapping.get('physical_values_fused') is not False):raise ValueError('unsupported refined paired attribute mapping')
    if parent.get('sourceCheckedCrossViewAttributeFusion') or parent.get('pairedServiceCrossViewAttributeFusion'):
        raise ValueError('refined child requires the common confirmed parent, not a composed presentation')
    graph,records=attach(parent,mapping,plan,coverage,units,diameters,sources,mapping_hash)
    classified=copy.deepcopy(mapping);junction_ids={m['junction_mapping_id'] for r in mapping['evidence']['native_junction_correspondence']['records'] if r['complete'] for m in r['matches']}
    for record in classified['records']:
        if record['kind']=='main_between_matched_junctions':
            if (not record.get('junction_correspondence_ids') or not set(record['junction_correspondence_ids'])<=junction_ids
                or 'endpoint_equipment_ids' in record):raise ValueError('generic T path lacks checked native junction identities')
            record['kind']='main_between_equipment_branches'
        elif record['kind'] not in ('equipment_branch','main_between_equipment_branches'):raise ValueError('unknown refined path kind')
    graph,dn_proof=fuse_DN(graph,classified,plan,DN,DN_hash,angles)
    by={r['mapping_id']:r for r in mapping['records']};claimed={eid for r in mapping['records'] for eid in r['iso_edges']}
    for edge in graph['edges']:
        if edge['edge_id'] not in claimed:continue
        attributes=edge['cross_view_attributes'];record=by[attributes['mapping_id']]
        if attributes['mapping_kind']!=record['kind']:raise ValueError('internal classifier changed stored junction semantics')
        attributes.update(mapping_basis=BASIS,junction_correspondence_ids=copy.deepcopy(record.get('junction_correspondence_ids',[])))
    for row in dn_proof:
        actual=by[row['mapping_id']];row.update(mapping_kind=actual['kind'],junction_correspondence_ids=copy.deepcopy(actual.get('junction_correspondence_ids',[])))
    graph['sourceCheckedCrossViewAttributeFusion'].update(proof_type=BASIS,independent_scope_requires_composition=True)
    return graph,records,dn_proof


def compute(paths,policy):
    for key in ('mapping','mapping_receipt','diameter_evidence','diameter_receipt','parent_graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('refined attribute input changed '+key)
    folder=Path(paths['diameter_evidence']).resolve().parent
    if Path(paths['diameter_evidence']).resolve()!=folder/'plan-DN-scopes.json' or Path(paths['diameter_receipt']).resolve()!=folder/'plan-DN-scope-receipt.json':raise ValueError('noncanonical refined DN stage')
    DN=verify_DN(folder);dr=load(paths['diameter_receipt'])
    if DN['mapping_sha256']!=sha(paths['mapping']) or dr['inputs']['mapping_receipt']['sha256']!=sha(paths['mapping_receipt']):raise ValueError('refined DN and mapping disagree')
    # verify_DN freshly replays this exact refined mapping and its base source.
    mapping=load(paths['mapping']);refined_receipt=load(paths['mapping_receipt']);mr=load(refined_receipt['inputs']['base_receipt']['path'])
    parent=verify_parent(Path(paths['parent_graph']).parent)
    if (parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['parent_graph']['sha256']!=mapping['iso_graph_sha256']
        or parent['inputs']['devices']['sha256']!=sha(paths['devices'])):raise ValueError('refined scope common parent or component inventory differs')
    pp=mr['inputs']['plan_graph']['path'];sp=mr['inputs']['plan_source']['path']
    if sha(pp)!=DN['graph_sha256'] or sha(sp)!=DN['source_sha256']:raise ValueError('refined plan source or graph changed')
    plan=load(pp);doc,preflight=read_source(sp);ids=[eid for r in mapping['records'] for eid in r['plan_edges']]
    coverage=audit_paths(doc,plan,dict(source_sha256=DN['source_sha256'],graph_sha256=DN['graph_sha256'],edges=ids),DN['source_sha256'],DN['graph_sha256'])
    units,detail=metric_context(doc,policy,plan,mapping)
    if detail:raise ValueError('refined floor-plan main scope cannot use nonmetric details')
    diameters={r['mapping_id']:native_local_diameters(doc,plan,r,coverage) for r in mapping['records']}
    sources=dict(plan=DN['source_sha256'],isometric=mapping['source_sha256']['iso'],plan_graph=DN['graph_sha256'],local_iso_graph=mapping['iso_graph_sha256'])
    original=load(paths['parent_graph']);graph,records,dn_proof=attach_checked_scope(original,mapping,plan,coverage,units,diameters,sources,sha(paths['mapping']),DN,sha(paths['diameter_evidence']),policy.get('isometric_horizontal_directions_degrees',[]))
    before={e['edge_id']:e for e in original['edges']};after={e['edge_id']:e for e in graph['edges']}
    if set(before)!=set(after) or graph['nodes']!=original['nodes']:raise ValueError('refined attributes changed graph identity')
    for eid,edge in before.items():
        if {k:v for k,v in edge.items() if k!='cross_view_attributes'}!={k:v for k,v in after[eid].items() if k!='cross_view_attributes'}:raise ValueError('refined attributes changed local pipes or components')
        if 'cross_view_attributes' in edge and edge!=after[eid]:raise ValueError('refined scope overwrote a confirmed historical attribute')
    audit=dict(records=records,plan_DN_scope_fusion=dn_proof,source_preflight=preflight,metric_evidence=units,
        parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),
        scope_only_not_published_presentation=True,added_axis_edges=len({eid for r in mapping['records'] for eid in r['iso_edges']}),
        graph_identity_and_component_fields_preserved=True,previous_coarse_mapping_superseded_not_additive=True)
    return graph,audit


def implementation_hashes():
    hashes=DN_hashes()
    for name in ('attach_refined_paired_plan_attributes.py','attach_source_checked_plan_attributes.py','fuse_plan_DN_scopes.py','confirmed_detail_projection.py','source_checked_plan_path_coverage.py','native_plan_projection_lengths.py'):
        hashes[name]=sha(Path(__file__).with_name(name))
    return hashes


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'source-attribute-fusion-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('refined attribute implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('refined attribute dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or audit['output_graph_sha256']!=sha(directory/'graph_with_edges.json') or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('refined attribute native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('refined attribute components changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('mapping-run','diameter-run','parent-graph','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'source-mapping-receipt.json',diameter_evidence=a.diameter_run/'plan-DN-scopes.json',diameter_receipt=a.diameter_run/'plan-DN-scope-receipt.json',parent_graph=a.parent_graph,devices=a.devices,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'source-attribute-fusion-audit.json').write_bytes(encode(audit));print(dict(added_axis_edges=audit['added_axis_edges'],scope_requires_composition=True),flush=True)


if __name__=='__main__':main()
