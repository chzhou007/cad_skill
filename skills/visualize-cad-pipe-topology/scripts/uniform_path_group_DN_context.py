"""Derive a uniform intensive DN from an already qualified whole-path group.

Length is extensive: its unknown child allocation is never copied or divided.
The caller qualifies the immutable parent source comparison and input hashes.
"""
import copy,hashlib,json,math,re,sys
from pathlib import Path
OWNER=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(OWNER)not in sys.path:sys.path.insert(0,str(OWNER))
from attach_anchored_floor_main_attributes import horizontal_domain

MODE='source_checked_uniform_path_group_DN_child_domains_v1'
def valid_hash(value):return isinstance(value,str)and re.fullmatch('[0-9a-f]{64}',value)is not None

def from_artifact(graph_path,rendered_path,policy_path,expected_graph_hash,expected_policy_hash):
    raw=Path(graph_path).read_bytes();policy=Path(policy_path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_graph_hash or hashlib.sha256(policy).hexdigest()!=expected_policy_hash:raise ValueError('source-bound bundle inputs changed')
    return collect(json.loads(raw),expected_graph_hash,hashlib.sha256(Path(rendered_path).read_bytes()).hexdigest(),json.loads(policy),expected_policy_hash,expected_policy_hash)

def collect(graph,graph_hash,rendered_hash,policy,policy_hash,expected_policy_hash):
    if not all(valid_hash(v)for v in(graph_hash,rendered_hash,policy_hash))or policy_hash!=expected_policy_hash:raise ValueError('native group policy or graph binding differs')
    root=graph.get('sourceFullPlanBatchAttributes')
    if not root:return None
    if root.get('mode')!='complete_plan_batch_axis_attribute_composition_v1'or root.get('source_verification_pending')is not False or root.get('human_accepted')is not False:raise ValueError('unqualified complete source group')
    angles=policy['isometric_horizontal_directions_degrees'];edges={e['edge_id']:e for e in graph['edges']};records=[];pending=[];used=set()
    for scope in root['records']:
        if len(scope['iso_edges'])<=1:continue
        try:
            value=scope['plan_drawn_nominal_mm'];rows=scope['plan_DN_records']
            if (scope['kind']!='native_main_chain_between_independent_junctions'or scope['group_scope_not_allocated_to_child_edges']is not True
                or scope['whole_axis_nominal_mm']is not None or scope['whole_installed_length_mm']is not None
                or scope['human_accepted']is not False or scope['related_HIL_confirmation_inherited']is not False):raise ValueError('not a qualified unallocated native main path group')
            if isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0:raise ValueError('path group DN is conflicting or unknown')
            if (len(rows)!=len(scope['plan_edges'])or{r['edge_id']for r in rows}!=set(scope['plan_edges'])
                or any(r['nominal_mm']!=value or not r['lineage']or r['system']!=scope['system']or r['human_accepted']is not False or r['status']in('conflict','unresolved','annotation_blocked','source_scope_unverified')for r in rows)):
                raise ValueError('all independent plan scopes must agree on known DN')
            if len(set(scope['iso_edges']))!=len(scope['iso_edges'])or used.intersection(scope['iso_edges']):raise ValueError('group child repeats a pipe writer')
            domains=[]
            for eid in scope['iso_edges']:
                edge=edges[eid]
                if edge.get('batch_plan_attribute_scopes')!=scope:raise ValueError('group root and child evidence differ')
                if edge.get('axis_riser_attributes')or edge.get('plan_segment_attributes'):raise ValueError('mixed or vertical child attributes need their source stage')
                local=dict(iso_edges=[eid],iso_start=edge['start_node_id'],iso_end=edge['end_node_id'],system=scope['system'],floor=scope['floor'])
                path=horizontal_domain(graph,local,angles)
                domains.append(dict(edge_id=eid,start_node_id=edge['start_node_id'],end_node_id=edge['end_node_id'],scope_paths=[copy.deepcopy(path)]))
            used.update(scope['iso_edges']);records.append(dict(mapping_id=scope['mapping_id'],floor=scope['floor'],system=scope['system'],nominal_mm=value,
                plan_edges=copy.deepcopy(scope['plan_edges']),iso_edges=copy.deepcopy(scope['iso_edges']),source_sha256=copy.deepcopy(scope['source_sha256']),
                graph_sha256=copy.deepcopy(scope['graph_sha256']),plan_DN_receipt_sha256=scope['plan_DN_receipt_sha256'],
                mapping_receipt_sha256=scope['mapping_receipt_sha256'],domains=domains,
                child_length_allocation_known=False,physical_child_lengths_mm=None,human_accepted=False))
        except(ValueError,KeyError)as exc:pending.append(dict(mapping_id=scope['mapping_id'],reason=str(exc)))
    return dict(mode=MODE,source_graph_sha256=graph_hash,rendered_graph_sha256=rendered_hash,source_policy_sha256=policy_hash,
        horizontal_directions_degrees=copy.deepcopy(angles),groups=records,pending=pending,child_DN_domains=len(used),
        scalar_physical_lengths_assigned=0,topology_mutated=False,human_accepted=False)
