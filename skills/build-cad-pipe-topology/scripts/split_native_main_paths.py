"""Split a witnessed main at scoped landing points and conserve inline instances.

Connectivity evidence belongs to the caller. Reuse the existing confirmed-circle
path slicing and native source assignment primitives; never count drawing gaps
as installed length or silently spread parent diameter evidence across children.
"""
import collections,copy,math
from repair_confirmed_circle_junctions import pos,slice_path,segments_for_interval,assign_sources

def split_main(doc,main,rows,cuts,graph_hash,prefix='PAIR',tol=.05):
    if not cuts or len({c['source_handle'] for c in cuts})!=len(cuts):raise ValueError('empty or duplicate main cuts')
    if any(k.startswith('diameter_') or k.startswith('pipe_diameter') or k in ('source_segment_dimensions','physical_length','physical_length_mm') for k in main):
        raise ValueError('parent attributes require explicit remapping before splitting')
    path=main['path'];total=sum(math.dist(a,b) for a,b in zip(path,path[1:]));items=sorted(((pos(path,c['point']),c) for c in cuts),key=lambda item:item[0])
    offsets=[0]+[s for s,_ in items]+[total]
    if any(b-a<=tol for a,b in zip(offsets,offsets[1:])):raise ValueError('overlapping or non-interior cuts')
    tees=['T-'+prefix+'-'+c['source_handle'] for _,c in items]
    ids=[main['edge_id']]+['E-'+prefix+'-'+c['source_handle'] for _,c in items]
    ends=[main['start_node_id']]+tees+[main['end_node_id']];children=[]
    for i,(lo,hi) in enumerate(zip(offsets,offsets[1:])):
        edge=copy.deepcopy(main);edge.update(edge_id=ids[i],start_node_id=ends[i],end_node_id=ends[i+1])
        if i:edge.pop('start_port_id',None)
        if i<len(ids)-1:edge.pop('end_port_id',None)
        edge['path']=slice_path(path,lo,hi);edge['path_points']=copy.deepcopy(edge['path'])
        edge['attribute_paths']=segments_for_interval(path,main['attribute_paths'],lo,hi)
        if not edge['attribute_paths']:raise ValueError('main child lacks native drawing paths')
        edge['path_length']=sum(math.dist(a,b) for p in edge['attribute_paths'] for a,b in zip(p,p[1:]))
        edge['source_handles']=assign_sources(doc,main['source_handles'],edge['attribute_paths'])
        edge['source_flexible_joints']=[f for f in main.get('source_flexible_joints',[]) if all(lo-tol<=pos(path,p)<=hi+tol for p in f['source_contact_points'])]
        if not edge['source_flexible_joints']:edge.pop('source_flexible_joints',None);edge.pop('connection_mode',None)
        edge['equipment_names']=[];edge['equipment_counts']={}
        edge['split_source_edge']=dict(edge_id=main['edge_id'],source_graph_sha256=graph_hash,interval_native_units=[lo,hi])
        children.append(edge)
    assignments=copy.deepcopy(rows)
    for row in assignments:
        if row['edge_id']!=main['edge_id']:continue
        location=pos(path,[float(row['x']),float(row['y'])],tol=5.)
        slots=[i for i,(lo,hi) in enumerate(zip(offsets,offsets[1:])) if lo+tol<location<hi-tol]
        if len(slots)!=1:raise ValueError('component at a cut needs separate ownership evidence')
        edge=children[slots[0]];row['edge_id']=edge['edge_id'];edge['equipment_names'].append(row['device_name'])
        typ=row['equipment_type'];edge['equipment_counts'][typ]=edge['equipment_counts'].get(typ,0)+1
    if collections.Counter(n for e in children for n in e['equipment_names'])!=collections.Counter(main.get('equipment_names',[])):raise ValueError('component conservation failed')
    if abs(sum(e['path_length'] for e in children)-main['path_length'])>tol:raise ValueError('native drawing length not conserved')
    if {h for e in children for h in e['source_handles']}!=set(main['source_handles']):raise ValueError('native source handles not conserved')
    if collections.Counter(f['source_handle'] for e in children for f in e.get('source_flexible_joints',[]))!=collections.Counter(f['source_handle'] for f in main.get('source_flexible_joints',[])):
        raise ValueError('flexible joints lost or duplicated')
    return children,assignments,[(c,t) for (_,c),t in zip(items,tees)]
