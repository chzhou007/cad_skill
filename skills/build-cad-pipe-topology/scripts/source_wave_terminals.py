"""Source-calibrated transverse spline end marks, never hydraulic curves.

Recognize a repeated native spline form through a unique degree-one pipe ray.
No edge, endpoint, service, port identity or remote connection is changed.
"""
import collections
import copy
import math
from ezdxf.math import BSpline


def normalized_form(entity):
    controls=[list(p)[:2]for p in entity.control_points]
    if len(controls)<2 or len(entity.weights)>0:
        return None
    a,b=controls[0],controls[-1];length=math.dist(a,b)
    if length<=0:return None
    u=[(b[i]-a[i])/length for i in(0,1)];v=[-u[1],u[0]]
    points=[[sum((p[i]-a[i])*axis[i]for i in(0,1))/length for axis in(u,v)]for p in controls]
    knots=list(entity.knots);span=knots[-1]-knots[0]
    if span<=0:return None
    knots=[(x-knots[0])/span for x in knots]
    variants=[(points,knots),([[p[0],-p[1]]for p in points],knots),
              ([[1-p[0],p[1]]for p in reversed(points)],[1-x for x in reversed(knots)]),
              ([[1-p[0],-p[1]]for p in reversed(points)],[1-x for x in reversed(knots)])]
    coords,knots=min(variants,key=lambda form:tuple(round(x,6)for p in form[0]for x in p)+tuple(round(x,6)for x in form[1]))
    return {'control_points':coords,'knots':knots,'degree':entity.dxf.degree,'chord_length':length,'chord_direction':u}


def form_matches(form,prototype,tolerance):
    return (form['degree']==prototype['degree']and len(form['control_points'])==len(prototype['control_points'])
            and len(form['knots'])==len(prototype['knots'])
            and max(math.dist(a,b)for a,b in zip(form['control_points'],prototype['control_points']))<=tolerance
            and max(abs(a-b)for a,b in zip(form['knots'],prototype['knots']))<=tolerance)


def line_curve_contacts(point,outward,curve,tolerance):
    """Intersections with the actual tessellated native curve, deduplicated."""
    hits=[]
    for a,b in zip(curve,curve[1:]):
        v=[b[i]-a[i]for i in(0,1)];den=outward[0]*v[1]-outward[1]*v[0]
        if abs(den)<1e-12:continue
        delta=[a[i]-point[i]for i in(0,1)]
        t=(delta[0]*v[1]-delta[1]*v[0])/den
        s=(delta[0]*outward[1]-delta[1]*outward[0])/den
        if not -1e-8<=s<=1+1e-8:continue
        p=[point[i]+t*outward[i]for i in(0,1)]
        if not any(math.dist(p,h['point'])<=tolerance for h in hits):hits.append({'point':p,'outward_distance':t})
    return hits


def segment_distance(p,a,b):
    v=[b[i]-a[i]for i in(0,1)];den=sum(x*x for x in v)
    t=max(0.,min(1.,sum((p[i]-a[i])*v[i]for i in(0,1))/den))if den else 0.
    return math.dist(p,[a[i]+t*v[i]for i in(0,1)])


def native_terminal_rays(doc,node,tolerance):
    point=[node['x'],node['y']];rays=[]
    for handle in node.get('source_handles',[]):
        if handle not in doc.entitydb:continue
        entity=doc.entitydb[handle];kind=entity.dxftype()
        if kind=='LINE':points=[list(entity.dxf.start)[:2],list(entity.dxf.end)[:2]]
        elif kind=='LWPOLYLINE'and not entity.closed and not any(abs(p[4])>1e-10 for p in entity.get_points()):
            points=[list(p)[:2]for p in entity.vertices_in_wcs()]
        else:continue
        if len(points)<2:continue
        for a,b in((points[0],points[1]),(points[-1],points[-2])):
            if math.dist(point,a)>tolerance or math.dist(a,b)<=tolerance:continue
            size=math.dist(a,b);direction=[(a[i]-b[i])/size for i in(0,1)]
            if not any(math.dist(direction,r['direction'])<1e-6 for r in rays):
                rays.append({'direction':direction,'source_handle':handle,'native_endpoint':a,'native_tail':b})
    return rays


