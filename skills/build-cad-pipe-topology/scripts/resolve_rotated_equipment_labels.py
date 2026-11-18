"""Resolve retained equipment identities from robust source caption footprints.

Font-substituted glyph extents are bounded and compared across independent
fonts. Only isolated, unconnected equipment instances may be renamed. Source
layout identity is not a verified equipment port or human acceptance.
"""
import argparse,copy,csv,hashlib,json,math,re,shutil
from pathlib import Path
from ezdxf.fonts import fonts
from source_readability import read_source
from native_dn_text_position import supported
from native_equipment_body import body_straight_segments
from confirm_crossview_paths import encode,load,sha

def body_boxes(doc,graph,policy):
    nodes={n['source_handle']:n for n in graph['nodes'] if n.get('node_type')=='equipment' and n.get('source_handle')}
    equipment=[e for e in doc.modelspace().query('INSERT') if e.dxf.layer==policy['equipment_layer'] and e.dxf.name in policy['equipment_block_names']]
    boxes={}
    for insert in equipment:
        segments,unsupported=body_straight_segments(insert)
        if unsupported or not segments:raise ValueError('incomplete native equipment family body')
        points=[p for a,b in segments for p in (a,b)]
        box=[min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points)]
        if insert.dxf.handle in nodes:
            node=nodes[insert.dxf.handle];center=[(box[0]+box[1])/2,(box[2]+box[3])/2]
            if math.dist(center,[node['x'],node['y']])>.05:raise ValueError('source body disagrees with equipment node')
        boxes[insert.dxf.handle]=box
    if len(nodes)!=sum(n.get('node_type')=='equipment' and bool(n.get('source_handle')) for n in graph['nodes']):raise ValueError('equipment source represented twice')
    return boxes

def footprint_candidates(position,rotation,height,widths,boxes,width_factors=(.8,1.2)):
    """Use guaranteed and possible axial overlap, never nearest insertion point."""
    if not widths or not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>0 for x in widths):raise ValueError('invalid glyph widths')
    low,high=width_factors
    if not .75<=low<=.9 or not 1.1<=high<=1.3:raise ValueError('insufficient font uncertainty bound')
    if not height>0 or not math.isfinite(height):raise ValueError('invalid caption height')
    angle=math.radians(rotation);u=[math.cos(angle),math.sin(angle)];v=[-u[1],u[0]]
    dot=lambda p,w:p[0]*w[0]+p[1]*w[1]
    start=dot(position,u);normal=dot(position,v);minimum=min(widths)*low;maximum=max(widths)*high
    certain=[];possible=[];details=[]
    for handle,box in boxes.items():
        corners=[(x,y) for x in box[:2] for y in box[2:]]
        axial=[dot(p,u) for p in corners];perpendicular=[dot(p,v) for p in corners]
        a,b=min(axial),max(axial);c,d=min(perpendicular),max(perpendicular)
        gap=max(0,c-(normal+height),normal-d)
        overlap=lambda width:max(0,min(start+width,b)-max(start,a))
        guaranteed=overlap(minimum);available=overlap(maximum);threshold=.5*height
        if gap<=2*height and available>=threshold:possible.append(handle)
        if gap<=2*height and guaranteed>=threshold:certain.append(handle)
        if gap<=2*height and available>0:details.append(dict(source_handle=handle,perpendicular_gap=gap,minimum_axial_overlap=guaranteed,maximum_axial_overlap=available))
    return dict(certain=sorted(certain),possible=sorted(possible),width_interval=[minimum,maximum],threshold=.5*height,body_comparisons=details)

def measure_caption(text,profiles):
    values=[];evidence=[]
    if not supported(text) or not re.fullmatch(r'CRAH-[A-Za-z0-9#-]+',text.plain_text()):raise ValueError('unsupported source caption transform or syntax')
    for spec in profiles:
        path=Path(spec['path'])
        if sha(path)!=spec['sha256']:raise ValueError('calibrated display font changed')
        face=fonts.get_font_face(path.name)
        if face.family!=spec['family'] or Path(face.filename).name.lower()!=path.name.lower():raise ValueError('font silently fell back')
        font=fonts.make_font(path.name,float(text.dxf.height),float(text.dxf.get('width',1)))
        if not isinstance(font,fonts.TrueTypeFont):raise ValueError('unsupported display font')
        width=font.text_width(text.plain_text());values.append(width);evidence.append(dict(filename=path.name,sha256=spec['sha256'],family=face.family,width=width))
    if len({r['family'] for r in evidence})<2:raise ValueError('two independent font families required')
    return values,evidence

