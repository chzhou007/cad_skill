"""Reanchor omitted projected branches at isolated header circles.

Three independent branch roles and complete component conservation must explain
the split. A circle, slash DN or a matching component count alone is insufficient.
"""
import copy,hashlib,math
from collections import Counter
from confirm_crossview_paths import encode
from native_inline_coordinates import ball_valve_anchor,balancing_valve_anchor
from native_line_path_evidence import LAYERS,_on
from crossview_equipment_branch_inventory import index_graph,native_tee
from batch_native_path_coverage import collect as coverage
from compound_member_interfaces import declaration

MODE='native_compound_riser_header_member_reconstruction_v1'
ALIASES={'球阀':'ball_valve','平衡阀':'balancing_valve','金属软接':'flexible_joint'}
def profile(rows):return Counter(ALIASES.get(r['equipment_type'],r['equipment_type'])for r in rows)
def oriented(edge,start):
    paths=copy.deepcopy(edge['attribute_paths'])
    if edge['start_node_id']==start:return paths
    if edge['end_node_id']==start:return [list(reversed(p))for p in reversed(paths)]
    raise ValueError('path does not start at requested interface')

def split_and_allocate(header,stub,departure,old_main,circle,components,centers,axis_profiles):
    toward=oriented(header,old_main)
    if len(toward)!=1 or len(toward[0])!=2:raise ValueError('single native header arm required')
    corner,gate=toward[0];den=sum((corner[i]-gate[i])**2 for i in(0,1))
    if not den or not _on(circle,gate,corner,.05)or min(math.dist(circle,gate),math.dist(circle,corner))<=.05:raise ValueError('circle must be strictly inside header')
    parameter=lambda p:sum((p[i]-gate[i])*(corner[i]-gate[i])for i in(0,1))/den
    cut=parameter(circle);left=[];right=[];upper=[];lower=[];all_ids=[]
    for row in components:
        if row['edge_id']not in{header['edge_id'],stub['edge_id'],departure['edge_id']}:continue
        name=row['device_name'];all_ids.append(name)
        if row['edge_id']==stub['edge_id']:upper.append(row);continue
        if row['edge_id']==departure['edge_id']:lower.append(row);continue
        if name not in centers:raise ValueError('header component lacks complete native family anchor')
        t=parameter(centers[name])
        if not 0<=t<=1 or abs(t-cut)*math.sqrt(den)<=.05:raise ValueError('component position cannot select a header side')
        (left if t<cut else right).append(row)
    if len(set(all_ids))!=len(all_ids):raise ValueError('duplicate scoped component identity')
    if profile(left)!=Counter(axis_profiles['approach']):raise ValueError('approach component profile differs')
    need_u=Counter(axis_profiles['riser']);need_l=Counter(axis_profiles['departure'])
    if profile(upper)-need_u or profile(lower)-need_l:raise ValueError('existing branch components exceed axis profile')
    need_u.subtract(profile(upper));need_l.subtract(profile(lower))
    if +need_u + +need_l !=profile(right):raise ValueError('native member component populations differ')
    for row in right:
        kind=ALIASES.get(row['equipment_type'],row['equipment_type'])
        if need_u[kind]>0 and need_l[kind]>0:raise ValueError('component identity allocation is not unique')
        target=upper if need_u[kind]>0 else lower;target.append(row)
    paths=dict(approach=[[gate,circle]],riser=[[circle,corner]]+oriented(stub,old_main),departure=[[circle,corner]]+oriented(departure,old_main))
    allocation=dict(approach=left,riser=upper,departure=lower)
    if sorted(r['device_name']for rows in allocation.values()for r in rows)!=sorted(all_ids):raise ValueError('member component conservation failed')
    return dict(paths=paths,components=allocation,component_ids_conserved=sorted(all_ids),raw_graph_edges_replaced=[header['edge_id'],stub['edge_id'],departure['edge_id']])