def reconcile(doc,graph,profile,prior=None):
    if not profile.get('readability_verified')or not profile.get('calibration_evidence'):
        raise ValueError('Native wave terminal profile needs readable source calibration')
    if profile['maximum_terminal_gap_chord_ratio']>.05:
        raise ValueError('Wave terminal clearance must be locally bounded')
    out=copy.deepcopy(graph);incident=collections.defaultdict(list);prior_nodes={n['node_id']:n for n in(prior or{}).get('nodes',[])}
    for edge in out['edges']:
        for side in('start','end'):incident[edge[side+'_node_id']].append((edge,side))
    terminals=[n for n in out['nodes']if n['node_type']=='virtual_equipment'and len(incident[n['node_id']])==1]
    candidates=[];glyphs=[];tol=profile['contact_tolerance']
    for entity in doc.modelspace().query('SPLINE'):
        if entity.dxf.layer not in profile['source_layers']:continue
        form=normalized_form(entity)
        if form is None:
            candidates.append({'source_handle':entity.dxf.handle,'source_layer':entity.dxf.layer,'status':'pending_unrecognized_source_spline_form'});continue
        prototype=next((p for p in profile['shape_prototypes']if form_matches(form,p,profile['maximum_shape_error'])),None)
        if prototype is None:
            candidates.append({'source_handle':entity.dxf.handle,'source_layer':entity.dxf.layer,'status':'pending_unrecognized_source_spline_form'});continue
        points=[list(p)[:2]for p in entity.construction_tool().approximate(profile.get('curve_samples',400))]
        length=form['chord_length'];gap=length*profile['maximum_terminal_gap_chord_ratio']
        bb=[min(p[0]for p in points)-gap,min(p[1]for p in points)-gap,max(p[0]for p in points)+gap,max(p[1]for p in points)+gap]
        row={'source_handle':entity.dxf.handle,'source_layer':entity.dxf.layer,'shape_id':prototype['id'],
             'status':'pending_no_unique_source_pipe_ray','candidate_nodes':[],'source_curve_points':points}
        # A real curved pipe or crossover has owning tails at its curve ends.
        end_edges={e['edge_id']for e in out['edges']for path in e['attribute_paths']for a,b in zip(path,path[1:])
                   if min(segment_distance(p,a,b)for p in(points[0],points[-1]))<=tol}
        if end_edges:
            row.update(status='rejected_curve_endpoint_pipe_contacts',curve_endpoint_edge_ids=sorted(end_edges));candidates.append(row);continue
        matches=[]
        for node in terminals:
            p=[node['x'],node['y']]
            if not(bb[0]<=p[0]<=bb[2]and bb[1]<=p[1]<=bb[3]):continue
            edge,side=incident[node['node_id']][0];path=edge['path_points']if side=='start'else list(reversed(edge['path_points']))
            tail=next((q for q in path[1:]if math.dist(q,p)>tol),None)
            if tail is None:continue
            rays=native_terminal_rays(doc,node,tol)
            if len(rays)!=1:continue
            outward=rays[0]['direction']
            norm=math.dist(p,tail);logical_outward=[(p[i]-tail[i])/norm for i in(0,1)]
            if sum(outward[i]*logical_outward[i]for i in(0,1))<.999999:continue
            if abs(sum(outward[i]*form['chord_direction'][i]for i in(0,1)))>profile['maximum_tail_chord_alignment']:continue
            layers={doc.entitydb[h].dxf.layer for h in node.get('source_handles',[])if h in doc.entitydb}
            if layers!={entity.dxf.layer}:continue
            hits=line_curve_contacts(p,outward,points,tol)
            if len(hits)!=1:continue
            hit=hits[0]
            if abs(hit['outward_distance'])>gap:continue
            if min(math.dist(hit['point'],end)for end in(points[0],points[-1]))<length*profile['minimum_contact_end_fraction']:continue
            matches.append({'node_id':node['node_id'],'edge_id':edge['edge_id'],'source_pipe_handles':node['source_handles'],
                            'native_terminal':p,'curve_intersection':hit['point'],'terminal_to_glyph_distance':abs(hit['outward_distance']),
                            'signed_outward_distance':hit['outward_distance'],'source_layer':entity.dxf.layer,
                            'native_endpoint_witness':rays[0]})
        row['candidate_nodes']=matches
        if len(matches)==1:
            row['status']='qualified_native_transverse_wave_terminal'
        candidates.append(row)
    owners=collections.defaultdict(list)
    for row in candidates:
        if row['status']=='qualified_native_transverse_wave_terminal':owners[row['candidate_nodes'][0]['node_id']].append(row)
    nodes={n['node_id']:n for n in out['nodes']}
    for row in candidates:
        if row['status']!='qualified_native_transverse_wave_terminal':continue
        contact=row['candidate_nodes'][0]
        if len(owners[contact['node_id']])!=1:
            row['status']='pending_competing_source_wave_markers';continue
        node=nodes[contact['node_id']];key='WAVE-'+row['source_handle'];prior_node=prior_nodes.get(node['node_id'],{})
        destination=node.get('interface_destination')or prior_node.get('interface_destination')
        node.setdefault('source_terminal_glyph_ids',[]).append(key)
        evidence={k:v for k,v in row.items()if k not in('source_curve_points','candidate_nodes')};evidence.update(contact)
        node['source_glyph_evidence']=evidence
        if not destination:
            node.update(subtype='native_transverse_wave_interface',boundary_type='source_native_wave_terminal',
                        label='Source wavy end-mark interface '+node['node_id'],interface_kind_zh='原图横向波形管端标识',
                        resolution_state='source_boundary_identified_remote_continuation_not_shown',review_queue='source_boundary_inventory',
                        review_required=False,remote_continuation_confirmed=False)
        row['status']='applied_source_glyph_role_only'
        glyphs.append({'id':key,'source_handles':[row['source_handle']],'node_id':node['node_id'],
                       'edge_id':contact['edge_id'],'floor':prior_node.get('floor',node['floor']),'system':node['system'],
                       'kind':'native_transverse_wave_terminal','source_paths':[{'points':row['source_curve_points'],'fill':False}],
                       'role':'Source drawing end mark; neither a physical curved pipe nor a hydraulic connection.',
                       'native_terminal':contact['native_terminal'],'terminal_to_glyph_distance':contact['terminal_to_glyph_distance'],
                       'known_destination_preserved':bool(destination),'remote_continuation_confirmed':False})
    if glyphs:out['sourceTerminalGlyphs']=glyphs
    return out,{'source_family':'native_transverse_spline_end_marks','candidates':candidates,'glyphs':glyphs,
                'source_curves':len(candidates),'represented_glyphs':len(glyphs),
                'known_destinations_preserved':sum(g['known_destination_preserved']for g in glyphs),
                'hydraulic_paths_unchanged':True,'remote_links_inferred':0}
