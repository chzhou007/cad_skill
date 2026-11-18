"""SH16-only parent adapter for the shared native source-interface role kernel."""
import copy,shutil,sys
from pathlib import Path
R=Path(__file__).resolve().parent;ROOT=R.parents[1]
sys.path[:0]=[str(ROOT/'skills/build-cad-pipe-topology/scripts'),str(ROOT/'skills/orchestrate-cad-drawing-pipeline/scripts')]
from confirm_crossview_paths import load,sha,encode
from match_source_checked_crossview_paths import selected_snapshot
from source_capped_branch_roles import apply
from native_capped_branch_annotations import verify_output as verify_annotations
from sh16_related_corner_known_issue_v1 import verify_output as verify_project_parent
from source_comparison_gate import graph_comparison_blockers

PARENT=R/'sh16-10-related-corner-known-issue-v1';ANNOTATIONS=R/'sh16-10-native-capped-branch-annotation-v1'
OUT=R/'sh16-10-source-capped-interface-roles-v1'


def compute():
    parent_audit=verify_project_parent(PARENT);annotation_audit=verify_annotations(ANNOTATIONS)
    gp=PARENT/'graph_with_edges.json';graph=load(gp);inventory=load(ANNOTATIONS/'inventory.json')
    if parent_audit['output_graph_sha256']!=sha(gp) or annotation_audit['inputs']['graph']['sha256']!=sha(gp):raise ValueError('actual parent and native annotation graph differ')
    result,proof=apply(graph,inventory,sha(gp),sha(ANNOTATIONS/'inventory.json'))
    before_edges={e['edge_id']:e for e in graph['edges']};after_edges={e['edge_id']:e for e in result['edges']}
    changed=[eid for eid in before_edges if before_edges[eid]!=after_edges[eid]]
    if changed!=['E0183'] or len(graph['nodes'])!=len(result['nodes']) or len(result['nodes'])!=258 or len(result['edges'])!=264:raise ValueError('source role change escaped selected scope')
    mapping_path=R/'sh16-10-11-wave-rebased-mapping-groups-v1/mapping.json';mapping=load(mapping_path)
    unchanged=[]
    for row in mapping['records']:
        if selected_snapshot(result,row['plan_edges'])!=row['plan_snapshot']:raise ValueError('selected current mapping scope needs extra reconciliation')
        unchanged.append(row['mapping_id'])
    if len(unchanged)!=66:raise ValueError('unexpected current mapping scope count')
    gate=load(PARENT/'source-comparison-gate.json');old=gate['graph_unresolved_node_blockers'];current,_=graph_comparison_blockers(result)
    if len(old)!=46 or len(current)!=45 or {n['node_id'] for n in old}-{n['node_id'] for n in current}!={'UT0192'}:
        raise ValueError('source role disposition is not exactly the direct native caption frontier')
    gate=copy.deepcopy(gate);gate['source_capped_interface_parent_comparison']=load(PARENT/'source-comparison-gate.json')
    message=f'{len(old)} graph nodes have unresolved source-terminal or equipment-overlap semantics'
    gate['pending']=[p for p in gate['pending'] if p!=message]
    gate['pending'].extend([f'{len(current)} graph nodes have unresolved source-terminal or equipment-overlap semantics',
        'Direct native capped interface role classified only at UT0192; graph-bound mapping/attribute receipts and human acceptance require explicit reconciliation'])
    gate.update(status='pending',graph_unresolved_node_blockers=current,hil_ready=False,human_accepted=False,
        source_declared_capped_branch_roles_stage=dict(source_replay='passed',classified_nodes=['UT0192'],retired_nodes=0,
            connections_added=0,physical_lengths_assigned=0,unchanged_selected_current_mapping_scopes=66,new_human_confirmation=False))
    proof.update(nodes=258,edges=264,canonical_components=parent_audit['proof']['canonical_components'],unresolved_source_terminals_before=46,
        unresolved_source_terminals_after=45,source_role_node='UT0192',edge_endpoint_metadata_changed=['E0183'],current66_selected_scope_snapshots_unchanged=True,
        current66_receipts_or_axis_attributes_rebound=False,source_qualifier='盲板封堵',native_source_annotation_audit_sha256=sha(ANNOTATIONS/'native-capped-branch-annotations-audit.json'),
        original_project_corner_audit_sha256=sha(PARENT/'SH16-related-corner-known-issue-audit.json'))
    return result,gate,proof


def verify_output(directory=OUT):
    directory=Path(directory);audit=load(directory/'source-capped-interface-roles-audit.json')
    kernel=ROOT/'skills/build-cad-pipe-topology/scripts/source_capped_branch_roles.py'
    if audit['adapter_sha256']!=sha(__file__) or audit['role_kernel_sha256']!=sha(kernel):raise ValueError('source role owner changed')
    for row in audit['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('source role inputs changed')
    graph,gate,proof=compute();gate['graph_sha256']=sha(directory/'graph_with_edges.json')
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or encode(gate)!=(directory/'source-comparison-gate.json').read_bytes() or proof!=audit['proof']:
        raise ValueError('source role independent native replay differs')
    if (directory/'assigned_edge_device_instances.csv').read_bytes()!=(PARENT/'assigned_edge_device_instances.csv').read_bytes():raise ValueError('source role changed components')
    return audit


def main():
    if OUT.exists():raise FileExistsError(OUT)
    graph,gate,proof=compute();OUT.mkdir();gp=OUT/'graph_with_edges.json';gp.write_bytes(encode(graph));gate['graph_sha256']=sha(gp)
    (OUT/'source-comparison-gate.json').write_bytes(encode(gate));shutil.copyfile(PARENT/'assigned_edge_device_instances.csv',OUT/'assigned_edge_device_instances.csv')
    paths=dict(graph=PARENT/'graph_with_edges.json',devices=PARENT/'assigned_edge_device_instances.csv',parent_comparison=PARENT/'source-comparison-gate.json',
        native_annotations=ANNOTATIONS/'inventory.json',native_annotation_audit=ANNOTATIONS/'native-capped-branch-annotations-audit.json')
    audit=dict(mode='SH16_project_parent_native_capped_interface_role_v1',adapter_sha256=sha(__file__),
        role_kernel_sha256=sha(ROOT/'skills/build-cad-pipe-topology/scripts/source_capped_branch_roles.py'),inputs={key:dict(path=str(path),sha256=sha(path)) for key,path in paths.items()},
        output_graph_sha256=sha(gp),proof=proof,hil_ready=False,human_accepted=False)
    (OUT/'source-capped-interface-roles-audit.json').write_bytes(encode(audit))
    print(dict(source_role='UT0192_reserved_capped_interface',nodes=258,edges=264,components=204,remaining_source_terminals=45,nodes_retired=0),flush=True)


if __name__=='__main__':main()
