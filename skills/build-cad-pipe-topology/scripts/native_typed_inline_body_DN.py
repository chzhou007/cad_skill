"""Inherit known native component identity in DN competitor classification.

No symbol is excluded by name or bounds alone: require a pinned historical
catalogue/type, complete native block fingerprint, exact nested instance,
unique assigned inventory identity and current same-root pipe ownership.
Unknown layer0 geometry remains in the original half-text-height guard.
"""
import ast,copy,math,types
from ezdxf.disassemble import recursive_decompose
from confirm_crossview_paths import encode
from native_inline_anchors import block_signature
from native_line_path_evidence import _on
from native_line_path_evidence import LAYERS
from native_repeated_branch_DN_layout import primitives
from axis_unbranched_vertical_DN import source_Z
import native_nested_direct_caption_DN as original

MODE='inherited_typed_native_inline_body_DN_reapplication_v1'

def historical_types(code):
    tree=ast.parse(code);hits=[n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='COMPONENT_BLOCK_TYPES'for t in n.targets)]
    if len(hits)!=1:raise ValueError('one original native component type declaration required')
    return ast.literal_eval(hits[0].value)

def qualify_templates(doc,baseline,catalogue,type_map,selections):
    result={}
    for spec in selections:
        name=spec['block_name'];kind,code=type_map.get(name,(None,None))
        if (kind!=spec['equipment_type']or code!=spec['type_code']or code!='YS'or name not in doc.blocks or name not in baseline.blocks):raise ValueError('original supported inline type and template required')
        rows=[r for r in catalogue if r['legend_equipment_type']==kind and name in r['matched_source_symbols'].split(';')and r['used_in_sh16_edge_graph']=='yes'and r['graph_role']=='edge_attribute_only']
        signature=block_signature(doc,name)
        if len(rows)!=1 or signature!=block_signature(baseline,name)or signature!=spec['block_signature_sha256']:raise ValueError('complete original inline geometry or catalogue differs')
        if len(doc.blocks[name])<3 or any(e.dxftype()!='LINE'or e.dxf.layer!='0'for e in doc.blocks[name]):raise ValueError('only complete layer0 straight native inline bodies supported')
        result[name]=dict(spec,legacy_catalogue=copy.deepcopy(rows[0]),prototype_handles=sorted(e.dxf.handle for e in doc.blocks[name]))
    if not result or len(result)!=len(selections):raise ValueError('nonempty unique original type templates required')
    return result

