"""Source-native equipment in nested context; a block instance owns its ports.

Opt-in profiles identify verified native prototypes, never tags or distance alone.
No edge paths, services, inline devices, or lengths are changed by this stage.
"""
import collections,copy,hashlib,json,math,re
from pathlib import Path
import ezdxf
from ezdxf.math import Matrix44
from native_proxy_evidence import block_fingerprint


def readable(value):
    if '\ufffd' in value or any(0xd800<=ord(c)<=0xdfff for c in value):
        raise ValueError('Unreadable native source text')
    return value


def distance(p,a,b):
    v=[b[i]-a[i] for i in (0,1)];den=sum(x*x for x in v)
    t=max(0.,min(1.,sum((p[i]-a[i])*v[i] for i in (0,1))/den)) if den else 0.
    return math.dist(p,[a[i]+t*v[i] for i in (0,1)])


def inside(p,poly):
    x,y=p;yes=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:yes=not yes
    return yes


def perimeter(p,poly):
    return min(distance(p,a,b) for a,b in zip(poly,poly[1:]+poly[:1]))


def resolve_instance_chain(doc,chain):
    matrix=Matrix44();parent=None
    for handle in chain:
        entity=doc.entitydb[handle]
        if entity.dxftype()!='INSERT':raise ValueError('Native source chain must name INSERTs')
        if parent is None and entity not in doc.modelspace():raise ValueError('Native source chain must start at modelspace')
        if parent is not None and entity.dxf.owner!=doc.blocks[parent.dxf.name].block_record_handle:
            raise ValueError('Native source chain ownership mismatch')
        matrix=entity.matrix44()@matrix;parent=entity
    if parent is None:raise ValueError('Native source chain must not be empty')
    return matrix,parent


def native_instances(doc,profile):
    """Audit explicit instance chains with all source handles and WCS transforms."""
    result=[]
    for root in profile['roots']:
        matrix,parent=resolve_instance_chain(doc,root['source_chain'])
        for child in doc.blocks[parent.dxf.name]:
            if child.dxftype()!='INSERT':continue
            rule=next((r for r in profile['prototypes'] if r['block']==child.dxf.name),None)
            if rule is None:continue
            block=doc.blocks[child.dxf.name]
            if rule.get('fingerprint')!=block_fingerprint(block):raise ValueError('Native equipment prototype changed')
            texts=[{'handle':p.dxf.handle,'text':readable(p.plain_text())} for p in block if p.dxftype()in ('TEXT','MTEXT')]
            tags=[r for r in texts if re.fullmatch(rule['tag_regex'],r['text'].strip())]
            if len(tags)!=1:raise ValueError('Native equipment needs one verified source caption')
            m=child.matrix44()@matrix;polygons=[];primitives=[]
            for p in block:
                if p.dxftype()!='LWPOLYLINE':continue
                if not p.closed or any(abs(v[4])>1e-10 for v in p.get_points()):continue
                points=[list(m.transform(v))[:2] for v in p.vertices_in_wcs()]
                if len(points)<3:continue
                polygons.append(points);primitives.append({'source_handle':p.dxf.handle,'points':points,'closed':True})
            if not polygons:raise ValueError('Native equipment lacks verified closed body')
            # Only a real enclosing native contour can own a port; no bbox substitute.
            outer=max(polygons,key=lambda p:abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]))))
            tol=profile['contact_tolerance']
            if not all(inside(q,outer)or perimeter(q,outer)<=tol for p in polygons for q in p):
                raise ValueError('Equipment primitives do not share an enclosing body')
            chain=root['source_chain']+[child.dxf.handle]
            identity='EQ-'+root['floor']+'-'+child.dxf.handle
            result.append({'node_id':identity,'source_chain':chain,'source_block':child.dxf.name,'floor':root['floor'],
                'tag':tags[0]['text'],'source_tag_handle':tags[0]['handle'],'texts':texts,'polygon':outer,'primitives':primitives,
                'subtype':rule['label'],'subtype_zh':rule['label_zh'],'symbol_key':rule['symbol_key'],
                'bounds':[min(p[0]for p in outer),min(p[1]for p in outer),max(p[0]for p in outer),max(p[1]for p in outer)]})
    if len({r['node_id']for r in result})!=len(result):raise ValueError('Equipment instance identities collide')
    return result


