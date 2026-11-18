"""Retain qualified horizontal domains inside a partly undetermined axis edge.

The complete two-view range and its uniform floor-plan member must already
have independent source-owner proof. An unknown direction stays unknown; it
does not invalidate other explicitly horizontal source domains in that range.
"""
import copy,math
from confirm_crossview_paths import encode
from axis_unbranched_vertical_DN import chain_evidence,source_key,annotation_index
from compound_member_interfaces import native_label_guard
from pipe_annotation_attributes import contact

MODE='native_uniform_plan_range_partial_horizontal_main_DN_v1'
def require(value,message):
    if not value:raise ValueError(message)

def collect(scope,group,graph,routing,doc,items,caps,existing):
    before=encode(scope),encode(group),encode(graph),encode(routing)
    require(scope['status']=='native_bounded_range_correspondence'and scope['scope_id']==group['scope_id'],
            'independently qualified complete range and same uniform group required')
    nominal=group['nominal_mm'];source_rows=group['remaining_plan_DN_regions']
    require(type(nominal)in(int,float)and math.isfinite(nominal)and nominal>0,'positive independently owned plan DN required')
    require(graph['metadata']['source_sha256']==routing['inputs']['source']['sha256'],'partial-main source/routing binding differs')
    require(source_rows and all(r['nominal_mm']==nominal and r['system']==scope['system']and r['lineage']for r in source_rows),
            'complete independently replayed uniform source-plan DN regions required')
    require(group['scoped_plan_caption_guard']['original_guard_reexecuted']is True
        and group['scoped_plan_caption_guard']['original_thresholds_unchanged']is True
        and group['scoped_plan_caption_guard']['F_and_other_new_DN_guards_retained']is True,
            'original full plan caption/transition guards required')
    owners=group['records'];require(owners and len({r['source_scope_id']for r in owners})==1,'one qualified lower-main domain source required')
    edges={e['edge_id']:e for e in graph['edges']};rows={source_key(r):r for r in routing['records']}
    require(len(rows)==len(routing['records']),'duplicate original direction domains')
    records=[];pending=[];annotation=annotation_index(doc,graph,graph['metadata']['source_sha256'])
    # The first edge is an independently owned higher-member prefix. It must
    # never receive the lower member's DN, even if it has horizontal geometry.
    for eid in scope['views']['iso']['route']['edges'][1:]:
        if eid in existing:continue
        try:
            edge=edges[eid];require(edge['system']==scope['system']and edge['floor_start']==edge['floor_end']==scope['floor'],
                'partial range changes source system or floor')
            expected={(pi,si)for pi,path in enumerate(edge['attribute_paths'])for si in range(len(path)-1)}
            selected=[r for r in routing['records']if r['edge_id']==eid]
            require({(r['path_index'],r['segment_index'])for r in selected}==expected and len(selected)==len(expected),
                    'complete original route population required')
            chains=[];handles=set()
            for pi,path in enumerate(edge['attribute_paths']):
                parts=[rows[eid,pi,si]for si in range(len(path)-1)]
                require(all(r['scope_points']==path[r['segment_index']:r['segment_index']+2]
                    and r['system']==edge['system']and r['floor_start']==r['floor_end']==scope['floor']
                    and r['native_source_status']=='single_source_line_covers'and len(r['native_witnesses'])==1
                    and r['native_witnesses'][0]['scope']=='modelspace'for r in parts),
                    'full partial-edge path needs unchanged unique native source LINEs')
                chain=chain_evidence(parts,None,items);chains.append(chain)
                handles.update(r['native_witnesses'][0]['source_handle']for r in parts)
            guard=native_label_guard(doc,handles,nominal,caps)
            require(not any(contact(a,b,*s['scope_points'])is not None for a,b in annotation['F_strokes']for s in selected),
                    'ordered F leader crosses partial-main source corridor')
            horizontal=[copy.deepcopy(s)for s in selected if s['direction_class']=='horizontal']
            excluded=[dict(copy.deepcopy(s),new_DN_assigned=None,physical_length_mm=None,
                reason='vertical_remains_owned_by11'if s['direction_class']=='vertical'else'original_direction_undetermined_retained')
                for s in selected if s['direction_class']!='horizontal']
            require(bool(horizontal),'no independently classified horizontal domain')
            records.append(dict(axis_edge_id=eid,system=edge['system'],floor=scope['floor'],nominal_mm=nominal,
                axis_nodes=[edge['start_node_id'],edge['end_node_id']],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),
                source_scope_id=owners[0]['source_scope_id'],horizontal_segment_domains=horizontal,
                scope_paths=[s['scope_points']for s in horizontal],whole_horizontal_edge=not excluded,
                excluded_other_direction_domains=excluded,full_native_path_chains=chains,original_axis_caption_guard=guard,
                plan_remaining_edges=[r['edge_id']for r in source_rows],source='native_uniform_plan_range_with_other_direction_domains_retained',
                axis_labels_validation_only=True,physical_length_mm=None,new_vertical_values_assigned=0,
                original_direction_thresholds_unchanged=True,internal_node_identities_assigned=False,human_accepted=False))
        except ValueError as exc:pending.append(dict(axis_edge_id=eid,reason=str(exc)))
    require(before==(encode(scope),encode(group),encode(graph),encode(routing)),'original source group, graph or direction inventory mutated')
    return dict(mode=MODE,records=records,pending=pending,unknown_directions_reclassified=0,physical_lengths_assigned=0,
        vertical_values_assigned=0,individual_node_identities_assigned=0,human_accepted=False)