def partition(doc,graph,inventory,neutral,templates):
    edges={e['edge_id']:e for e in graph['edges']};roots={e.get('source_insert_handle')for e in graph['edges']if e.get('source_insert_handle')};bodies=[];held=[];pipes=primitives(doc,graph)
    def visit(entity,chain,root):
        origin=entity.source_of_copy;handle=origin.dxf.handle if origin else entity.dxf.handle;path=chain+[handle]
        if entity.dxftype()!='INSERT':return
        name=entity.dxf.name
        if name not in templates:
            for child in entity.virtual_entities():visit(child,path,root)
            return
        position=list(entity.ocs().to_wcs(entity.dxf.insert));spec=templates[name]
        rows=[r for r in inventory if r.get('source_top_handle')==root and r.get('source_block_name')==name and r.get('type_code')==spec['type_code']and r.get('equipment_type')==spec['equipment_type']and r.get('assignment_status')=='assigned'and math.dist(position[:2],[float(r['x']),float(r['y'])])<=.05]
        if len(rows)!=1:held.append(dict(source_chain=path,reason='no unique original assigned typed inventory instance'));return
        row=rows[0];edge=edges.get(row['edge_id'])
        if not edge or edge.get('source_insert_handle')!=root or not any(_on(position[:2],a,b,.05)for p in edge['attribute_paths']for a,b in zip(p,p[1:])):
            held.append(dict(source_chain=path,reason='typed component lacks current same-root pipe ownership'));return
        native_pipes=[p for p in pipes if p['root_handle']==root and p['layer']==LAYERS[edge['system']]and _on(position[:2],p['XYZ'][0][:2],p['XYZ'][1][:2],.05)and abs(source_Z(p,position[:2])-position[2])<=.05]
        if len(native_pipes)!=1:held.append(dict(source_chain=path,reason='typed component needs one same-Z native owner pipe at its anchor'));return
        if sum(r.get('device_name')==row['device_name']for r in inventory)!=1:raise ValueError('duplicate component identity')
        parts=list(recursive_decompose([entity]));hs=[p.source_of_copy.dxf.handle if p.source_of_copy else None for p in parts]
        if sorted(hs)!=spec['prototype_handles']or len(parts)!=len(doc.blocks[name])or any(p.dxftype()!='LINE'or p.dxf.layer!='0'for p in parts):raise ValueError('nested complete inline body changed')
        if any(not all(math.isfinite(v)for pt in(p.dxf.start,p.dxf.end)for v in pt)for p in parts):raise ValueError('nonfinite transformed inline body')
        bodies.append(dict(source_chain=path,root_handle=root,block_name=name,block_signature_sha256=spec['block_signature_sha256'],equipment_type=row['equipment_type'],type_code=row['type_code'],device_name=row['device_name'],edge_id=row['edge_id'],instance_position_WCS=position,native_owner_pipe=copy.deepcopy(native_pipes[0]),physical_ports_verified=False,primitives=[dict(root_handle=root,child_handle=p.source_of_copy.dxf.handle,XYZ=[list(p.dxf.start),list(p.dxf.end)],layer=p.dxf.layer)for p in parts]))
    for root in sorted(roots):
        entity=doc.entitydb.get(root)
        if entity is None or entity not in doc.modelspace():raise ValueError('original graph-referenced root missing')
        if entity.dxftype()=='INSERT':visit(entity,[],root)
    retained=[];excluded=[]
    for item in neutral:
        hits=[b for b in bodies if b['root_handle']==item['root_handle']and any(p['child_handle']==item['child_handle']and all(math.dist(a,c)<=1e-7 for a,c in zip(p['XYZ'],item['XYZ']))for p in b['primitives'])]
        if len(hits)>1:raise ValueError('neutral source primitive belongs to competing inline instances')
        if hits:excluded.append(dict(source_item=copy.deepcopy(item),typed_instance=copy.deepcopy(hits[0])))
        else:retained.append(copy.deepcopy(item))
    if len(retained)+len(excluded)!=len(neutral):raise ValueError('complete neutral population not conserved')
    return retained,dict(original_neutral_population=len(neutral),retained_neutral_population=len(retained),excluded_known_body_primitives=excluded,qualified_typed_instances=bodies,unqualified_typed_instances=held,unknown_neutral_geometry_excluded=False,physical_ports_inferred=False,source_geometry_mutated=False)

def collect(doc,graph,route,handles,source_hash,graph_hash,inventory,templates):
    before=encode(graph),encode(route),encode(inventory);audit={}
    def projection(*args):
        values=list(original.projection(*args));values[-1],proof=partition(doc,graph,inventory,values[-1],templates);audit.update(proof);return tuple(values)
    def guard(*args):
        result=original.neutral_guard(*args);result.update(original_neutral_population=audit['original_neutral_population'],typed_body_primitives_excluded=len(audit['excluded_known_body_primitives']),unknown_neutral_geometry_excluded=False);return result
    namespace=dict(original.collect.__globals__,projection=projection,neutral_guard=guard);reader=types.FunctionType(original.collect.__code__,namespace,original.collect.__name__,original.collect.__defaults__,original.collect.__closure__);result=reader(doc,graph,route,handles,source_hash,graph_hash)
    if before!=(encode(graph),encode(route),encode(inventory)):raise ValueError('graph, routing or component inventory mutated')
    result.update(mode=MODE,complete_neutral_population=audit['original_neutral_population'],typed_inline_body_evidence=audit,original_direct_reader_and_margin_unchanged=True,component_instances_removed=0,physical_values_assigned=0)
    return result
