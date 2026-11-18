"""Replay explicitly scoped project descendants from preserved owner assets.

The corner remains SH16-only. Native capped-interface semantics reuse the
shared kernel. Legacy receipts are preserved; this reader issues no HIL pass.
"""
import importlib.util,sys
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from native_capped_branch_annotations import verify_output as verify_annotations
from source_capped_branch_roles import apply
from match_source_checked_crossview_paths import selected_snapshot

SOURCE_SHA='4008f96373fe154c5ad1de1892f6b1dbd0e07ff9582267f819f8a66a7ba268e1'
ASSETS=Path(__file__).resolve().parent.parent/'assets/project-adapters/SH16-10-v1'
NAMES={'related_corner':'sh16_related_corner_known_issue_v1.py','capped_roles':'sh16_source_capped_branch_roles_v1.py'}


def asset(key):
    manifest=load(ASSETS/'manifest.json');spec=manifest['files'][key];path=ASSETS/spec['filename']
    if (manifest.get('schema')!='byte_preserved_SH16_project_native_adapters_v1' or manifest.get('project')!='SH16-10'
        or manifest.get('source_sha256')!=SOURCE_SHA or spec['filename']!=NAMES[key]
        or not path.resolve().is_relative_to(ASSETS.resolve()) or sha(path)!=spec['sha256']):raise ValueError('project native owner asset changed or escaped scope')
    return path,spec['sha256']


def corner_owner():
    path,digest=asset('related_corner');spec=importlib.util.spec_from_file_location('_preserved_SH16_corner_owner',path)
    module=importlib.util.module_from_spec(spec);previous=list(sys.path)
    try:spec.loader.exec_module(module)
    finally:sys.path[:]=previous
    return module,digest


def kind(graph):
    if 'sourceDeclaredCappedBranchInterfaces' in graph:return 'capped_roles'
    if 'sourceSH16RelatedCornerKnownIssue' in graph:return 'related_corner'
    raise ValueError('graph has no supported explicit project descendant')


def verify_corner(directory):
    directory=Path(directory).resolve();graph=load(directory/'graph_with_edges.json');audit=load(directory/'SH16-related-corner-known-issue-audit.json')
    if kind(graph)!='related_corner' or graph.get('metadata',{}).get('source_sha256')!=SOURCE_SHA:raise ValueError('project corner is SH16-10 only')
    owner,digest=corner_owner()
    if audit.get('mode')!='SH16_10_source_checked_related_corner_known_issue_v1' or audit.get('owner_sha256')!=digest:raise ValueError('project corner receipt owner differs from preserved asset')
    result=owner.verify_output(directory)
    return dict(kind='related_corner',audit=result,parent_graph=Path(result['inputs']['graph']['path']).resolve(),
        current_graph_sha256=sha(directory/'graph_with_edges.json'),disposed_node_ids=[n['node_id'] for n in graph['sourceSH16RelatedCornerKnownIssue']['retired_node_snapshots']],
        owner_asset_sha256=digest,source_replay='passed',general_circle_rule=False,new_human_confirmation=False)


def verify_capped_roles(directory,mapping_path,mapping_sha256):
    directory=Path(directory).resolve();graph_path=directory/'graph_with_edges.json';graph=load(graph_path)
    audit=load(directory/'source-capped-interface-roles-audit.json');_,adapter_sha=asset('capped_roles')
    if (kind(graph)!='capped_roles' or graph.get('metadata',{}).get('source_sha256')!=SOURCE_SHA
        or audit.get('mode')!='SH16_project_parent_native_capped_interface_role_v1' or audit.get('adapter_sha256')!=adapter_sha
        or audit.get('role_kernel_sha256')!=sha(Path(__file__).with_name('source_capped_branch_roles.py'))):raise ValueError('native capped-interface role owner or project differs')
    if any(sha(row['path'])!=row['sha256'] for row in audit['inputs'].values()):raise ValueError('native capped-interface role inputs changed')
    parent_path=Path(audit['inputs']['graph']['path']).resolve();parent=load(parent_path);parent_check=verify_corner(parent_path.parent)
    annotation_path=Path(audit['inputs']['native_annotations']['path']).resolve();annotation=verify_annotations(annotation_path.parent);inventory=load(annotation_path)
    if (annotation['inputs']['graph']['sha256']!=sha(parent_path) or Path(annotation['inputs']['graph']['path']).resolve()!=parent_path
        or annotation['inputs']['source']['sha256']!=SOURCE_SHA):raise ValueError('annotation inventory is not the actual native parent')
    recomputed,proof=apply(parent,inventory,sha(parent_path),sha(annotation_path))
    if encode(recomputed)!=graph_path.read_bytes() or audit['output_graph_sha256']!=sha(graph_path):raise ValueError('shared source-role kernel does not reproduce current graph')
    component_path=directory/'assigned_edge_device_instances.csv';parent_components=Path(audit['inputs']['devices']['path']).resolve()
    if parent_components.parent!=parent_path.parent or component_path.read_bytes()!=parent_components.read_bytes():raise ValueError('project capped-interface components changed')
    if mapping_path is None or not mapping_sha256 or sha(mapping_path)!=mapping_sha256:raise ValueError('explicit hash-bound mapping snapshot scope required')
    mapping=load(mapping_path)
    if mapping.get('mode')!='independent_native_common_anchor_mapping_groups_v1' or len(mapping.get('records',[]))!=66:raise ValueError('unsupported project mapping snapshot scope')
    if mapping.get('plan_graph_sha256')!=parent['sourceSH16RelatedCornerKnownIssue']['input_graph_sha256']:raise ValueError('mapping historical plan parent differs')
    for row in mapping['records']:
        if selected_snapshot(recomputed,row['plan_edges'])!=row['plan_snapshot']:raise ValueError('current mapping scope changed; explicit remapping required')
    # This verifies selected scope equality, not correspondence or receipt rebinding.
    original_proof=audit['proof'];ids=[r['node_id'] for r in graph['sourceDeclaredCappedBranchInterfaces']['records']]
    if ids!=['UT0192'] or not original_proof.get('node_ids_retained') or original_proof.get('nodes_retired')!=0 or original_proof.get('physical_lengths_assigned')!=0:
        raise ValueError('project source-role disposition differs')
    return dict(kind='capped_roles',audit=audit,parent_graph=parent_path,current_graph_sha256=sha(graph_path),disposed_node_ids=ids,
        native_parent_check=parent_check,owner_asset_sha256=adapter_sha,shared_role_kernel_sha256=audit['role_kernel_sha256'],
        current_mapping_snapshot_scope=dict(path=str(Path(mapping_path).resolve()),sha256=mapping_sha256,records=66,selected_scopes_unchanged=True,receipts_rebound=False),
        source_replay='passed',node_ids_retained=True,nodes_retired=0,connections_added=0,physical_lengths_assigned=0,new_human_confirmation=False)


def verify_output(directory,mapping_path=None,mapping_sha256=None):
    graph=load(Path(directory)/'graph_with_edges.json')
    return verify_capped_roles(directory,mapping_path,mapping_sha256) if kind(graph)=='capped_roles' else verify_corner(directory)
