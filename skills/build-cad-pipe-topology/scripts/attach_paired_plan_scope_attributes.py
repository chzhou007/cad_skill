"""Build a paired attribute child on the common confirmed-attribute parent.

This is an independently replayable scope. It must be composed with the other
checked scopes before replacing the published multi-floor axis presentation.
"""
import argparse,copy,json,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from paired_plan_DN_scopes import verify_output as verify_DN
from match_paired_service_crossview_paths import MODE as MAPPING_MODE
from attach_crossview_plan_attributes import verify_output as verify_parent
from attach_source_checked_plan_attributes import attach,native_local_diameters,metric_context
from source_checked_plan_path_coverage import audit as audit_paths
from source_readability import read_source
from fuse_plan_DN_scopes import apply as fuse_DN

MODE='paired_service_plan_attribute_scope_v1'
BASIS='native_paired_service_corridors'


def attach_checked_scope(parent,mapping,plan,coverage,units,diameters,sources,mapping_hash,DN,DN_hash,angles):
    if (mapping.get('mode')!=MAPPING_MODE or mapping.get('status')!='source_checked_paired_service_correspondence_attributes_pending'
        or mapping.get('human_accepted') is not False or mapping.get('local_graphs_mutated') is not False):raise ValueError('unsupported paired attribute mapping')
    if parent.get('sourceCheckedCrossViewAttributeFusion'):raise ValueError('paired scope needs common confirmed parent, not a composed presentation')
    graph,records=attach(parent,mapping,plan,coverage,units,diameters,sources,mapping_hash)
    graph,dn_proof=fuse_DN(graph,mapping,plan,DN,DN_hash,angles)
    claimed={eid for r in mapping['records'] for eid in r['iso_edges']}
    for edge in graph['edges']:
        if edge['edge_id'] in claimed:edge['cross_view_attributes']['mapping_basis']=BASIS
    graph['sourceCheckedCrossViewAttributeFusion'].update(proof_type=BASIS,independent_scope_requires_composition=True)
    return graph,records,dn_proof


def compute(paths,policy):
    for key in ('mapping','mapping_receipt','diameter_evidence','diameter_receipt','parent_graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('paired attribute input changed '+key)
    dnfolder=Path(paths['diameter_evidence']).resolve().parent
    if Path(paths['diameter_evidence']).resolve()!=dnfolder/'plan-DN-scopes.json' or Path(paths['diameter_receipt']).resolve()!=dnfolder/'plan-DN-scope-receipt.json':raise ValueError('noncanonical paired DN evidence')
    DN=verify_DN(dnfolder);dnreceipt=load(paths['diameter_receipt'])
    if DN['mapping_sha256']!=sha(paths['mapping']) or dnreceipt['inputs']['mapping_receipt']['sha256']!=sha(paths['mapping_receipt']):raise ValueError('paired DN and mapping scope differ')
    # verify_DN already independently replays this exact mapping and inventory.
    mapping=load(paths['mapping']);mr=load(paths['mapping_receipt']);parent=verify_parent(Path(paths['parent_graph']).parent)
    if (parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['parent_graph']['sha256']!=mapping['iso_graph_sha256']
        or parent['inputs']['devices']['sha256']!=sha(paths['devices'])):raise ValueError('paired scope common parent or components differ')
    plan_path=Path(mr['inputs']['plan_graph']['path']);source_path=Path(mr['inputs']['plan_source']['path'])
    if sha(plan_path)!=DN['graph_sha256'] or sha(source_path)!=DN['source_sha256']:raise ValueError('paired source topology changed after DN replay')
    plan=load(plan_path);doc,preflight=read_source(source_path);ids=[eid for r in mapping['records'] for eid in r['plan_edges']]
    coverage=audit_paths(doc,plan,dict(source_sha256=DN['source_sha256'],graph_sha256=DN['graph_sha256'],edges=ids),DN['source_sha256'],DN['graph_sha256'])
    units,detail=metric_context(doc,policy,plan,mapping)
    if detail:raise ValueError('paired floor-plan scope does not accept unmeasured details')
    diameters={r['mapping_id']:native_local_diameters(doc,plan,r,coverage) for r in mapping['records']}
    sources=dict(plan=DN['source_sha256'],isometric=mapping['source_sha256']['iso'],plan_graph=DN['graph_sha256'],local_iso_graph=mapping['iso_graph_sha256'])
    original=load(paths['parent_graph']);graph,records,dn_proof=attach_checked_scope(original,mapping,plan,coverage,units,diameters,sources,sha(paths['mapping']),DN,sha(paths['diameter_evidence']),policy.get('isometric_horizontal_directions_degrees',[]))
    before={e['edge_id']:e for e in original['edges']};after={e['edge_id']:e for e in graph['edges']}
    if set(before)!=set(after) or graph['nodes']!=original['nodes']:raise ValueError('paired scope changed graph identity')
    for eid,edge in before.items():
        if {k:v for k,v in edge.items() if k!='cross_view_attributes'}!={k:v for k,v in after[eid].items() if k!='cross_view_attributes'}:raise ValueError('paired scope changed local pipe or components')
        if 'cross_view_attributes' in edge and edge!=after[eid]:raise ValueError('paired scope overwrote prior confirmed attributes')
    audit=dict(records=records,plan_DN_scope_fusion=dn_proof,source_preflight=preflight,metric_evidence=units,
        parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),
        scope_only_not_published_presentation=True,existing_common_parent_attribute_edges=sum('cross_view_attributes' in e for e in original['edges']),
        added_axis_edges=len({eid for r in mapping['records'] for eid in r['iso_edges']}),graph_identity_and_component_fields_preserved=True)
    return graph,audit


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('attach_paired_plan_scope_attributes.py','paired_plan_DN_scopes.py',
        'attach_source_checked_plan_attributes.py','fuse_plan_DN_scopes.py','confirmed_detail_projection.py','source_checked_plan_path_coverage.py','native_plan_projection_lengths.py')}


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'source-attribute-fusion-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('paired attribute implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('paired attribute dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or audit['output_graph_sha256']!=sha(directory/'graph_with_edges.json') or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('paired attribute native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('paired attribute component CSV changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('mapping-run','diameter-run','parent-graph','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'source-mapping-receipt.json',
        diameter_evidence=a.diameter_run/'plan-DN-scopes.json',diameter_receipt=a.diameter_run/'plan-DN-scope-receipt.json',parent_graph=a.parent_graph,devices=a.devices,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'source-attribute-fusion-audit.json').write_bytes(encode(audit));print(dict(added_axis_edges=audit['added_axis_edges'],scope_requires_composition=True),flush=True)


if __name__=='__main__':main()
