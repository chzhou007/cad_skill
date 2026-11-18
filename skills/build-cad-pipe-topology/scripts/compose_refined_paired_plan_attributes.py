"""Compose the replacement refined child with every prior nonpaired scope."""
import argparse,copy,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from compose_source_checked_plan_scopes import verify_output as verify_base
from attach_refined_paired_plan_attributes import verify_output as verify_scope,implementation_hashes as scope_hashes,BASIS

MODE='paired_junction_refined_attribute_composition_v1'
ROOT='pairedJunctionCrossViewAttributeFusion'


def append_scope(base,common,scope,scope_hash):
    if any(key in g for g in (base,scope) for key in (ROOT,'pairedServiceCrossViewAttributeFusion')):
        raise ValueError('refined composition replaces the coarse paired child; it cannot append to a paired presentation')
    if not base.get('sourceCheckedCrossViewAttributeFusion') or scope.get('sourceCheckedCrossViewAttributeFusion',{}).get('proof_type')!=BASIS:
        raise ValueError('unsupported nonpaired base or refined child')
    indices={name:{e['edge_id']:e for e in g['edges']} for name,g in [('base',base),('common',common),('scope',scope)]}
    if any(len(indices[name])!=len(g['edges']) for name,g in [('base',base),('common',common),('scope',scope)]):raise ValueError('duplicate composition edge identity')
    if not(indices['base'].keys()==indices['common'].keys()==indices['scope'].keys()):raise ValueError('refined composition graph identities differ')
    for name,graph in [('base',base),('scope',scope)]:
        for key,value in common.items():
            if key not in ('metadata','edges') and graph.get(key)!=value:raise ValueError('refined composition changed local source evidence '+key)
        for eid,edge in indices['common'].items():
            if {k:v for k,v in indices[name][eid].items() if k!='cross_view_attributes'}!={k:v for k,v in edge.items() if k!='cross_view_attributes'}:
                raise ValueError('refined composition changed local geometry or components')
    output=copy.deepcopy(base);target={e['edge_id']:e for e in output['edges']};added=[]
    for eid,edge in indices['scope'].items():
        common_edge=indices['common'][eid]
        if 'cross_view_attributes' in common_edge:
            if edge!=common_edge or indices['base'][eid]!=common_edge:raise ValueError('common confirmed attributes changed')
            continue
        if 'cross_view_attributes' not in edge:continue
        if 'cross_view_attributes' in indices['base'][eid]:raise ValueError('refined paired writer overlaps an inherited attribute')
        if edge['cross_view_attributes'].get('mapping_basis')!=BASIS:raise ValueError('refined paired proof type differs')
        target[eid]['cross_view_attributes']=copy.deepcopy(edge['cross_view_attributes']);added.append(eid)
    if not added:raise ValueError('empty refined attribute scope')
    root=copy.deepcopy(scope['sourceCheckedCrossViewAttributeFusion']);root.update(
        status='source_checked_refined_paired_attribute_composition_hil_pending',scope_graph_sha256=scope_hash,
        added_axis_edges=sorted(added),prior_attributes_preserved=True,independent_scope_requires_composition=False,human_accepted=False)
    output[ROOT]=root;output.setdefault('metadata',{}).update(graph_complete=False,hil_ready=False,review_status='unreviewed_after_native_junction_mapping_refinement')
    return output,dict(added_axis_edges=sorted(added),prior_attribute_edges=sum('cross_view_attributes' in e for e in base['edges']),
        records=root['records'],plan_DN_scope_evidence_sha256=root.get('plan_DN_scope_evidence_sha256'),
        old_nodes_edges_source_roots_and_components_preserved=True,all_prior_attribute_values_preserved=True,
        coarse_paired_child_not_added=True,related_prior_HIL_confirmation_inherited=False)


def compute(paths,policy):
    for key in ('base_graph','common_parent_graph','scope_graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('refined composition input changed '+key)
    base=verify_base(Path(paths['base_graph']).parent);scope=verify_scope(Path(paths['scope_graph']).parent)
    common=dict(path=str(Path(paths['common_parent_graph']).resolve()),sha256=sha(paths['common_parent_graph']))
    if base['parent_graph']!=common or scope['parent_graph']!=common:raise ValueError('refined child and base use different common parents')
    if base['output_graph_sha256']!=sha(paths['base_graph']) or scope['output_graph_sha256']!=sha(paths['scope_graph']):raise ValueError('refined composition verified graphs differ')
    if any(a['inputs']['devices']['sha256']!=sha(paths['devices']) for a in (base,scope)):raise ValueError('refined composition component inventory differs')
    graph,proof=append_scope(load(paths['base_graph']),load(paths['common_parent_graph']),load(paths['scope_graph']),sha(paths['scope_graph']))
    mapping=load(scope['inputs']['mapping']['path'])
    return graph,dict(proof,plan_DN_scope_fusion=scope['plan_DN_scope_fusion'],
        superseded_mapping_records=mapping['superseded_path_records'],
        parent_graph=dict(path=str(Path(paths['base_graph']).resolve()),sha256=sha(paths['base_graph'])),common_parent_graph=common,
        refined_scope_graph=dict(path=str(Path(paths['scope_graph']).resolve()),sha256=sha(paths['scope_graph'])))


def implementation_hashes():
    hashes=scope_hashes()
    for name in ('compose_refined_paired_plan_attributes.py','compose_source_checked_plan_scopes.py'):hashes[name]=sha(Path(__file__).with_name(name))
    return hashes


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'refined-paired-attribute-composition-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('refined composition implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('refined composition dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or audit['output_graph_sha256']!=sha(directory/'graph_with_edges.json') or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('refined composition native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('refined composition components changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('base-graph','common-parent-graph','scope-graph','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={key:getattr(a,key) for key in ('base_graph','common_parent_graph','scope_graph','devices','policy')}
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'refined-paired-attribute-composition-audit.json').write_bytes(encode(audit));print(dict(added=len(audit['added_axis_edges']),prior=audit['prior_attribute_edges'],human_accepted=False),flush=True)


if __name__=='__main__':main()
