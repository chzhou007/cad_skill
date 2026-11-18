"""Batch native caption footprints over connected exploded equipment bodies.

Reuse the bounded two-font footprint kernel. A complete identity permutation
changes references only; paths, services and physical equipment stay intact.
"""
import collections
import copy
import math
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from resolve_rotated_equipment_labels import measure_caption, footprint_candidates
from source_readability import read_source

MODE='native_exploded_equipment_caption_permutation_v1'


def body_inventory(doc,layer):
    lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer==layer]
    endpoints=collections.defaultdict(set)
    for i,e in enumerate(lines):
        for p in (e.dxf.start,e.dxf.end):
            endpoints[tuple(round(float(c)*10) for c in list(p)[:3])].add(i)
    adjacent=collections.defaultdict(set)
    for ids in endpoints.values():
        for i in ids:adjacent[i].update(ids)
    seen=set();result={}
    for start in range(len(lines)):
        if start in seen:continue
        todo=[start];ids=set()
        while todo:
            i=todo.pop()
            if i in ids:continue
            ids.add(i);todo.extend(adjacent[i]-ids)
        seen.update(ids)
        if len(ids)<8:continue
        points=[list(p) for i in ids for p in (lines[i].dxf.start,lines[i].dxf.end)]
        bounds=[min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points)]
        if not 0<min(bounds[1]-bounds[0],bounds[3]-bounds[2]) or max(bounds[1]-bounds[0],bounds[3]-bounds[2])>=5000:continue
        handles=sorted(lines[i].dxf.handle for i in ids)
        result[handles[0]]=dict(bounds=bounds,handles=handles,source_XYZ=points)
    return result


def resolve(doc,graph,policy):
    bodies=body_inventory(doc,policy['equipment_layer']);boxes={k:v['bounds'] for k,v in bodies.items()}
    rows=[];pending=[];selected={n['node_id']:n for n in graph['nodes'] if n.get('placement_rule')=='exploded-outline'}
    if not selected:raise ValueError('no native exploded equipment bodies selected')
    captions=collections.defaultdict(list)
    for text in doc.modelspace().query('TEXT'):
        if text.plain_text() in selected:captions[text.plain_text()].append(text)
    choices={}
    for name,texts in captions.items():
        if len(texts)!=1:raise ValueError('duplicated native equipment caption')
        text=texts[0];widths,metrics=measure_caption(text,policy['font_profiles'])
        proof=footprint_candidates(list(text.dxf.insert)[:2],float(text.dxf.get('rotation',0)),
            float(text.dxf.height),widths,boxes)
        if len(proof['certain'])==1 and proof['certain']==proof['possible']:
            body=proof['certain'][0]
            if body in choices:raise ValueError('multiple source captions claim one body')
            choices[body]=dict(new_node_id=name,text_handle=text.dxf.handle,text_position=list(text.dxf.insert),
                font_metrics=metrics,footprint=proof)
    aliases={}
    for name,node in selected.items():
        matching=[k for k,b in boxes.items() if math.dist([node['x'],node['y']],[(b[0]+b[1])/2,(b[2]+b[3])/2])<=.05]
        if len(matching)!=1:raise ValueError('graph equipment lacks a unique native body')
        body=matching[0];record=choices.get(body)
        if not record:
            pending.append(dict(node_id=name,reason='caption_footprint_not_unique_under_font_bounds',body=bodies[body]))
            continue
        rows.append(dict(old_node_id=name,body=bodies[body],**record))
        if record['new_node_id']!=name:aliases[name]=record['new_node_id']
    if len(set(aliases.values()))!=len(aliases) or set(aliases)!=set(aliases.values()):
        raise ValueError('identity changes must form a complete closed permutation')
    out=apply_aliases(graph,aliases)
    return out,dict(mode=MODE,records=rows,pending=pending,aliases=aliases,
        equipment_bodies_checked=len(selected),all_candidate_native_bodies=len(bodies),
        source_geometry_changed=False,connections_changed=False,physical_lengths_assigned=0,human_accepted=False)