def resolve(doc,graph,policy,source_hash,graph_hash,inventory):
    if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('stale identity inputs')
    groups=policy.get('groups',[]);profiles=policy.get('font_profiles',[])
    if not groups or not profiles or len({g['id'] for g in groups})!=len(groups):raise ValueError('invalid identity groups')
    boxes=body_boxes(doc,graph,policy);nodes={n['node_id']:n for n in graph['nodes']};selected=set();new_labels=set();changes=[]
    if len(nodes)!=len(graph['nodes']):raise ValueError('duplicate node IDs')
    for group in groups:
        ids=group['node_ids'];captions=group['captions'];handles={nodes[n]['source_handle'] for n in ids}
        if len(ids)!=2 or len(set(ids))!=2 or len(captions)!=2 or len(handles)!=2 or selected&set(ids):raise ValueError('group must contain two distinct retained bodies')
        expected=set(captions)
        if any(nodes[n].get('node_type')!='equipment' or nodes[n].get('identity_status')!='unresolved' or nodes[n].get('floor')!=policy['floor'] or set(nodes[n].get('source_label_candidates',[]))!=expected for n in ids):raise ValueError('equipment identity scope changed')
        if any(n in (e.get('start_node_id'),e.get('end_node_id')) for n in ids for e in graph['edges']):raise ValueError('connected equipment requires explicit reference migration')
        if any(r.get('owner_equipment') in set(ids)|expected for r in inventory):raise ValueError('component equipment ownership requires explicit migration')
        chosen={}
        for label,handle in captions.items():
            if label in nodes or label in new_labels:raise ValueError('resolved equipment identity collision')
            text=doc.entitydb.get(handle)
            if not text or text not in doc.modelspace() or text.dxftype()!='TEXT' or text.dxf.layer!=policy['caption_layer'] or text.plain_text()!=label:raise ValueError('native equipment caption differs')
            if sum(e.plain_text()==label for e in doc.modelspace().query('TEXT MTEXT'))!=1:raise ValueError('duplicate native equipment caption')
            values,metrics=measure_caption(text,profiles)
            footprint=footprint_candidates([text.dxf.insert.x,text.dxf.insert.y],float(text.dxf.get('rotation',0)),float(text.dxf.height),values,boxes,policy['width_uncertainty_factors'])
            if len(footprint['certain'])!=1 or footprint['certain']!=footprint['possible'] or footprint['certain'][0] not in handles:raise ValueError('caption footprint identity remains ambiguous')
            body_handle=footprint['certain'][0]
            if body_handle in chosen:raise ValueError('two labels select one equipment')
            chosen[body_handle]=dict(label=label,source_text_handle=handle,source_text_position=list(text.dxf.insert),source_text_rotation=float(text.dxf.get('rotation',0)),source_text_height=float(text.dxf.height),font_metrics=metrics,footprint=footprint)
        if set(chosen)!=handles:raise ValueError('caption layout is not a complete one-to-one assignment')
        for old_id in ids:
            node=nodes[old_id];record=chosen[node['source_handle']]
            changes.append(dict(old_node_id=old_id,new_node_id=record['label'],source_handle=node['source_handle'],group_id=group['id'],source_body_bounds=boxes[node['source_handle']],**record))
            new_labels.add(record['label'])
        selected.update(ids)
    out=copy.deepcopy(graph);updates={r['old_node_id']:r for r in changes}
    for node in out['nodes']:
        record=updates.get(node['node_id'])
        if not record:continue
        old=copy.deepcopy(node)
        for key in ('source_label_candidates','source_label_pair_evidence'):node.pop(key,None)
        node.update(node_id=record['new_node_id'],label=record['label'],identity_status='source_layout_identity_resolved_human_unreviewed',
            source_identity_evidence=dict(rule='robust_rotated_caption_footprint',source_sha256=source_hash,input_graph_sha256=graph_hash,record=record,previous_anonymous_instance=old,ports_inferred=False,human_accepted=False))
    out['sourceEquipmentIdentityResolution']=dict(source_sha256=source_hash,input_graph_sha256=graph_hash,records=changes,id_aliases={r['old_node_id']:r['new_node_id'] for r in changes},
        physical_equipment_conserved=True,ports_inferred=False,fonts_are_declared_display_substitutes=True,human_accepted=False)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_equipment_identity_change')
    out['derivedEvidenceInvalidation']=dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),reason='equipment IDs resolved from native rotated captions; source paths and local connectivity unchanged',recompute=['equipment_identity_references','crossview_mapping','source_comparison','human_acceptance'],historical_annotations_preserved=True)
    return out,changes

def compute(source,graph,devices,policy):
    p=load(policy)
    if sha(devices)!=p['devices_sha256']:raise ValueError('component table changed')
    with Path(devices).open(encoding='utf-8-sig',newline='') as stream:inventory=list(csv.DictReader(stream))
    doc,preflight=read_source(source);out,records=resolve(doc,load(graph),p,sha(source),sha(graph),inventory)
    return out,dict(records=records,source_preflight=preflight,parent_graph=dict(path=str(Path(graph).resolve()),sha256=sha(graph)))

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'equipment-identity-layout-audit.json')
    if audit['implementation_sha256']!=sha(Path(__file__)):raise ValueError('stale caption footprint implementation')
    for key,item in audit['inputs'].items():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale identity input '+key)
    inputs=audit['inputs'];out,proof=compute(*(inputs[k]['path'] for k in ('source','graph','devices','policy')))
    if encode(out)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or proof['records']!=audit['records']:raise ValueError('native caption layout replay differs')
    if (directory/'assigned_edge_device_instances.csv').read_bytes()!=Path(inputs['devices']['path']).read_bytes():raise ValueError('component inventory not conserved')
    return audit

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','devices','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    out,audit=compute(a.source,a.graph,a.devices,a.policy);a.output.mkdir(parents=True)
    (a.output/'graph_with_edges.json').write_bytes(encode(out));shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
    audit.update(inputs={k:dict(path=str(getattr(a,k).resolve()),sha256=sha(getattr(a,k))) for k in ('source','graph','devices','policy')},implementation_sha256=sha(Path(__file__)),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'equipment-identity-layout-audit.json').write_bytes(encode(audit));print(json.dumps(dict(status='isolated_equipment_identities_source_checked',renamed_nodes=len(audit['records']),added_edges=0,human_accepted=False)))

if __name__=='__main__':main()