def bind(graph,instances,profile,prior=None):
    out=copy.deepcopy(graph);tol=profile['contact_tolerance'];inc=collections.defaultdict(list)
    for edge in out['edges']:
        for side in ('start','end'):inc[edge[side+'_node_id']].append((edge,side))
    proposals=collections.defaultdict(list);audit=[];byid={r['node_id']:r for r in instances}
    for n in out['nodes']:
        if n['node_type']!='virtual_equipment'or len(inc[n['node_id']])!=1:continue
        if n.get('destination')or n.get('interface_destination')or n.get('boundary_type')=='interface_destination':continue
        edge,side=inc[n['node_id']][0];p=[n['x'],n['y']];path=edge['path_points'] if side=='start' else list(reversed(edge['path_points']))
        if math.dist(p,path[0])>profile['contact_tolerance']:raise ValueError('Source endpoint differs from candidate interface')
        for item in instances:
            tol=item.get('outline_contact_tolerance',profile['contact_tolerance'])
            poly=item['polygon'];bb=item['bounds']
            if not(bb[0]-tol<=p[0]<=bb[2]+tol and bb[1]-tol<=p[1]<=bb[3]+tol):continue
            row={'old_node_id':n['node_id'],'equipment_id':item['node_id'],'edge_id':edge['edge_id'],'side':side,'x':p[0],'y':p[1],
                'source_chain':item['source_chain'],'source_pipe_handles':edge['source_handles'],'system':edge['system'],
                'native_outline_distance':perimeter(p,poly),'outline_contact_tolerance':tol}
            if item.get('outline_precision_evidence'):row['outline_precision_evidence']=item['outline_precision_evidence']
            if n.get('floor')not in (None,'Schematic',item['floor']):row['status']='pending_floor_conflict'
            elif perimeter(p,poly)>tol:row['status']='rejected_inside_body_without_native_outline_contact'
            else:
                first=next((q for q in path[1:] if math.dist(q,p)>tol),None)
                if first is None or inside(first,poly)or perimeter(first,poly)<=tol:row['status']='pending_no_outward_source_ray'
                else:row['status']='qualified_native_outline_terminal_and_outward_pipe';proposals[n['node_id']].append(row)
            audit.append(row)
    retired={};contacts=[]
    for old,rr in sorted(proposals.items()):
        if len(rr)!=1:
            for r in rr:r['status']='pending_competing_native_equipment_owners'
            continue
        r=rr[0];item=byid[r['equipment_id']];edge=next(e for e in out['edges']if e['edge_id']==r['edge_id']);side=r['side']
        pid=item['node_id']+'-P'+str(1+sum(c['node_id']==item['node_id']for c in contacts)).zfill(2)
        edge[side+'_node_id']=item['node_id'];edge[side+'_port_id']=pid
        edge['edge_type']='tee_to_virtual_equipment'if any(n['node_type']=='virtual_equipment' and n['node_id']in (edge['start_node_id'],edge['end_node_id'])and n['node_id']!=old for n in out['nodes'])else'tee_to_equipment'
        edge.setdefault('endpoint_reconciliation',[]).append({'old_node_id':old,'new_node_id':item['node_id'],'source_port_id':pid,'side':side})
        r.update(status='applied',port_id=pid);retired[old]={'node_id':item['node_id'],'port_id':pid}
        contacts.append(dict(r,node_id=item['node_id'],contact_rule='unique_native_closed_outline_terminal_and_outward_source_pipe'))
    out['nodes']=[n for n in out['nodes']if n['node_id']not in retired]
    for item in instances:
        cc=[c for c in contacts if c['node_id']==item['node_id']]
        n={'node_id':item['node_id'],'node_type':'equipment','subtype':item['subtype'],'subtype_zh':item['subtype_zh'],'floor':item['floor'],
            'label':item['tag']+' / '+item['node_id'],'source_caption':item['tag'],'source_tag_handle':item['source_tag_handle'],
            'x':(item['bounds'][0]+item['bounds'][2])/2,'y':(item['bounds'][1]+item['bounds'][3])/2,
            'source_handle':item['source_chain'][-1],'source_handles':[item['source_chain'][-1]],'source_block':item['source_block'],
            'display_source_chain':item['source_chain'],'display_source_handles':[item['source_chain'][-1]],'symbol_key':item['symbol_key'],
            'source_bounds':item['bounds'],'source_ports':cc,'ports':[dict(port_id=c['port_id'],system=c['system'],x=c['x'],y=c['y'],physical_port_verified=True)for c in cc],
            'recognition_status':'native_nested_body_and_caption_verified','parameter_binding_state':'source_type_identified_schedule_variant_unbound',
            'source_port_completeness':'local_contacts_proven_all_expected_ports_unconfirmed','review_required':not bool(cc),'source_body_verified':True}
        out['nodes'].append(n)
    # Stable final IDs survive physical endpoint promotion. Unique native path
    # signatures are required; neither index order nor nearest matching is used.
    mapping={}
    if prior:
        def sig(e):return (tuple(sorted(e['source_handles'])),json.dumps(e.get('attribute_paths',[]),sort_keys=True))
        old=collections.defaultdict(list)
        for e in prior.get('edges',[]):old[sig(e)].append(e['edge_id'])
        for e in out['edges']:
            found=old[sig(e)]
            if len(found)==1 and found[0]!=e['edge_id']:mapping[e['edge_id']]=found[0];e['edge_id']=found[0]
        if len({e['edge_id']for e in out['edges']})!=len(out['edges']):raise ValueError('Final edge IDs collide')
        for c in contacts:c['edge_id']=mapping.get(c['edge_id'],c['edge_id'])
    return out,{'instances':instances,'contacts':contacts,'candidate_contacts':audit,'retired_nodes':retired,'stable_edge_reconciliation':mapping,
        'instance_count':len(instances),'connected_equipment_count':len({c['node_id']for c in contacts}),'physical_port_count':len(contacts),
        'disconnected_equipment_ids':[r['node_id']for r in instances if not any(c['node_id']==r['node_id']for c in contacts)],'source_paths_unchanged':True}


def apply(graph,profile,prior=None):
    path=Path(profile['source_path'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=profile['source_sha256']:raise ValueError('Native equipment source hash mismatch')
    if profile.get('readability_verified') is not True:raise ValueError('Verify source Chinese readability before binding')
    doc=ezdxf.readfile(path)
    return bind(graph,native_instances(doc,profile),profile,prior)