def apply_aliases(graph,aliases):
    if set(aliases)!=set(aliases.values()) or len(set(aliases.values()))!=len(aliases):
        raise ValueError('complete closed identity permutation required')
    out=copy.deepcopy(graph)
    def ref(value):
        if not isinstance(value,str):return value
        if value in aliases:return aliases[value]
        for old,new in aliases.items():
            if value.startswith(old+'-P'):return new+value[len(old):]
        return value
    for node in out['nodes']:
        if node['node_id'] in aliases:
            node['node_id']=aliases[node['node_id']]
            if 'label' in node:node['label']=ref(node['label'])
            for port in node.get('ports',[]):
                for key in ('port_id','equipment_id','node_id'):
                    if key in port:port[key]=ref(port[key])
    for edge in out['edges']:
        for key in ('start_node_id','end_node_id','start_port_id','end_port_id','device_label','equipment_id','owner_equipment'):
            if key in edge:edge[key]=ref(edge[key])
    if len({n['node_id'] for n in out['nodes']})!=len(out['nodes']):raise ValueError('identity collision')
    return out


def migrate_components(rows,aliases):
    out=copy.deepcopy(rows);changes=[]
    for row in out:
        old=row.get('owner_equipment')
        if old not in aliases:continue
        row['original_owner_equipment']=old
        row['owner_equipment']=aliases[old]
        before=row.get('device_name','')
        if before.startswith(old+'/'):
            row['original_device_name']=before
            row['device_name']=aliases[old]+before[len(old):]
        changes.append(dict(source_top_handle=row.get('source_top_handle'),edge_id=row.get('edge_id'),
            previous_owner=old,current_owner=aliases[old],previous_device_name=before,current_device_name=row.get('device_name')))
    # This layer changes identity references, never assignments or instances.
    for a,b in zip(rows,out):
        if any(a.get(k)!=b.get(k) for k in ('source_top_handle','edge_id','x','y','assignment_x','assignment_y','equipment_type')):
            raise ValueError('component identity migration changed a physical instance or its pipe owner')
    return out,changes


def compute(paths,policy):
    for key,path in paths.items():
        if sha(path)!=policy['inputs'][key]['sha256']:raise ValueError('identity batch input changed '+key)
    from reconstruct_native_block_branches import verify_output as verify_parent
    audit=verify_parent(Path(paths['graph']).parent)
    if audit['output_graph_sha256']!=sha(paths['graph']):raise ValueError('axis parent differs')
    doc,readable=read_source(paths['source']);graph=load(paths['graph'])
    if graph['metadata']['source_sha256']!=sha(paths['source']):raise ValueError('axis native source differs')
    out,proof=resolve(doc,graph,policy)
    out['sourceExplodedCaptionIdentity']=dict(proof,inputs=copy.deepcopy(policy['inputs']),
        parent_graph_sha256=sha(paths['graph']),source_sha256=sha(paths['source']),
        implementation_sha256=implementation_hashes(),source_readability=readable)
    out['derivedEvidenceInvalidation']=dict(previous_invalidation=graph.get('derivedEvidenceInvalidation'),
        reason='native caption footprint identity batch; local pipe geometry unchanged',
        recompute=['crossview_mapping','attribute_fusion','source_comparison','human_acceptance'],
        historical_annotations_preserved=True)
    return out,proof


def implementation_hashes():
    import resolve_rotated_equipment_labels as kernel
    return dict(entry=sha(__file__),footprint_kernel=sha(kernel.__file__))


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'identity-receipt.json')
    if receipt['implementation_sha256']!=implementation_hashes():raise ValueError('identity implementation changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items() if k!='policy'}
    policy_path=receipt['inputs']['policy']['path']
    if sha(policy_path)!=receipt['inputs']['policy']['sha256']:raise ValueError('identity policy changed')
    graph,proof=compute(paths,load(policy_path))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or proof!=receipt['proof']:
        raise ValueError('identity independent native replay differs')
    return receipt
