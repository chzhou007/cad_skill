"""Replay a plan wave child before its unchanged logical-ownership ancestor."""
import copy,hashlib,json,sys
from pathlib import Path
OWNER=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text('utf-8-sig'))


def check_inherited_wave_graph(root,report,graph_hash,graph_path):
    if str(OWNER) not in sys.path:sys.path.insert(0,str(OWNER))
    from inherited_wave_pair_continuity import verify_output,MODE
    from source_comparison_gate import check,graph_comparison_blockers
    root=Path(root).resolve();graph_path=Path(graph_path).resolve()
    if graph_path.name!='graph_with_edges.json' or graph_path.parent not in (root,root/'topology-inherited-wave-pair-continuity'):
        raise ValueError('inherited wave graph outside declared stage')
    audit=verify_output(graph_path.parent);graph=load(graph_path);scope=graph['sourceInheritedWavePairContinuity']
    parent=Path(audit['inputs']['graph']['path']).resolve();parent_hash=audit['inputs']['graph']['sha256']
    if (audit['mode']!=MODE or audit['output_graph_sha256']!=graph_hash or digest(graph_path)!=graph_hash or digest(parent)!=parent_hash
        or scope.get('input_graph_sha256')!=parent_hash or scope.get('source_sha256')!=audit['inputs']['source']['sha256']
        or scope.get('physical_lengths_assigned')!=0 or scope.get('dependent_mapping_attributes_and_HIL_invalidated') is not True
        or scope.get('human_accepted') is not False or graph.get('metadata',{}).get('hil_ready') is not False):
        raise ValueError('inherited wave source gate evidence or invalidation differs')
    if graph_path.parent!=root:
        stage=load(root/'reports/source-inherited-wave-continuity-stage.json')
        if (stage.get('graph_sha256')!=graph_hash or stage.get('parent_graph_sha256')!=parent_hash
            or stage.get('source_sha256')!=audit['inputs']['source']['sha256'] or stage.get('artifact_directory')!=str(graph_path.parent)
            or stage.get('audit_sha256')!=digest(graph_path.parent/'inherited-wave-receipt.json')
            or stage.get('entry_sha256')!=digest(OWNER/'inherited_wave_family_stage.py') or stage.get('hil_ready') is not False):
            raise ValueError('stale inherited wave family stage receipt')
    parent_root=parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result=copy.deepcopy(check(report,parent_hash,parent_root,parent));result['inherited_wave_parent_comparison']=copy.deepcopy(result)
    previous=result.get('graph_unresolved_node_blockers',[]);current,_=graph_comparison_blockers(graph)
    retired={n['node_id'] for n in scope['retired_node_snapshots']}
    old_ids={n['node_id'] for n in previous};new_ids={n['node_id'] for n in current}
    if not old_ids-new_ids<=retired or new_ids-old_ids:raise ValueError('wave comparison changed an unrelated unresolved node')
    old_message=f'{len(previous)} graph nodes have unresolved source-terminal or equipment-overlap semantics'
    result['pending']=[value for value in result['pending'] if value!=old_message]
    if current:result['pending'].append(f'{len(current)} graph nodes have unresolved source-terminal or equipment-overlap semantics')
    result['graph_unresolved_node_blockers']=current
    result['pending'].append('paired wave drawing continuations checked; dependent inventory, mapping, DN/length attributes, current full source comparison and HIL require revalidation')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,
        inherited_wave_continuity_stage=dict(source_replay='passed',parent_graph_sha256=parent_hash,pairs=audit['proof']['pairs'],
            components=audit['proof']['components'],retired_drawing_nodes=sorted(retired),physical_lengths_assigned=0,
            unrelated_parent_issues_preserved=True,current_full_source_comparison_complete=False,human_accepted=False))
    return result
