"""Compare lower-floor additions against the exact complete upper-floor parent."""
import copy,hashlib,json,sys
from pathlib import Path


def check_lower_floor_plan_attribute_graph(root,report,graph_hash,graph_path):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_lower_floor_plan_attributes import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve()
    # Deliberately uncached root: its two independently cached children recheck
    # their complete read closures on every call.
    audit=verify_output(root)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:
        raise ValueError('lower-floor fusion outside verified output')
    if (audit.get('previous_plan_vertical_and_component_fields_preserved') is not True
        or audit.get('mixed_edge_whole_values_assigned')!=0 or audit.get('physical_ports_verified') is not False
        or audit.get('related_HIL_confirmation_inherited') is not False or audit.get('human_accepted') is not False
        or audit.get('hil_ready') is not False or audit.get('added_segment_attribute_scopes')!=4
        or len(audit.get('complete_main_centerline_route_edges',[]))!=2):raise ValueError('lower-floor fusion preservation or extent differs')
    parent=Path(audit['parent_graph']['path']);parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('lower-floor parent changed')
    cached=parent.parent/'source-comparison-gate.json';previous=json.loads(cached.read_text('utf8'))
    if previous.get('graph_sha256')!=parent_hash or report!=previous or not isinstance(previous.get('errors'),list) or not isinstance(previous.get('pending'),list):
        raise ValueError('lower-floor comparison needs exact complete parent context')
    result=copy.deepcopy(previous)
    result['pending'].append('Lower-floor plan values cover only checked original axis prefixes and horizontal mains; other interfaces, unseen connections, explicit vertical physical lengths, whole-drawing comparison and human acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        lower_floor_plan_segment_attribute_stage=dict(source_replay='passed',segment_scopes=4,added_axis_edges=audit['added_axis_edges'],
            records=audit['records'],complete_main_centerline_route_edges=audit['complete_main_centerline_route_edges'],
            source_scope_sha256=audit['source_scope_sha256'],mapping_sha256=audit['mapping_sha256'],prior_graph_sha256=parent_hash,
            prior_graph_comparison_sha256=hashlib.sha256(cached.read_bytes()).hexdigest(),
            previous_plan_vertical_and_component_fields_preserved=True,mixed_edge_whole_values_assigned=0,human_accepted=False))
    return result
