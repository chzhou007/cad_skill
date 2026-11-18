"""Formal source-comparison entry for preserved SH16 project descendants.

The core dispatcher remains unchanged until the active viewer build finishes.
This explicit entry replays actual project assets before the original ancestor.
"""
import argparse,copy,sys
from pathlib import Path
S=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(S) not in sys.path:sys.path.insert(0,str(S))
from confirm_crossview_paths import load,sha,encode
from project_scoped_graph_descendants import verify_output,kind


def check_project_descendant(root,report,graph_path,mapping_path=None,mapping_sha256=None):
    from source_comparison_gate import check as check_ancestor,graph_comparison_blockers
    root=Path(root).resolve();graph_path=Path(graph_path).resolve()
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json':raise ValueError('project descendant graph outside exact declared directory')
    graph=load(graph_path);native=verify_output(root,mapping_path,mapping_sha256)
    if native['current_graph_sha256']!=sha(graph_path):raise ValueError('project descendant changed during native replay')
    parent=Path(native['parent_graph']);parent_graph=load(parent)
    if 'sourceSH16RelatedCornerKnownIssue' in parent_graph or 'sourceDeclaredCappedBranchInterfaces' in parent_graph:
        previous=check_project_descendant(parent.parent,report,parent,mapping_path,mapping_sha256)
    else:
        parent_root=parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
        previous=check_ancestor(report,sha(parent),parent_root,parent)
    result=copy.deepcopy(previous);old=previous.get('graph_unresolved_node_blockers',[]);current,_=graph_comparison_blockers(graph)
    old_ids={row['node_id'] for row in old};new_ids={row['node_id'] for row in current};allowed=set(native['disposed_node_ids'])
    if old_ids-new_ids!=allowed or new_ids-old_ids:raise ValueError('project descendant disposed unrelated source-terminal work')
    result['project_scoped_parent_comparison']=copy.deepcopy(previous)
    message=f'{len(old)} graph nodes have unresolved source-terminal or equipment-overlap semantics'
    result['pending']=[value for value in result.get('pending',[]) if value!=message]
    if current:result['pending'].append(f'{len(current)} graph nodes have unresolved source-terminal or equipment-overlap semantics')
    pending='project-scoped source changes require versioned mapping/attribute receipts and related HIL reconciliation; selected unchanged paths do not rebind old receipts'
    if pending not in result['pending']:result['pending'].append(pending)
    result.update(status='failed' if result.get('errors') else 'pending',graph_sha256=sha(graph_path),hil_ready=False,human_accepted=False,
        graph_unresolved_node_blockers=current,project_scoped_descendant_stage=dict(kind=native['kind'],source_replay='passed',
            parent_graph_sha256=sha(parent),owner_asset_sha256=native['owner_asset_sha256'],disposed_node_ids=sorted(allowed),
            nodes_retired=0 if native['kind']=='capped_roles' else len(allowed),connections_added=0,physical_lengths_assigned=0,
            source_role_node_ids_retained=native['kind']=='capped_roles',new_human_confirmation=False,
            mapping_snapshot_scope=native.get('current_mapping_snapshot_scope'),source_verifier_sha256=sha(S/'project_scoped_graph_descendants.py'),
            comparison_entry_sha256=sha(__file__),whole_source_comparison_complete=False))
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('graph','report','mapping','output'):parser.add_argument('--'+key,type=Path,required=key in ('graph','report','output'))
    parser.add_argument('--mapping-sha256');args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=check_project_descendant(args.graph.parent,load(args.report),args.graph,args.mapping,args.mapping_sha256)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(encode(result))
    print(dict(source_replay=result['project_scoped_descendant_stage']['source_replay'],errors=len(result['errors']),
        unresolved_source_terminals=len(result['graph_unresolved_node_blockers']),hil_ready=False),flush=True)
    if result['errors']:raise SystemExit(1)


if __name__=='__main__':main()
