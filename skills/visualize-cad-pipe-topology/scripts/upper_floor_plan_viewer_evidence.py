"""Replay upper-floor composition and reuse its freshly verified parent ancestry."""
import copy,hashlib,json,sys
from pathlib import Path


def verify(graph_path,graph):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    orchestrator=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
    if str(orchestrator) not in sys.path:sys.path.insert(0,str(orchestrator))
    from native_replay_session import verify_once
    from attach_upper_floor_plan_attributes import verify_output,ROOT
    from attach_axis_riser_segment_attributes import viewer_ancestry
    graph_path=Path(graph_path);digest=hashlib.sha256(graph_path.read_bytes()).hexdigest();audit=verify_once(graph_path.parent,verify_output)
    if json.loads(graph_path.read_text('utf8'))!=graph or audit['output_graph_sha256']!=digest:
        raise ValueError('upper-floor viewer graph differs from native replay')
    if (audit.get('previous_plan_vertical_and_component_fields_preserved') is not True or audit.get('mixed_edge_whole_values_assigned')!=0
        or audit.get('physical_ports_verified') is not False or audit.get('related_HIL_confirmation_inherited') is not False
        or audit.get('human_accepted') is not False or audit.get('hil_ready') is not False):raise ValueError('upper-floor viewer preservation or scope differs')
    records=audit['records'];rows=[r for e in graph['edges'] for r in e.get('plan_segment_attributes',[])]
    if (len(records)!=4 or len(rows)!=4 or len({r['mapping_id'] for r in rows})!=4
        or {r['mapping_id']:r for r in rows}!={r['mapping_id']:r for r in records}
        or graph.get(ROOT,{}).get('records')!=records):raise ValueError('upper-floor viewer fields differ from native audit')
    named=audit['verified_named_parent'];axis=named['verified_axis_segment_parent']
    ancestor,proof=viewer_ancestry(axis,digest)
    proof['records']+=copy.deepcopy(named['records']);proof['plan_DN_scope_fusion']+=copy.deepcopy(named['plan_DN_scope_fusion'])
    proof.update(named_riser_plan_attribute_audit=named,axis_riser_attribute_parent_graph_path=named['parent_graph']['path'],
        upper_floor_plan_segment_attribute_audit=audit,human_accepted=False,hil_ready=False)
    return ancestor,proof
