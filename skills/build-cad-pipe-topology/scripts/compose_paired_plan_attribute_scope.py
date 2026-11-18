"""Append an independently checked paired scope to the current presentation."""
import argparse,copy,json,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from compose_source_checked_plan_scopes import verify_output as verify_base
from attach_paired_plan_scope_attributes import verify_output as verify_scope,BASIS

MODE='paired_plan_attribute_extension_v1'
ROOT='pairedServiceCrossViewAttributeFusion'


def append_scope(base,common,scope,scope_hash):
    if ROOT in base or ROOT in scope:raise ValueError('paired extension already present')
    if not base.get('sourceCheckedCrossViewAttributeFusion') or scope.get('sourceCheckedCrossViewAttributeFusion',{}).get('proof_type')!=BASIS:
        raise ValueError('unsupported base or paired attribute scope')
    indices={label:{e['edge_id']:e for e in graph['edges']} for label,graph in [('base',base),('common',common),('scope',scope)]}
    if any(len(index)!=len(graph['edges']) for index,graph in zip(indices.values(),(base,common,scope))):raise ValueError('duplicate attribute graph edge IDs')
    if not(indices['base'].keys()==indices['common'].keys()==indices['scope'].keys()):raise ValueError('attribute scope graph identities differ')
    for graph in (base,scope):
        for key,value in common.items():
            if key not in ('metadata','edges') and graph.get(key)!=value:raise ValueError('attribute scope changed common local evidence '+key)
        for eid,edge in indices['common'].items():
            current={k:v for k,v in indices['base' if graph is base else 'scope'][eid].items() if k!='cross_view_attributes'}
            if current!={k:v for k,v in edge.items() if k!='cross_view_attributes'}:raise ValueError('attribute scope changed pipe geometry or components')
    out=copy.deepcopy(base);target={e['edge_id']:e for e in out['edges']};added=[]
    for eid,edge in indices['scope'].items():
        prior=indices['common'][eid]
        if 'cross_view_attributes' in prior:
            if edge!=prior or indices['base'][eid]!=prior:raise ValueError('common confirmed attributes changed')
            continue
        if 'cross_view_attributes' not in edge:continue
        if 'cross_view_attributes' in indices['base'][eid]:raise ValueError('paired scope overlaps previously published writer')
        if edge['cross_view_attributes'].get('mapping_basis')!=BASIS:raise ValueError('paired addition has incorrect proof type')
        target[eid]['cross_view_attributes']=copy.deepcopy(edge['cross_view_attributes']);added.append(eid)
    if not added:raise ValueError('empty paired attribute increment')
    root=copy.deepcopy(scope['sourceCheckedCrossViewAttributeFusion'])
    root.update(status='source_checked_paired_plan_attribute_extension_hil_pending',scope_graph_sha256=scope_hash,
        added_axis_edges=sorted(added),prior_attributes_preserved=True,independent_scope_requires_composition=False,human_accepted=False)
    out[ROOT]=root;out.setdefault('metadata',{}).update(graph_complete=False,hil_ready=False,review_status='unreviewed_after_paired_plan_attribute_extension')
    return out,dict(added_axis_edges=sorted(added),prior_attribute_edges=sum('cross_view_attributes' in e for e in base['edges']),
        records=root['records'],plan_DN_scope_evidence_sha256=root.get('plan_DN_scope_evidence_sha256'),
        old_nodes_edges_source_roots_and_components_preserved=True,all_prior_attribute_values_preserved=True)


def compute(paths,policy):
    for key in ('base_graph','common_parent_graph','scope_graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('paired composition input changed '+key)
    base=verify_base(Path(paths['base_graph']).parent);scope=verify_scope(Path(paths['scope_graph']).parent)
    common=dict(path=str(Path(paths['common_parent_graph']).resolve()),sha256=sha(paths['common_parent_graph']))
    if base['parent_graph']!=common or scope['parent_graph']!=common:raise ValueError('paired scope and current presentation use different common parents')
    if base['output_graph_sha256']!=sha(paths['base_graph']) or scope['output_graph_sha256']!=sha(paths['scope_graph']):raise ValueError('verified composition input graphs differ')
    if any(a['inputs']['devices']['sha256']!=sha(paths['devices']) for a in (base,scope)):raise ValueError('paired composition component inventories differ')
    graph,proof=append_scope(load(paths['base_graph']),load(paths['common_parent_graph']),load(paths['scope_graph']),sha(paths['scope_graph']))
    return graph,dict(proof,plan_DN_scope_fusion=scope['plan_DN_scope_fusion'],parent_graph=dict(path=str(Path(paths['base_graph']).resolve()),sha256=sha(paths['base_graph'])),common_parent_graph=common,
        paired_scope_graph=dict(path=str(Path(paths['scope_graph']).resolve()),sha256=sha(paths['scope_graph'])))


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('compose_paired_plan_attribute_scope.py','compose_source_checked_plan_scopes.py','attach_paired_plan_scope_attributes.py')}


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'paired-attribute-extension-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('paired composition implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('paired composition dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or audit['output_graph_sha256']!=sha(directory/'graph_with_edges.json') or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('paired composition native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('paired composition canonical components changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('base-graph','common-parent-graph','scope-graph','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={key:getattr(a,key) for key in ('base_graph','common_parent_graph','scope_graph','devices','policy')}
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'paired-attribute-extension-audit.json').write_bytes(encode(audit));print(dict(added=len(audit['added_axis_edges']),prior=audit['prior_attribute_edges'],human_accepted=False),flush=True)


if __name__=='__main__':main()