def reconstruct(plan_doc,axis_doc,plan,axis,plan_components,axis_components,roles,risks,caption_pairs,hashes):
    pn,pe,padj=index_graph(plan);an,ae,aadj=index_graph(axis);records=[];pending=[]
    for role in roles:
        try:
            system=role['system'];floor=role['floor'];p=role['plan'];a=role['iso'];old=p['main_node'];riser=p['interface_node'];stub=pe[p['branch_edge']]
            if pn[riser].get('subtype')!='out_of_plane_riser'or len(padj[riser])!=1 or len(padj[old])!=3:raise ValueError('native plan riser roles differ')
            if len(aadj[a['main_node']])!=3 or len(aadj[a['interface_node']])!=3:raise ValueError('axis tee/riser degree differs')
            vertical=[e for e in aadj[a['interface_node']]if e['edge_id']!=a['branch_edge']]
            far=[an[e['end_node_id']if e['start_node_id']==a['interface_node']else e['start_node_id']]['floor']for e in vertical]
            if not min(far)<floor<max(far):raise ValueError('axis riser lacks two-sided interfloor continuity')
            candidates=[]
            for e in padj[old]:
                peer=e['end_node_id']if e['start_node_id']==old else e['start_node_id']
                if e['edge_id']==stub['edge_id']or peer not in role['known_gate_mapping']:continue
                axgate=role['known_gate_mapping'][peer];links=[x for x in aadj[a['main_node']]if axgate in(x['start_node_id'],x['end_node_id'])]
                corridors=[c for c in risks['corridors']if c['system']==system and c['source_LINE']in e.get('source_handles',[])]
                if len(links)==1 and len(corridors)==1:candidates.append((e,links[0],corridors[0],peer,axgate))
            if len(candidates)!=1:raise ValueError('one known-gate compound header required')
            header,approach,corridor,gate,axgate=candidates[0];line=plan_doc.entitydb[corridor['source_LINE']];hp=header['attribute_paths']
            if len(hp)!=1 or len(hp[0])!=2:raise ValueError('unsupported bent compound header')
            circles=[c for c in plan_doc.modelspace().query('CIRCLE')if tuple(c.dxf.extrusion)==(0.,0.,1.)and abs(c.dxf.center.z-line.dxf.start.z)<.05 and _on(list(c.dxf.center)[:2],hp[0][0],hp[0][1],.05)and min(math.dist(list(c.dxf.center)[:2],v)for v in hp[0])>c.dxf.radius and not any(math.dist(list(c.dxf.center)[:2],[n['x'],n['y']])<=.05 for n in pn.values())]
            if len(circles)!=1:raise ValueError('isolated native circle is missing or ambiguous')
            circle=circles[0];cp=list(circle.dxf.center)[:2];departure=next(e for e in padj[old]if e['edge_id']not in{header['edge_id'],stub['edge_id']});axis_departure=next(e for e in aadj[a['main_node']]if e['edge_id']not in{approach['edge_id'],a['branch_edge']})
            axes=dict(approach=approach,riser=ae[a['branch_edge']],departure=axis_departure)
            if any(e['system']!=system for e in[header,stub,departure,*axes.values()]):raise ValueError('member reconstruction mixes services')
            profiles={k:profile([r for r in axis_components if r['edge_id']==e['edge_id']])for k,e in axes.items()};centers={}
            for row in plan_components:
                if row['edge_id']!=header['edge_id']:continue
                ent=plan_doc.entitydb.get(row.get('source_handle'));kind=ALIASES.get(row['equipment_type'],row['equipment_type'])
                anchor=ball_valve_anchor(ent)if ent is not None and kind=='ball_valve'else balancing_valve_anchor(ent)if ent is not None and kind=='balancing_valve'else None
                if anchor is None:raise ValueError('header component signature unsupported')
                centers[row['device_name']]=anchor['center']
            split=split_and_allocate(header,stub,departure,old,cp,plan_components,centers,profiles)
            native_t={n:native_tee(axis_doc,axis,n,hashes['axis_source'],hashes['axis_graph'])for n in(a['main_node'],a['interface_node'],axgate)}
            native_axis=coverage(axis_doc,axis,[e['edge_id']for e in axes.values()],hashes['axis_source'],hashes['axis_graph'])
            native_plan=coverage(plan_doc,plan,split['raw_graph_edges_replaced'],hashes['plan_source'],hashes['plan_graph'])
            for proof in(native_axis,native_plan):
                if any(s['status']!='single_source_line_covers'or len(s['witnesses'])!=1 for e in proof['edges']for s in e['segments']):raise ValueError('native path ownership is not unique')
            observations=[o for pair in caption_pairs['pairs']for o in pair['observations']];members={}
            for kind,e in axes.items():
                handles={s['witnesses'][0]['source_handle']for audit in native_axis['edges']if audit['edge_id']==e['edge_id']for s in audit['segments']};obs=[o for o in observations if o['native_pipe']['source_LINE']in handles and o['native_pipe']['system']==system]
                if len(obs)!=1:raise ValueError('independent member caption is missing or ambiguous')
                dn,decl=declaration(corridor,obs[0]['text']['literal_level_key'])
                if dn!=obs[0]['text']['nominal_mm']:raise ValueError('member declaration and axis caption conflict')
                members[kind]=dict(nominal_mm=dn,literal_level_key=obs[0]['text']['literal_level_key'],plan_declarations=decl,axis_caption_crosscheck=obs[0])
            if members['approach']['literal_level_key']!=members['riser']['literal_level_key']or members['riser']['literal_level_key']==members['departure']['literal_level_key']:raise ValueError('upper/lower member literal roles differ')
            scope='MEMBER-RISER:'+hashlib.sha256(encode([hashes['plan_source'],system,floor,circle.dxf.handle])).hexdigest()[:16]
            nodes=[dict(node_id=scope+':'+k,source_node_id=v,x=pt[0],y=pt[1],system=system,floor=floor,node_type='tee'if k=='tee'else'member_boundary')for k,v,pt in[('gate',gate,[pn[gate]['x'],pn[gate]['y']]),('tee',None,cp),('riser',riser,[pn[riser]['x'],pn[riser]['y']]),('departure',departure['end_node_id']if departure['start_node_id']==old else departure['start_node_id'],split['paths']['departure'][-1][-1])]]
            ends=dict(approach=('gate','tee'),riser=('tee','riser'),departure=('tee','departure'));edges=[]
            for kind,paths in split['paths'].items():
                aa,bb=ends[kind];sources=[header]if kind=='approach'else[header,stub]if kind=='riser'else[header,departure]
                edges.append(dict(edge_id=scope+':'+kind,start_node_id=scope+':'+aa,end_node_id=scope+':'+bb,system=system,attribute_paths=paths,source_handles=sorted({h for e in sources for h in e.get('source_handles',[])}),connection_mode='member_reconstruction_anchor_revalidation_pending',member=members[kind],component_ids=[r['device_name']for r in split['components'][kind]],candidate_axis_edge=axes[kind]['edge_id']if kind!='departure'else None,installed_length_mm=None,unshown_connection_length_mm=None))
            records.append(dict(floor=floor,system=system,scope_id=scope,source_circle=dict(handle=circle.dxf.handle,center=cp,radius=circle.dxf.radius,layer=circle.dxf.layer,foreign_annotation_layer=circle.dxf.layer!=line.dxf.layer),old_graph_main_node=old,new_axis_tee=a['main_node'],scoped_graph=dict(nodes=nodes,edges=edges),component_ids_conserved=split['component_ids_conserved'],source_edges=split['raw_graph_edges_replaced'],native_axis_T_evidence=native_t,native_path_evidence=dict(plan=native_plan,axis=native_axis),gate_mapping_revalidation_required=True,lower_terminal_identity_selected=False,whole_axis_values_assigned=0,human_accepted=False))
        except (ValueError,KeyError,StopIteration)as exc:pending.append(dict(floor=role['floor'],system=role['system'],reason=str(exc)))
    return dict(mode=MODE,records=records,pending=pending,scoped_member_edges=sum(len(r['scoped_graph']['edges'])for r in records),conditional_interval_candidates=2*len(records),raw_graphs_unchanged=True,original_graph_T_not_used_as_final_member_T=True,component_duplicated=False,whole_axis_values_assigned=0,viewer_publication_pending=True,human_accepted=False)
