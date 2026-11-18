"""Consume wave/main cohort before retained reviewed-owner ancestry."""
import copy
from pathlib import Path
import sys


def check(root,report,graph_hash,graph_path):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from reconstruct_wave_main_cohorts import verify_output,MODE
    from wave_main_cohort_stage import DESTINATION,STAGE
    from confirm_crossview_paths import load,sha
    from source_comparison_gate import check as parent_check,graph_comparison_blockers
    root,path=Path(root).resolve(),Path(graph_path).resolve()
    if path.name!='graph_with_edges.json' or path.parent not in (root,root/DESTINATION):
        raise ValueError('wave cohort graph outside declared stage')
    audit=verify_output(path.parent);graph=load(path);scope=graph['sourceWaveMainCohort']
    parent=Path(audit['inputs']['graph']['path']);ph=audit['inputs']['graph']['sha256']
    if (audit['mode']!=MODE or sha(path)!=graph_hash or audit['output_graph_sha256']!=graph_hash or sha(parent)!=ph
        or scope.get('input_graph_sha256')!=ph or scope.get('human_accepted') is not False
        or scope.get('physical_lengths_assigned')!=0 or scope.get('supply_return_independent') is not True
        or graph.get('metadata',{}).get('hil_ready') is not False):raise ValueError('wave cohort source evidence or invalidation differs')
    if path.parent!=root:
        stage=load(root/STAGE)
        if (stage.get('graph_sha256')!=graph_hash or stage.get('parent_graph_sha256')!=ph
            or stage.get('audit_sha256')!=sha(path.parent/'wave-main-cohort-audit.json')
            or stage.get('entry_sha256')!=sha(owner/'wave_main_cohort_stage.py') or stage.get('hil_ready') is not False):
            raise ValueError('wave cohort family receipt differs')
    result=copy.deepcopy(parent_check(report,ph,parent.parent,parent))
    result['wave_main_cohort_parent_comparison']=copy.deepcopy(result)
    if result['errors']:
        result.update(status='failed',graph_sha256=graph_hash,human_accepted=False,hil_ready=False,
            wave_main_cohort_stage=dict(source_replay='passed',parent_comparison_failed=True))
        return result
    old=result.get('graph_unresolved_node_blockers',[]);current,_=graph_comparison_blockers(graph)
    retired={r['node_id'] for r in scope['retired_terminal_snapshots']}
    before_ids={r['node_id'] for r in old};after_ids={r['node_id'] for r in current}
    if not before_ids-after_ids<=retired or after_ids-before_ids:
        raise ValueError('wave cohort changed unrelated unresolved nodes')
    message=f'{len(old)} graph nodes have unresolved source-terminal or equipment-overlap semantics'
    result['pending']=[m for m in result['pending'] if m!=message]
    if current:result['pending'].append(f'{len(current)} graph nodes have unresolved source-terminal or equipment-overlap semantics')
    result['graph_unresolved_node_blockers']=current
    result['pending'].append('paired wave-main connections source-checked; inventory, cross-view paths, DN/length and HIL require recomputation')
    result.update(status='pending',graph_sha256=graph_hash,human_accepted=False,hil_ready=False,
        wave_main_cohort_stage=dict(source_replay='passed',parent_graph_sha256=ph,
            connections=len(scope['records']),equipment=len({r['equipment_id'] for r in scope['records']}),
            retired_drawing_terminals=sorted(retired),unrelated_parent_issues_preserved=True,physical_lengths_assigned=0,whole_source_comparison_complete=False))
    return result
