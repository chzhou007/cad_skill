"""Read separate native omission endpoints without certifying remote paths.

Reuse the complete original marker/contact owner on actual terminal LINE
slices. A private cut is a reading boundary, never a new physical graph node.
The caller must separately qualify its complete original branch and root T.
"""
import copy,hashlib,math
from confirm_crossview_paths import encode
from crossview_equipment_branch_inventory import index_graph
from inherited_marker_and_crossover_evidence import collect as complete_marker
from native_path_coverage_audit import audit

MODE='native_omission_marker_endpoint_scope_geometry_v1'

def require(value,message):
    if not value:raise ValueError(message)

def endpoint_projection(doc,graph,node_id,source_hash,graph_hash):
    nodes,_,adj=index_graph(graph);node=nodes[node_id]
    require(graph['metadata']['source_sha256']==source_hash,'marker endpoint source binding differs')
    require(node.get('node_type')=='virtual_equipment'and node.get('subtype')=='external_system_interface',
            'typed source drawing interface required')
    projection=dict(metadata=copy.deepcopy(graph['metadata']),nodes=[copy.deepcopy(node)],edges=[])
    bindings=[]
    for edge in adj[node_id]:
        sides=[side for side in('start','end')if edge.get(side+'_node_id')==node_id]
        require(len(sides)==1 and len(edge['attribute_paths'])==1 and len(edge['attribute_paths'][0])>=3,
                'one actual marker endpoint on one source path required')
        side=sides[0];path=edge['attribute_paths'][0]
        original_display=0 if side=='start'else len(path)-2
        physical_index=1 if side=='start'else len(path)-3
        coverage=audit(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=[edge['edge_id']]),source_hash,graph_hash)
        physical=coverage['edges'][0]['segments'][physical_index]
        require(physical['status']=='single_source_line_covers'and len(physical['witnesses'])==1
            and physical['witnesses'][0]['scope']=='modelspace','terminal endpoint needs one actual native LINE')
        sliced=copy.deepcopy(edge);sliced['attribute_paths']=[copy.deepcopy(path[:3]if side=='start'else path[-3:])]
        opposite='end'if side=='start'else'start';cut='READING-PORT-CUT:'+node_id+':'+edge['edge_id']
        require(cut not in nodes,'reserved nonphysical reading boundary collides with an actual node')
        sliced[opposite+'_node_id']=cut;sliced.pop(opposite+'_port_id',None);sliced.pop(opposite+'_boundary_id',None)
        point=sliced['attribute_paths'][0][-1 if side=='start'else 0]
        projection['nodes'].append(dict(node_id=cut,node_type='virtual_equipment',subtype='nonphysical_source_reading_cut',
            floor=node.get('floor'),x=point[0],y=point[1],physical_connection_claimed=False))
        projection['edges'].append(sliced)
        bindings.append(dict(edge_id=edge['edge_id'],original_display_segment_index=original_display,
            original_physical_segment_index=physical_index,original_branch_paths=copy.deepcopy(edge['attribute_paths']),
            endpoint_slice_paths=copy.deepcopy(sliced['attribute_paths']),native_endpoint_LINE=copy.deepcopy(physical),
            reading_cut_node=cut,original_far_node=edge.get(opposite+'_node_id')))
    require(len(projection['edges'])==len(node.get('ports',[])),'complete independent marker port cohort required')
    projection['endpointReadingProjection']=dict(mode=MODE,original_graph_sha256=graph_hash,
        source_marker_node=node_id,full_branch_paths_qualified=False,physical_nodes_created=0,physical_lengths_assigned=0)
    return projection,bindings

def collect(doc,graph,node_id,source_hash,graph_hash,pop):
    before=encode(graph)
    try:
        # Preserve the previous complete owner byte for byte whenever it passes.
        return complete_marker(doc,graph,node_id,source_hash,graph_hash,pop)
    except ValueError as original_error:
        failure=str(original_error)
    projection,bindings=endpoint_projection(doc,graph,node_id,source_hash,graph_hash)
    projection_hash=hashlib.sha256(encode(projection)).hexdigest()
    # The unchanged owner still checks the original complete source endpoint
    # population, finite marker strokes, both systems and the original30-unit
    # drawing-boundary calibration; no path repair or tolerance relaxation.
    proof=complete_marker(doc,projection,node_id,source_hash,projection_hash,pop)
    indexed={r['edge_id']:r for r in bindings};records=[]
    for original in proof['records']:
        row=copy.deepcopy(original);binding=indexed[row['edge_id']]
        row['display_segment_index']=binding['original_display_segment_index']
        row['endpoint_slice_native_path_coverage']=row.pop('native_path_coverage')
        row.pop('physical_segments',None)
        row.update(endpoint_slice_source_binding=copy.deepcopy(binding),full_original_branch_path_qualified=False,
            source_reading_projection_sha256=projection_hash,scope='native_marker_endpoint_geometry_only')
        records.append(row)
    require(encode(graph)==before,'original graph mutated by endpoint reading projection')
    return dict(mode=MODE,node_id=node_id,source_marker_handle=proof['source_marker_handle'],marker_vertices=proof['marker_vertices'],
        records=records,complete_original_marker_endpoint_population_replayed=True,original_complete_path_failure=failure,
        original_graph_sha256=graph_hash,source_reading_projection_sha256=projection_hash,source_reading_projection=projection,
        full_original_branch_paths_qualified=False,root_T_or_remote_equipment_qualified=False,
        common_marker_creates_pipe_connection=False,remote_destination_or_cap_role_assigned=False,
        graph_mutated=False,physical_nodes_created=0,physical_values_assigned=0,human_accepted=False)
