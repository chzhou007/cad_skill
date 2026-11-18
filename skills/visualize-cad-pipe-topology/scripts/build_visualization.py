"""Build, validate and zip a portable CAD graph viewer. All inputs are read-only."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
import ezdxf
from ezdxf.disassemble import recursive_decompose
from ezdxf import bbox
from cad_geometry import strokes, svg_shapes, normalize_symbol
from validate_visualization import validate_bundle
from post_drawing_gate import check as post_drawing_check, junction_validation_complete
from instance_geometry import source_paths, recover_folded_valve_chains, recover_exploded_ball_valve_chains, recover_block_insert_chains
from source_evidence import terminal_geometry, attributes as native_attributes
from architecture_context import extract as extract_building, svg_markup as building_svg, validate_context
from coverage_display_paths import partition as partition_source_coverage
from device_source_paths import device_source_paths
from partial_line_evidence import validate as validate_partial_line_evidence

SKILL=Path(__file__).resolve().parents[1]
def read_json(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def require_same_plan_topology(canonical,display):
    for key,idkey,fields in [('nodes','node_id',('node_type','x','y','system')),('edges','edge_id',('start_node_id','end_node_id','system','source_handles','attribute_paths'))]:
        original={x[idkey]:x for x in canonical[key]};current={x[idkey]:x for x in display[key]}
        if len(original)!=len(canonical[key]) or len(current)!=len(display[key]) or set(original)!=set(current) or any(any(original[k].get(f)!=current[k].get(f) for f in fields) for k in original):raise ValueError('plan line viewer graph differs from canonical topology: '+key)

def native_equipment_display_handles(node,doc,declared_source_hash,actual_source_hash):
    """Display a source-bound body without inferring a name, port or pipe edge."""
    if not declared_source_hash or declared_source_hash!=actual_source_hash or node.get('node_type')!='equipment':return []
    insert=doc.entitydb.get(node.get('source_handle'))
    if not insert or insert not in doc.modelspace() or insert.dxftype()!='INSERT' or insert.dxf.name!=node.get('source_block'):return []
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_equipment_body import body_straight_segments
    segments,unsupported=body_straight_segments(insert)
    if not segments or unsupported:return []
    vertices=[p for a,b in segments for p in (a,b)]
    center=[(min(p[i] for p in vertices)+max(p[i] for p in vertices))/2 for i in (0,1)]
    if math.dist(center,[node['x'],node['y']])>.05:return []
    return [insert.dxf.handle]

def normalize_legacy_component_inventory(graph,instances):
    """Adapt legacy display fields only after exact per-edge audit agreement."""
    grouped=defaultdict(list)
    for row in instances:grouped[row['edge_id']].append(row)
    adapted=[]
    for edge in graph['edges']:
        if 'equipment_inventory' in edge or not('equipment_counts' in edge or 'equipment_names' in edge):continue
        counts=edge.get('equipment_counts');names=edge.get('equipment_names');rows=grouped[edge['edge_id']]
        if not isinstance(counts,dict) or not isinstance(names,list) or any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in counts.values()):raise ValueError('invalid legacy component inventory')
        actual=Counter(row['equipment_type'] for row in rows)
        if +Counter(counts)!=actual or Counter(names)!=Counter(row['device_name'] for row in rows):raise ValueError('legacy graph inventory differs from canonical instance audit')
        edge['equipment_inventory']=[dict(equipment_type=kind,count=count,device_names=[row['device_name'] for row in rows if row['equipment_type']==kind]) for kind,count in sorted(actual.items())]
        adapted.append(edge['edge_id'])
    if adapted:graph['legacyInventoryDisplayAdapter']=dict(edge_ids=adapted,rule='exact_legacy_counts_and_names_match_current_instance_audit',physical_assignment_changed=False)
    return adapted

def native_component_display_reference(instance,doc,declared_source_hash,actual_source_hash):
    if not declared_source_hash or declared_source_hash!=actual_source_hash or instance.get('source_kind')!='block_reference':return None
    insert=doc.entitydb.get(instance.get('source_handle'))
    if not insert or insert not in doc.modelspace() or insert.dxftype()!='INSERT' or insert.dxf.name!=instance.get('source_block_name'):return None
    return insert.dxf.handle

def cad_reference_chunks(doc,building,references,project_point,tolerance):
    """Bounded architectural references use their source-owned sidecar only.

    The primary drawing is still traversed in full. Opt-in reference scopes
    avoid expanding unrelated MEP/electrical internals in a building xref.
    """
    selected={};chunks=[];entities=0
    for spec in references:
        handle=str(spec['handle']);entity=doc.entitydb.get(handle)
        if entity is None or entity not in doc.modelspace() or entity.dxftype()!='INSERT' or entity.dxf.name!=spec['block']:
            raise ValueError('CAD reference context must identify an actual top-level source INSERT')
        if not spec.get('reason') or spec.get('mode')!='architectural_context':raise ValueError('CAD reference context needs an explicit scope reason')
        records=[r for r in building['records']if r.get('source_chain',[None])[0]==handle]
        if not records:raise ValueError('CAD reference context has no building-owned source records')
        selected[handle]=records
    for top in doc.modelspace():
        if top.dxf.handle in selected:continue
        for entity in recursive_decompose([top]):
            markup=svg_shapes(strokes(entity,tolerance=tolerance),project_point,screen_stroke=True)
            if markup:
                entities+=1;chunks.append(f'<g data-vector-id="v{entities}" data-source-handle="{html.escape(entity.dxf.get("handle","") or "")}">{markup}</g>')
    for records in selected.values():
        for record in records:
            if 'label'in record:continue  # all labels are appended once below
            markup=building_svg({'records':[record]})
            if markup:
                entities+=1;chunks.append(markup.replace('<g ',f'<g data-vector-id="v{entities}" ',1))
    # A reference namespace can contain real MEP equipment as well as walls.
    # Retain explicitly audited native chains through their owning branch;
    # architectural exclusions never authorize dropping source equipment.
    retained=set()
    for spec in references:
        for item in spec.get('retained_mep_chains',[]):
            chain=item['source_chain'];key=tuple(chain)
            if not chain or chain[0]!=str(spec['handle'])or not item.get('reason'):
                raise ValueError('Retained MEP chain needs its actual reference parent and scope evidence')
            if key in retained:raise ValueError('Duplicate retained MEP source chain')
            retained.add(key)
            paths=source_paths(doc,chain=chain)
            if not paths:raise ValueError('Retained MEP source chain has no native geometry')
            markup=svg_shapes([(p['points'],p['fill'])for p in paths],project_point,screen_stroke=True)
            entities+=1;chunks.append(f'<g data-vector-id="v{entities}" data-mep-source-chain="{html.escape("/".join(chain),quote=True)}" data-source-handle="{html.escape("/".join(chain),quote=True)}">{markup}</g>')
    return chunks,entities
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_native_building_text(building):
    for row in building.get('records',[]):
        text=row.get('source_text')
        if text is None:continue
        if not isinstance(text,str) or '\ufffd' in text or any(0xd800<=ord(c)<=0xdfff for c in text):
            raise ValueError('Unreadable native building text: '+str(row.get('id','unknown')))
def validate_reference_equipment_coverage(nodes,references):
    """Never silently omit graph equipment from an architecture-scoped CAD view."""
    scoped={r['handle']:r for r in references if r.get('mode')=='architectural_context'}
    missing=[]
    for node in nodes:
        chain=node.get('display_source_chain') or []
        if node.get('node_type')!='equipment' or not chain or chain[0] not in scoped:continue
        handles=node.get('display_source_handles') or [chain[-1]]
        targets=[chain] if handles==[chain[-1]] else [chain+[h] for h in handles]
        retained=[r.get('source_chain',[]) for r in scoped[chain[0]].get('retained_mep_chains',[])]
        for target in targets:
            if not any(keep and target[:len(keep)]==keep for keep in retained):missing.append((node.get('node_id'),target))
    if missing:raise ValueError('CAD reference omits nested graph equipment: '+repr(missing[:8]))
    return {'status':'PASS','scoped_equipment_coverage':'complete'}
def building_semantic_hash(data):
    """Exclude projection/style fields while preserving source geometry and labels."""
    records=[]
    for r in data['records']:
        row={k:v for k,v in r.items() if k not in ('display_position','display_text_bounds','font_height','paths')}
        row['paths']=[{k:v for k,v in p.items() if k!='display_points'}for p in r.get('paths',[])]
        records.append(row)
    payload={'source_sha256':data['source_sha256'],'source_units':data.get('source_units'),'records':records,
             'issues':data.get('issues',[]),'exclusions':data.get('explicit_exclusions',[])}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def verify_building_dependency():
    lock=read_json(SKILL/'scripts/architecture-dependency-lock.json')
    if lock['sha256']!=digest(SKILL/'scripts/architecture_context.py'):
        raise ValueError('Building dependency differs from its canonical owner lock; synchronize and regress before generation')
    return lock
def safe(value,name,english=False):
    s=str(value)
    if not s or any(c in s for c in '<>"\'&`') or any(ord(c)<32 for c in s):raise ValueError(f'{name}: empty value or unsupported markup/control characters')
    if '\ufffd' in s or any(0xD800<=ord(c)<=0xDFFF or 0x7f<=ord(c)<=0x9f or ord(c) in (0x200e,0x200f,0x202a,0x202b,0x202c,0x202d,0x202e,0x2066,0x2067,0x2068,0x2069) for c in s):raise ValueError(f'{name}: unreadable or unsupported Unicode characters')
    if english and not s.isascii():raise ValueError(f'{name}: use an English display label and retain originals as source_names')
    return s
def number(v,name):
    v=float(v)
    if not math.isfinite(v):raise ValueError(f'{name} must be finite')
    return v
def normalize_instance_position(instance,name):
    for key in ('x','y'):instance[key]=number(instance[key],name)
    missing=[instance.get(key) in (None,'') for key in ('assignment_x','assignment_y')]
    if any(missing) and not all(missing):raise ValueError(f'{name}: incomplete assignment display point')
    if all(missing):
        instance['assignment_x']=instance['x'];instance['assignment_y']=instance['y']
        instance['display_assignment_basis']='source_audit_anchor_no_separate_assignment_point'
    for key in ('assignment_x','assignment_y','edge_distance'):instance[key]=number(instance[key],name)
def points(v,name):
    if not isinstance(v,list) or len(v)<2:raise ValueError(f'{name}: at least two source points required')
    return [[number(p[0],name),number(p[1],name)] for p in v]

def load_symbol(spec,docs,label):
    drawing=spec.get('drawing','main');block=spec['block'];mode=spec.get('mode','block')
    if drawing not in docs:raise ValueError(f'{label}: missing {drawing} DXF')
    doc=docs[drawing]
    if block not in doc.blocks:raise ValueError(f'{label}: source block {block!r} not found')
    if mode=='block':entities=list(recursive_decompose(doc.blocks[block]))
    elif mode=='insert':
        matches=[e for e in doc.modelspace().query('INSERT') if e.dxf.name==block and (not spec.get('insert_handle') or e.dxf.handle==spec['insert_handle'])]
        if len(matches)!=1:raise ValueError(f'{label}: insert mode needs one insert or insert_handle; found {len(matches)}')
        entities=list(recursive_decompose(matches))
    else:raise ValueError(f'{label}: unsupported symbol mode {mode}')
    ext=bbox.extents(entities)
    tolerance=max(max(ext.size.x,ext.size.y)*1e-5,1e-12) if ext.has_data else .001
    items=[]
    for e in entities:
        if 'colors' in spec and e.dxf.get('color',256) not in spec['colors']:continue
        items.extend(strokes(e,tolerance=tolerance))
    return normalize_symbol(items,block)|{'source':drawing,'mode':mode}

def verified_source_attribute_ancestor(graph_path,graph):
    if 'sourceFullPlanBatchAttributes' in graph or any('batch_plan_attribute_scopes' in e for e in graph.get('edges',[])):
        if not graph.get('sourceFullPlanBatchAttributes'):raise ValueError('Complete batch attributes lack their verified root')
        from full_batch_plan_attribute_viewer import verify
        return verify(graph_path,graph)
    named_prefix='sourceCurrentNamedUpperPrefixEvidence' in graph or any('current_named_prefix_source_evidence' in e for e in graph.get('edges',[]))
    if named_prefix:
        if not graph.get('sourceCurrentNamedUpperPrefixEvidence'):raise ValueError('Current named prefix evidence lacks its verified fusion root')
        from current_named_prefix_viewer_evidence import verify
        return verify(graph_path,graph)
    if 'sourceKnownJunctionMainAttributes' in graph:
        from known_junction_main_viewer_evidence import verify
        return verify(graph_path,graph)
    current_floor='sourceCurrentFloorPlanScopeAdoption' in graph or any('current_floor_plan_scope_evidence' in e for e in graph.get('edges',[]))
    if current_floor:
        if not graph.get('sourceCurrentFloorPlanScopeAdoption'):raise ValueError('current floor scopes lack a verified adoption stage')
        from current_floor_scope_viewer_evidence import verify
        return verify(graph_path,graph)
    external='sourceExternalFeedPlanAttributes' in graph or any('external_feed_plan_attributes' in e for e in graph.get('edges',[])) or any('source_external_destination_context' in n for n in graph.get('nodes',[]))
    if external:
        if not graph.get('sourceExternalFeedPlanAttributes'):raise ValueError('external feed attributes lack a verified fusion stage')
        from external_feed_plan_viewer_evidence import verify
        return verify(graph_path,graph)
    network_prefix='sourceNetworkNamedLowerPlanAttributes' in graph or any('network_named_lower_plan_attributes' in e for e in graph.get('edges',[]))
    if network_prefix:
        if not graph.get('sourceNetworkNamedLowerPlanAttributes'):raise ValueError('network named prefixes lack a verified fusion stage')
        from network_named_lower_plan_viewer_evidence import verify
        return verify(graph_path,graph)
    anchored='sourceAnchoredFloorMainAttributes' in graph or any('anchored_floor_main_attributes' in e for e in graph.get('edges',[]))
    if anchored:
        if not graph.get('sourceAnchoredFloorMainAttributes'):raise ValueError('anchored main attributes lack a verified fusion stage')
        from anchored_floor_main_viewer_evidence import verify
        return verify(graph_path,graph)
    wave='sourceWaveRebasedPlanScopeAdoption' in graph or any('current_plan_scope_evidence' in e.get('cross_view_attributes',{}) for e in graph.get('edges',[]))
    if wave:
        if not graph.get('sourceWaveRebasedPlanScopeAdoption'):raise ValueError('current plan scopes lack a verified adoption stage')
        from wave_plan_scope_viewer_evidence import verify
        return verify(graph_path,graph)
    lower='sourceLowerFloorPlanSegmentAttributes' in graph or any(a.get('scope')=='native_plan_matched_lower_floor_axis_segments_only' for e in graph.get('edges',[]) for a in e.get('plan_segment_attributes',[]))
    if lower:
        if not graph.get('sourceLowerFloorPlanSegmentAttributes'):raise ValueError('lower floor plan segments lack a verified extension stage')
        from lower_floor_plan_viewer_evidence import verify
        return verify(graph_path,graph)
    upper='sourceUpperFloorPlanSegmentAttributes' in graph or any('plan_segment_attributes' in e for e in graph.get('edges',[]))
    if upper:
        if not graph.get('sourceUpperFloorPlanSegmentAttributes'):raise ValueError('upper floor plan segments lack a verified extension stage')
        from upper_floor_plan_viewer_evidence import verify
        return verify(graph_path,graph)
    named='sourceNamedRiserPlanAttributeFusion' in graph or any(e.get('cross_view_attributes',{}).get('mapping_basis')=='native_named_riser_and_independent_equipment_service' for e in graph.get('edges',[]))
    if named:
        if not graph.get('sourceNamedRiserPlanAttributeFusion'):raise ValueError('named approach attributes lack a verified extension stage')
        import sys
        owner=SKILL.parent/'build-cad-pipe-topology/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from attach_named_riser_plan_attributes import verify_output
        from attach_axis_riser_segment_attributes import viewer_ancestry
        audit=verify_output(graph_path.parent)
        if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('named approach viewer graph differs from native replay')
        if (audit.get('prior_edges_and_vertical_attributes_preserved') is not True or audit.get('physical_ports_verified') is not False
            or audit.get('whole_edge_DN_assigned')!=0 or audit.get('installed_lengths_assigned')!=0
            or audit.get('related_HIL_confirmation_inherited') is not False):raise ValueError('named approach extension changed inherited scopes or physical extent')
        parent=Path(audit['parent_graph']['path']);axis=audit['verified_axis_segment_parent']
        if digest(parent)!=audit['parent_graph']['sha256'] or axis['output_graph_sha256']!=digest(parent):raise ValueError('named approach verified axis parent changed')
        ancestor,proof=viewer_ancestry(axis,digest(graph_path))
        proof['records']+=copy.deepcopy(audit['records']);proof['plan_DN_scope_fusion']+=copy.deepcopy(audit['plan_DN_scope_fusion'])
        proof.update(named_riser_plan_attribute_audit=audit,axis_riser_attribute_parent_graph_path=str(parent),human_accepted=False,hil_ready=False)
        return ancestor,proof
    vertical='sourceAxisRiserSegmentAttributes' in graph or any('axis_riser_attributes' in e for e in graph.get('edges',[]))
    if vertical:
        if not graph.get('sourceAxisRiserSegmentAttributes'):raise ValueError('axis riser segment values lack a verified extension stage')
        import sys
        owner=SKILL.parent/'build-cad-pipe-topology/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from attach_axis_riser_segment_attributes import verify_output,viewer_ancestry
        audit=verify_output(graph_path.parent)
        if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('axis riser viewer graph differs from native replay')
        if audit.get('all_prior_plan_attributes_preserved') is not True or audit.get('local_topology_and_components_preserved') is not True:raise ValueError('axis riser extension changed inherited topology or plan attributes')
        return viewer_ancestry(audit,digest(graph_path))
    refined=bool(graph.get('pairedJunctionCrossViewAttributeFusion')) or any(e.get('cross_view_attributes',{}).get('mapping_basis')=='native_paired_service_junction_correspondence' for e in graph.get('edges',[]))
    if refined:
        if not graph.get('pairedJunctionCrossViewAttributeFusion'):raise ValueError('refined paired scope lacks a composed verified stage')
        if 'pairedServiceCrossViewAttributeFusion' in graph:raise ValueError('coarse and refined paired stages cannot be combined')
        import sys
        owner=SKILL.parent/'build-cad-pipe-topology/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from compose_refined_paired_plan_attributes import verify_output
        stage=graph_path.parent/'refined-paired-attribute-composition-audit.json';declared=read_json(stage)
        base=Path(declared['parent_graph']['path']);base_audit_path=base.parent/'source-attribute-fusion-audit.json';before=digest(base_audit_path)
        extension=verify_output(graph_path.parent)
        if digest(base_audit_path)!=before:raise ValueError('refined base audit changed during replay')
        if read_json(graph_path)!=graph or extension['output_graph_sha256']!=digest(graph_path):raise ValueError('refined viewer graph differs from native replay')
        if extension['parent_graph']!=declared['parent_graph'] or digest(base)!=extension['parent_graph']['sha256']:raise ValueError('refined viewer base changed')
        audit=copy.deepcopy(read_json(base_audit_path))
        if audit['output_graph_sha256']!=digest(base) or audit['parent_graph']!=extension['common_parent_graph']:raise ValueError('refined child and base have different ancestry')
        parent=Path(audit['parent_graph']['path'])
        if digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('refined common parent changed')
        audit['records']=audit['records']+extension['records'];audit['plan_DN_scope_fusion']=audit.get('plan_DN_scope_fusion',[])+extension['plan_DN_scope_fusion']
        audit.update(output_graph_sha256=digest(graph_path),refined_paired_attribute_composition_audit=extension,
            refined_base_attribute_audit_path=str(base_audit_path),human_accepted=False,hil_ready=False)
        return parent,audit
    paired=bool(graph.get('pairedServiceCrossViewAttributeFusion')) or any(e.get('cross_view_attributes',{}).get('mapping_basis')=='native_paired_service_corridors' for e in graph.get('edges',[]))
    if paired:
        if not graph.get('pairedServiceCrossViewAttributeFusion'):raise ValueError('paired attribute scope lacks a composed verified stage')
        import sys
        owner=SKILL.parent/'build-cad-pipe-topology/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from compose_paired_plan_attribute_scope import verify_output
        stage=graph_path.parent/'paired-attribute-extension-audit.json';declared=read_json(stage)
        base=Path(declared['parent_graph']['path']);base_audit_path=base.parent/'source-attribute-fusion-audit.json';before=digest(base_audit_path)
        extension=verify_output(graph_path.parent)
        if digest(base_audit_path)!=before:raise ValueError('paired base audit changed during replay')
        if read_json(graph_path)!=graph or extension['output_graph_sha256']!=digest(graph_path):raise ValueError('paired viewer graph differs from native replay')
        if extension['parent_graph']!=declared['parent_graph'] or digest(base)!=extension['parent_graph']['sha256']:raise ValueError('paired viewer base changed')
        audit=copy.deepcopy(read_json(base_audit_path))
        if audit['output_graph_sha256']!=digest(base) or audit['parent_graph']!=extension['common_parent_graph']:raise ValueError('paired scope and inherited attributes have different ancestry')
        parent=Path(audit['parent_graph']['path'])
        if digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('paired common parent changed')
        # Extension replay has already independently reproduced this exact
        # unchanged base audit. Reuse it instead of repeating the full replay.
        audit['records']=audit['records']+extension['records']
        audit['plan_DN_scope_fusion']=audit.get('plan_DN_scope_fusion',[])+extension['plan_DN_scope_fusion']
        audit.update(output_graph_sha256=digest(graph_path),paired_attribute_extension_audit=extension,paired_base_attribute_audit_path=str(base_audit_path),human_accepted=False,hil_ready=False)
        return parent,audit
    if not graph.get('sourceCheckedCrossViewAttributeFusion'):
        if any(e.get('cross_view_attributes',{}).get('mapping_basis')=='native_source_and_main_branch_order' for e in graph.get('edges',[])):raise ValueError('source-checked attributes lack a verified stage')
        return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from compose_source_checked_plan_scopes import verify_attribute_output as verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('source-checked attribute viewer graph differs from replay')
    parent=Path(audit['parent_graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('source-checked attribute parent changed')
    return parent,audit


def verified_block_branch_ancestor(graph_path,graph):
    if not graph.get('sourceNativeBlockBranchReconstruction'):
        if any(e.get('source_native_block_branch') for e in graph.get('edges',[])):raise ValueError('native block branch lacks verified reconstruction stage')
        return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from reconstruct_native_block_branches import verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('native block branch viewer graph differs from replay')
    parent=Path(audit['parent_graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('native block branch parent changed')
    return parent,audit


def verified_circle_path_ancestor(graph_path,graph):
    if not graph.get('sourceCirclePathNormalization'):
        if 'sourceCirclePathNormalization' in graph or any('source_circle_path_normalization' in e for e in graph.get('edges',[])):raise ValueError('circle path lacks verified normalization stage')
        return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from normalize_plan_circle_paths import verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('circle normalized viewer graph differs from native replay')
    parent=Path(audit['parent_graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('circle path parent changed')
    return parent,audit


def verified_sideview_ownership_ancestor(graph_path,graph):
    if 'sourceSideviewEquipmentOwnership' not in graph:
        if any('source_sideview_equipment_interface' in e for e in graph.get('edges',[])):raise ValueError('sideview ownership lacks verified stage')
        return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from reconstruct_sideview_equipment_ownership import verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('sideview ownership viewer graph differs from native replay')
    parent=Path(audit['parent_graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('sideview ownership parent changed')
    return parent,audit


def verified_plan_descendant_ancestor(graph_path,graph):
    if not any(key in graph for key in ('sourceDeclaredCappedBranchInterfaces','sourceSH16RelatedCornerKnownIssue','sourceInheritedWavePairContinuity')):
        return graph_path,None,{}
    import sys
    pipeline=SKILL.parent/'orchestrate-cad-drawing-pipeline/scripts'
    if str(pipeline) not in sys.path:sys.path.insert(0,str(pipeline))
    from project_descendant_dispatch import snapshot_scope
    from plan_descendant_viewer_evidence import verify
    scope,declaration=snapshot_scope(graph_path,digest(graph_path),graph)
    ancestor,proof,dependencies=verify(graph_path,graph,scope)
    if declaration is not None:dependencies['plan_project_snapshot_declaration']=declaration
    dependencies['plan_project_snapshot_scope_reader']=pipeline/'project_descendant_dispatch.py'
    return ancestor,proof,dependencies


def verified_ownership_ancestor(graph_path,graph):
    if not graph.get('sourceLayoutEquipmentOwnership'):
        if any(e.get('source_layout_equipment_interface') for e in graph.get('edges',[])):raise ValueError('equipment ownership lacks verified source-layout stage')
        return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from calibrated_ownership_scope_composition import verify_ownership_output as verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('equipment ownership viewer graph differs from native replay')
    parent=Path(audit['parent_graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('equipment ownership parent changed')
    return parent,audit


def verified_project_erratum_ancestor(graph_path,graph):
    if not graph.get('sourceDraftingErrata'):
        if any(e.get('source_drafting_erratum') for e in graph.get('edges',[])):raise ValueError('project erratum lacks verified root')
        return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from apply_known_project_pipe_erratum import verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('project erratum viewer graph differs')
    parent=Path(audit['parent_graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('project erratum parent changed')
    return parent,audit


def verified_identity_ancestor(graph_path,graph):
    if not graph.get('sourceEquipmentIdentityResolution'):
        if any(n.get('source_identity_evidence',{}).get('rule')=='robust_rotated_caption_footprint' for n in graph.get('nodes',[])):raise ValueError('resolved equipment labels lack verified identity stage')
        return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from resolve_rotated_equipment_labels import verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('equipment identity viewer graph differs from native replay')
    parent=Path(audit['parent_graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('equipment identity parent changed')
    return parent,audit

def verified_attribute_ancestor(graph_path,graph):
    if not graph.get('crossViewAttributeFusion'):
        if any(e.get('cross_view_attributes') for e in graph.get('edges',[])):raise ValueError('cross-view edge attributes lack verified fusion stage')
        return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_crossview_plan_attributes import verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('cross-view viewer graph differs from native replay')
    parent=Path(audit['parent_graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['parent_graph']['sha256']:raise ValueError('cross-view local parent changed')
    return parent,audit


def verified_repair_ancestor(graph_path,graph):
    """A replayed inventory-only child preserves its parent's repair proofs."""
    if not graph.get('sourceConfirmedGapJoints'):return graph_path,None
    import sys
    owner=SKILL.parent/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_confirmed_gap_joints import verify_output
    audit=verify_output(graph_path.parent)
    if read_json(graph_path)!=graph or audit['output_graph_sha256']!=digest(graph_path):raise ValueError('gap-joint viewer graph differs from verified output')
    parent=Path(audit['inputs']['graph']['path'])
    if not parent.is_file() or digest(parent)!=audit['inputs']['graph']['sha256']:raise ValueError('gap-joint viewer parent changed')
    return parent,audit

def execution_dependency_paths():
    """Bind the explicit native worker backend without changing legacy inputs."""
    import sys
    runtime=sys.modules.get('native_replay_session')
    if getattr(runtime,'execution_backend',None)!='native_direct_verification_v1':return {}
    owner=SKILL.parent/'orchestrate-cad-drawing-pipeline/scripts'
    expected_runtime=(owner/'native_direct_verification_runtime.py').resolve()
    expected_worker=(owner/'native_direct_worker.py').resolve()
    if Path(getattr(runtime,'__file__','')).resolve()!=expected_runtime:raise ValueError('Unexpected native direct runtime path')
    entry=sys.modules.get('__main__')
    if Path(getattr(entry,'__file__','')).resolve()!=expected_worker:raise ValueError('Native direct viewer requires its explicit worker entry')
    return {'native_direct_verification_runtime':expected_runtime,'native_direct_worker_entry':expected_worker}


def _build(args):
    paths={'graph':args.graph.resolve(),'devices':args.devices.resolve(),'main_dxf':args.dxf.resolve(),'config':args.config.resolve()}
    paths.update(execution_dependency_paths())
    if args.legend_dxf:paths['legend_dxf']=args.legend_dxf.resolve()
    if args.ports:paths['ports']=args.ports.resolve()
    if getattr(args,'building_context',None):paths['building_context']=args.building_context.resolve()
    if getattr(args,'parameters',None):paths['parameters']=args.parameters.resolve()
    if bool(getattr(args,'named_leader_screen',None))!=bool(getattr(args,'named_leader_source_graph',None)):raise ValueError('named leader screen requires its source graph')
    if getattr(args,'named_leader_screen',None):paths['named_leader_screen']=args.named_leader_screen.resolve();paths['named_leader_source_graph']=args.named_leader_source_graph.resolve()
    gap_args=[getattr(args,k,None) for k in ('gap_joint_screen','gap_joint_stage','gap_joint_source_graph')]
    if any(gap_args) and not all(gap_args):raise ValueError('gap joint viewer evidence requires screen, stage and source graph')
    if all(gap_args):
        for key,value in zip(('gap_joint_screen','gap_joint_stage','gap_joint_source_graph'),gap_args):paths[key]=value.resolve()
    plan_task=getattr(args,'plan_line_task',None)
    if getattr(args,'plan_line_source_graph',None) and not plan_task:raise ValueError('plan line source graph requires plan line task')
    if plan_task:
        plan_task=plan_task.resolve()
        for key,relative in (('plan_line_inventory','reports/final-plan-line-inventory.json'),('plan_line_stage','reports/final-plan-line-stage.json'),('plan_line_coincident','reports/final-coincident-source-segments.json'),('plan_line_families','reports/final-micro-line-families.json'),('plan_line_declaration','plan-line-required.json')):paths[key]=plan_task/relative
        paths['plan_line_source_graph']=(args.plan_line_source_graph or args.graph).resolve()
    for name,p in paths.items():
        if not p.is_file():raise ValueError(f'Missing {name}: {p}')
    output=args.output.resolve();archive=output.with_name(output.name+'.zip')
    if output.exists() or archive.exists():raise ValueError('Output or ZIP exists; choose a new versioned directory')
    g=copy.deepcopy(read_json(paths['graph']))
    # This cheap compatibility check must run before expensive native ancestry.
    # Keep the raw graph for source replay; apply display normalization later.
    if g.get('sourceExplodedCaptionIdentity',{}).get('aliases'):
        from component_identity_inventory_display import normalize as preflight_identity_inventory
        preflight_identity_inventory(g,read_csv(paths['devices']),digest(paths['graph']),digest(paths['devices']))
    source_attribute_parent,source_attribute_audit=verified_source_attribute_ancestor(paths['graph'],g)
    attribute_parent,attribute_audit=verified_attribute_ancestor(source_attribute_parent,read_json(source_attribute_parent) if source_attribute_audit else g)
    if source_attribute_audit is not None:
        base_audit=source_attribute_audit.get('refined_base_attribute_audit_path') or source_attribute_audit.get('paired_base_attribute_audit_path')
        paths['source_checked_attribute_audit']=Path(base_audit) if base_audit else paths['graph'].parent/'source-attribute-fusion-audit.json'
        paths['source_checked_attribute_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/attach_source_checked_plan_attributes.py'
        if source_attribute_audit.get('paired_attribute_extension_audit'):
            paths['paired_attribute_extension_audit']=paths['graph'].parent/'paired-attribute-extension-audit.json'
            paths['paired_attribute_extension_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/compose_paired_plan_attribute_scope.py'
        if source_attribute_audit.get('refined_paired_attribute_composition_audit'):
            refined_graph=Path(source_attribute_audit.get('axis_riser_refined_parent_graph_path') or paths['graph'])
            paths['refined_paired_attribute_composition_audit']=refined_graph.parent/'refined-paired-attribute-composition-audit.json'
            paths['refined_paired_attribute_composition_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/compose_refined_paired_plan_attributes.py'
        if source_attribute_audit.get('axis_riser_segment_attribute_audit'):
            axis_graph=Path(source_attribute_audit.get('axis_riser_attribute_parent_graph_path') or paths['graph'])
            paths['axis_riser_segment_attribute_audit']=axis_graph.parent/'axis-riser-attribute-audit.json'
            paths['axis_riser_segment_attribute_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/attach_axis_riser_segment_attributes.py'
            paths['axis_riser_attribute_schema_validator']=SKILL/'scripts/validate_axis_riser_attributes.py'
        if source_attribute_audit.get('named_riser_plan_attribute_audit'):
            paths['named_riser_plan_attribute_audit']=paths['graph'].parent/'named-riser-plan-attribute-fusion-audit.json'
            paths['named_riser_plan_attribute_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/attach_named_riser_plan_attributes.py'
        if source_attribute_audit.get('upper_floor_plan_segment_attribute_audit'):
            upper=source_attribute_audit['upper_floor_plan_segment_attribute_audit']
            paths['upper_floor_plan_attribute_audit']=paths['graph'].parent/'upper-floor-plan-attribute-fusion-audit.json'
            paths['upper_floor_plan_attribute_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/attach_upper_floor_plan_attributes.py'
            paths['upper_floor_plan_viewer_validator']=SKILL/'scripts/upper_floor_plan_viewer_evidence.py'
            paths['native_replay_session_verifier']=SKILL.parent/'orchestrate-cad-drawing-pipeline/scripts/native_replay_session.py'
            paths['named_riser_plan_attribute_audit']=Path(upper['inputs']['parent_graph']['path']).parent/'named-riser-plan-attribute-fusion-audit.json'
        if source_attribute_audit.get('lower_floor_plan_segment_attribute_audit'):
            lower=source_attribute_audit['lower_floor_plan_segment_attribute_audit']
            paths['lower_floor_plan_attribute_audit']=paths['graph'].parent/'lower-floor-plan-attribute-fusion-audit.json'
            paths['lower_floor_plan_attribute_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/attach_lower_floor_plan_attributes.py'
            paths['lower_floor_plan_viewer_validator']=SKILL/'scripts/lower_floor_plan_viewer_evidence.py'
            paths['upper_floor_plan_attribute_audit']=Path(lower['inputs']['parent_graph']['path']).parent/'upper-floor-plan-attribute-fusion-audit.json'
        if source_attribute_audit.get('wave_plan_scope_adoption_audit'):
            from wave_plan_scope_viewer_evidence import dependency_paths
            paths.update(dependency_paths(source_attribute_audit,paths['graph']))
        if source_attribute_audit.get('anchored_floor_main_attribute_audit'):
            from anchored_floor_main_viewer_evidence import dependency_paths
            paths.update(dependency_paths(source_attribute_audit,paths['graph']))
        if source_attribute_audit.get('network_named_lower_plan_attribute_audit'):
            from network_named_lower_plan_viewer_evidence import dependency_paths
            paths.update(dependency_paths(source_attribute_audit,paths['graph']))
        if source_attribute_audit.get('external_feed_plan_attribute_audit'):
            from external_feed_plan_viewer_evidence import dependency_paths
            paths.update(dependency_paths(source_attribute_audit,paths['graph']))
        if source_attribute_audit.get('current_floor_plan_scope_adoption_audit'):
            from current_floor_scope_viewer_evidence import dependency_paths
            paths.update(dependency_paths(source_attribute_audit,paths['graph']))
        if source_attribute_audit.get('known_junction_main_fusion_audit'):
            from known_junction_main_viewer_evidence import dependency_paths
            paths.update(dependency_paths(source_attribute_audit,paths['graph']))
        if source_attribute_audit.get('current_named_prefix_evidence_fusion_audit'):
            from current_named_prefix_viewer_evidence import dependency_paths
            paths.update(dependency_paths(source_attribute_audit,paths['graph']))
        if source_attribute_audit.get('full_batch_plan_attribute_fusion_audit'):
            from full_batch_plan_attribute_viewer import dependency_paths
            paths.update(dependency_paths(source_attribute_audit,paths['graph']))
        g['sourceCheckedCrossViewAttributeEvidence']=source_attribute_audit
    block_parent,block_branch_audit=verified_block_branch_ancestor(attribute_parent,read_json(attribute_parent) if attribute_audit else g)
    circle_parent,circle_audit=verified_circle_path_ancestor(block_parent,read_json(block_parent) if block_branch_audit or attribute_audit else g)
    sideview_parent,sideview_ownership_audit=verified_sideview_ownership_ancestor(circle_parent,read_json(circle_parent) if circle_audit or block_branch_audit or attribute_audit else g)
    sideview_parent,plan_descendant_audit,plan_descendant_dependencies=verified_plan_descendant_ancestor(sideview_parent,read_json(sideview_parent) if sideview_ownership_audit or circle_audit or block_branch_audit or attribute_audit else g)
    if plan_descendant_audit is not None:
        paths.update(plan_descendant_dependencies);g['sourcePlanDescendantEvidence']=plan_descendant_audit
    ownership_parent,ownership_audit=verified_ownership_ancestor(sideview_parent,read_json(sideview_parent) if plan_descendant_audit or sideview_ownership_audit or circle_audit or block_branch_audit or attribute_audit else g)
    erratum_parent,erratum_audit=verified_project_erratum_ancestor(ownership_parent,read_json(ownership_parent) if ownership_audit or circle_audit or block_branch_audit or attribute_audit else g)
    identity_parent,identity_audit=verified_identity_ancestor(erratum_parent,read_json(erratum_parent) if erratum_audit or ownership_audit or circle_audit or block_branch_audit or attribute_audit else g)
    if erratum_audit is not None:
        paths['project_known_erratum_audit']=ownership_parent.parent/'project-known-erratum-audit.json'
        paths['project_known_erratum_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/apply_known_project_pipe_erratum.py'
        g['sourceProjectKnownErratumEvidence']=erratum_audit
    if circle_audit is not None:
        paths['circle_path_normalization_audit']=block_parent.parent/'circle-path-normalization-audit.json'
        paths['circle_path_normalization_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/normalize_plan_circle_paths.py'
        g['sourceCirclePathNormalizationEvidence']=circle_audit
    if block_branch_audit is not None:
        paths['native_block_branch_audit']=attribute_parent.parent/'native-block-branch-reconstruction-audit.json'
        paths['native_block_branch_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/reconstruct_native_block_branches.py'
        g['sourceNativeBlockBranchEvidence']=block_branch_audit
    if ownership_audit is not None:
        paths['equipment_ownership_audit']=sideview_parent.parent/'calibrated-equipment-ownership-audit.json'
        from calibrated_ownership_scope_composition import MODE as OWNERSHIP_SCOPES_MODE
        ownership_module='calibrated_ownership_scope_composition.py' if ownership_audit.get('mode')==OWNERSHIP_SCOPES_MODE else 'calibrated_equipment_interface_ownership.py'
        paths['equipment_ownership_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts'/ownership_module
        if ownership_audit.get('mode')==OWNERSHIP_SCOPES_MODE:paths['equipment_ownership_native_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/calibrated_equipment_interface_ownership.py'
        g['sourceLayoutEquipmentOwnershipEvidence']=ownership_audit
    if sideview_ownership_audit is not None:
        paths['sideview_equipment_ownership_audit']=circle_parent.parent/'sideview-equipment-ownership-audit.json'
        paths['sideview_equipment_ownership_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/reconstruct_sideview_equipment_ownership.py'
        paths['sideview_equipment_branch_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/native_sideview_equipment_branch_evidence.py'
        g['sourceSideviewEquipmentOwnershipEvidence']=sideview_ownership_audit
    if identity_audit is not None:
        paths['equipment_identity_audit']=erratum_parent.parent/'equipment-identity-layout-audit.json'
        paths['equipment_identity_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/resolve_rotated_equipment_labels.py'
        g['sourceEquipmentIdentityEvidence']=identity_audit
        if plan_task and not getattr(args,'plan_line_source_graph',None):paths['plan_line_source_graph']=identity_parent
    if g.get('confirmedEquipmentPairReconstruction'):
        import sys
        owner=SKILL.parent/'build-cad-pipe-topology/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from reconstruct_confirmed_equipment_pairs import verify_output as verify_equipment_pair_output
        equipment_pair_audit=verify_equipment_pair_output(identity_parent.parent)
        if equipment_pair_audit['output_graph_sha256']!=digest(identity_parent):raise ValueError('stale viewer equipment pair graph')
        paths['equipment_pair_audit']=identity_parent.parent/'equipment-pair-reconstruction-audit.json'
        paths['equipment_pair_verifier']=owner/'reconstruct_confirmed_equipment_pairs.py'
    else:equipment_pair_audit=None
    if ownership_audit and plan_task and not getattr(args,'plan_line_source_graph',None):paths['plan_line_source_graph']=identity_parent
    local_graph=identity_parent
    repair_graph,gap_audit=verified_repair_ancestor(local_graph,read_json(local_graph) if attribute_audit or identity_audit or ownership_audit or circle_audit or block_branch_audit else g)
    if attribute_audit is not None:
        g['crossViewAttributeEvidence']=attribute_audit
        paths['crossview_attribute_audit']=source_attribute_parent.parent/'attribute-fusion-audit.json'
        paths['crossview_attribute_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/attach_crossview_plan_attributes.py'
    if equipment_pair_audit is not None:g['confirmedEquipmentPairEvidence']=equipment_pair_audit
    if gap_audit is not None:
        g['confirmedGapJointEvidence']=gap_audit
        paths['confirmed_gap_joint_audit']=local_graph.parent/'confirmed-gap-joint-audit.json'
        paths['confirmed_gap_joint_verifier']=SKILL.parent/'build-cad-pipe-topology/scripts/attach_confirmed_gap_joints.py'
    if (g.get('sourceInlineSystemResolutions') or
            any(e.get('source_inline_system_resolutions') for e in g.get('edges',[]))):
        import sys
        owner=SKILL.parent/'build-cad-pipe-topology/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from repair_upstream_joint_systems import verify_output
        g['upstreamSystemRepairEvidence']=verify_output(repair_graph)
        paths['upstream_system_audit']=repair_graph.parent/'upstream-system-repair-audit.json'
        paths['upstream_system_verifier']=owner/'repair_upstream_joint_systems.py'
    elif g.get('sourceFloorLabelRepair'):
        import sys
        owner=SKILL.parent/'build-cad-pipe-topology/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from repair_source_floor_labels import verify_output as verify_floor_output
        g['sourceFloorRepairEvidence']=verify_floor_output(repair_graph)
        paths['source_floor_audit']=repair_graph.parent/'floor-label-repair-audit.json'
        paths['source_floor_verifier']=owner/'repair_source_floor_labels.py'
    if g.get('sourceFloorLabelRepair'):
        by_node={n['node_id']:n for n in g['nodes']}
        for record in g['sourceFloorLabelRepair']['changes']:
            node=by_node[record['node_id']]
            if node.get('floor')!=record['to_floor']:raise ValueError('floor repair node snapshot changed')
            node['source_floor_reconciliation']=copy.deepcopy(record)
    if plan_task:
        import sys
        orchestrator=SKILL.parent/'orchestrate-cad-drawing-pipeline/scripts'
        if not (orchestrator/'source_comparison_gate.py').is_file():raise ValueError('plan line family display requires orchestrator source-comparison gate')
        paths['plan_line_gate']=orchestrator/'source_comparison_gate.py'
        if not read_json(paths['plan_line_stage']).get('micro_family_evidence_sha256'):raise ValueError('plan line task does not declare family evidence')
        sys.path.insert(0,str(orchestrator))
        from source_comparison_gate import final_plan_line_blockers
        canonical=read_json(paths['plan_line_source_graph'])
        require_same_plan_topology(canonical,read_json(identity_parent) if identity_audit or ownership_audit else g)
        blockers=final_plan_line_blockers(plan_task,digest(paths['plan_line_source_graph']),digest(paths['main_dxf']),canonical)
        evidence=read_json(paths['plan_line_families']);by_handle={m['source_handle']:m for family in evidence['families'] for m in family['members']}
        groups={}
        for row in blockers:
            family=row.get('source_geometry_family');key=family or 'SOURCE-'+row['source_handle']
            groups.setdefault(key,{'id':key,'members':[],'status':'pending_source_comparison'})['members'].append({'source_handle':row['source_handle'],'node_id':by_handle.get(row['source_handle'],{}).get('node_id'),'system':row['system'],'source_status':row['status']})
        if g.get('pendingPlanLineGroups'):raise ValueError('duplicate plan line family display evidence')
        g['pendingPlanLineGroups']=list(groups.values());g.setdefault('metadata',{}).update(hil_ready=False,hil_block_reason='Plan source line classification remains pending')
    if 'named_leader_screen' in paths:
        from named_leader_viewer_evidence import validate
        g['sourceNamedEndpointLeaderCandidates']=validate(read_json(paths['named_leader_screen']),read_json(paths['named_leader_source_graph']),g,digest(paths['main_dxf']),digest(paths['named_leader_source_graph']))
        g.setdefault('metadata',{}).update(hil_ready=False,hil_block_reason='Named endpoint leader candidates require source comparison')
    if 'gap_joint_screen' in paths:
        from gap_joint_viewer_evidence import validate as validate_gap_joints
        candidates=validate_gap_joints(read_json(paths['gap_joint_screen']),read_json(paths['gap_joint_stage']),read_json(paths['gap_joint_source_graph']),g,digest(paths['main_dxf']),digest(paths['gap_joint_source_graph']),digest(paths['gap_joint_screen']))
        if g.get('pendingGapJoints'):raise ValueError('duplicate gap joint viewer evidence')
        g['pendingGapJoints']=candidates;g.setdefault('pendingSourceObjects',[]).extend(copy.deepcopy(candidates))
        g.setdefault('metadata',{}).update(hil_ready=False,hil_block_reason='Unassigned source joints require source comparison')
    typed_boundary_input=g.get('metadata',{}).get('graph_format')=='experimental-typed-boundaries-v1'
    for key in ('sourceInlineSystemConflicts','sourceCircleCrossoverConflicts'):
        conflict=g.get(key,[])
        if not isinstance(conflict,list) or any(not isinstance(x,dict) for x in conflict):raise ValueError('Invalid source conflict record: '+key)
        if conflict:g.setdefault('metadata',{}).update(hil_ready=False,hil_block_reason='Unresolved source conflict: '+key)
    if typed_boundary_input:
        from typed_boundary_adapter import adapt_typed_boundaries
        g=adapt_typed_boundaries(g,paths['main_dxf'],ezdxf.readfile(paths['main_dxf'],errors='strict'))
    junction=g.get('junctionValidation')
    if any(n.get('node_type') in ('tee','physical_junction') for n in g['nodes']) and not junction_validation_complete(junction):
        g.setdefault('metadata',{})['hil_ready']=False
        g['metadata']['hil_block_reason']='Junction validation missing or malformed; source comparison required'
    cfg=read_json(paths['config']);project=copy.deepcopy(cfg['project'])
    if args.project_id:project['id']=args.project_id
    label_language=cfg.get('display',{}).get('human_label_language','en')
    if label_language not in ('en','unicode'):raise ValueError('Unsupported human label language')
    project['id']=safe(project['id'],'project.id',True)
    for k in ('title','description','equipmentLabel'):project[k]=safe(project[k],f'project.{k}',label_language=='en')
    project['slug']=re.sub('[^a-z0-9]+','-',project['id'].lower()).strip('-') or 'cad'
    systems=cfg['systems']
    # Node-only source groups must be selectable even when no edge uses them.
    # These names are explicit pending semantics, never supply/return inference.
    for node in g['nodes']:
        group=node.get('system')
        if group and group not in systems:
            if group in ('unresolved','unclassified_water','pending'):
                systems[group]={'code':'PENDING','name':'Source service unconfirmed','color':'#64748b','dash':''}
            else:
                raise ValueError(f'{node["node_id"]}: node system missing from filter configuration: {group}')
    if not systems or any(not re.fullmatch('[A-Za-z][A-Za-z0-9_-]*',key)for key in systems):raise ValueError('Provide nonempty explicit SVG-safe machine system IDs')
    for system,s in systems.items():
        safe(s['code'],f'{system}.code',True)
        safe(s['name'],f'{system}.name',label_language=='en')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',s['color']):raise ValueError(f'{system}: invalid color')
        if not re.fullmatch(r'[0-9. ]*',s.get('dash','')):raise ValueError(f'{system}: invalid SVG dash array')
    port=args.port or cfg.get('preferred_port',8765)
    if not isinstance(port,int) or not 1<=port<=65535:raise ValueError('preferred_port must be 1..65535')
    aliases={};by_code={}
    for t in cfg.get('device_types',[]):
        code=t['code']
        if not re.fullmatch('[A-Za-z][A-Za-z0-9_-]*',code) or code in by_code or code=='EQUIPMENT':raise ValueError(f'Invalid/duplicate type code: {code}')
        safe(t['label'],f'{code} label',True);by_code[code]=t
        for alias in t['source_names']+[t['label']]:
            if alias in aliases and aliases[alias]['code']!=code:raise ValueError(f'Ambiguous type alias {alias}')
            aliases[alias]=t
    def type_for(name):
        if name not in aliases:raise ValueError(f'Unmapped type {name!r}; add an English label and verified source symbol mapping')
        return aliases[name]
    instances=read_csv(paths['devices']);normalize_legacy_component_inventory(g,instances)
    if g.get('sourceExplodedCaptionIdentity',{}).get('aliases'):
        from component_identity_inventory_display import normalize as normalize_identity_inventory
        g,inventory_identity_audit=normalize_identity_inventory(g,instances,digest(paths['graph']),digest(paths['devices']))
        paths['component_identity_inventory_display']=SKILL/'scripts/component_identity_inventory_display.py'
    nodes=g.get('nodes',[]);edges=g.get('edges',[])
    if not nodes:raise ValueError('Graph has no nodes')
    node_map={};adj=defaultdict(list);kind_map={'equipment':'equipment','physical_equipment':'equipment','tee':'physical_junction','physical_junction':'physical_junction','virtual_equipment':'virtual_equipment'}
    for n in nodes:
        nid=safe(n['node_id'],'node_id')
        if 'node_label_visible' in n and not isinstance(n['node_label_visible'],bool):raise ValueError(f'{nid}: node_label_visible must be boolean')
        if n.get('node_label_visible') is False:
            proof=n.get('node_label_policy_evidence')
            if not isinstance(proof,dict) or not proof.get('expert_issue') or proof.get('source_pipe_handle') not in n.get('source_handles',[]):raise ValueError(f'{nid}: hidden node label requires expert issue and owned source pipe evidence')
        if nid in node_map:raise ValueError(f'Duplicate node ID {nid}')
        if n['node_type'] not in kind_map:raise ValueError(f'Unknown node_type {n["node_type"]}')
        n['node_type']=kind_map[n['node_type']];n['floor']=n.get('floor',n.get('floor_band'))
        if n['floor'] is None or str(n['floor'])=='all':raise ValueError(f'{nid}: missing/reserved floor ID')
        safe(n['floor'],f'{nid} floor');n['x']=number(n['x'],nid);n['y']=number(n['y'],nid)
        n['source_label']=n.get('label','')
        n['label']=f'Unresolved boundary {nid}' if n.get('boundary_type')=='unresolved_source_terminal' else nid if n['node_type']!='virtual_equipment' else f'External Interface {nid}';node_map[nid]=n
    edge_ids=set();expected=Counter();expected_names=defaultdict(Counter);main_source_digest=digest(paths['main_dxf'])
    for e in edges:
        eid=safe(e['edge_id'],'edge_id')
        if eid in edge_ids:raise ValueError(f'Duplicate edge ID {eid}')
        edge_ids.add(eid)
        for k in ('start_node_id','end_node_id'):
            if e[k] not in node_map:raise ValueError(f'{eid}: missing endpoint {e[k]}')
        if e['start_node_id']==e['end_node_id']:raise ValueError(f'{eid}: self-loop needs an explicit schema adapter')
        if e['system'] not in systems:raise ValueError(f'{eid}: unsupported system')
        e['floor_start']=node_map[e['start_node_id']]['floor'];e['floor_end']=node_map[e['end_node_id']]['floor']
        e['path_points']=points(e['path_points'],eid)
        wave_terminal=e.get('source_wave_terminal')
        if wave_terminal is not None:
            if (not isinstance(wave_terminal,dict) or wave_terminal.get('source_sha256')!=main_source_digest or
                wave_terminal.get('endpoint_node_id') not in (e['start_node_id'],e['end_node_id']) or
                wave_terminal.get('source_pipe_handle') not in e.get('source_handles',[]) or
                not wave_terminal.get('source_wave_handle') or wave_terminal.get('destination')!='unknown' or
                wave_terminal.get('paired_continuation')!='not_established' or wave_terminal.get('physical_length')!='unknown'):
                raise ValueError(f'{eid}: unpaired wave source evidence invalid')
        if e.get('source_path_coverage') and e['source_path_coverage'].get('source_sha256')!=main_source_digest:raise ValueError(f'{eid}: partial coverage source hash mismatch')
        if e.get('path_length_scope')=='drawing_paths_excluding_source_crossover_gaps_physical_length_unknown':
            gaps=e.get('source_normalized_crossovers')
            if not isinstance(gaps,list) or not gaps or any(not isinstance(g,dict) or g.get('source_sha256')!=main_source_digest or not g.get('source_gap_coverage_sha256') or not g.get('source_fragments_sha256') for g in gaps):raise ValueError(f'{eid}: crossover evidence source mismatch')
        inferred=(e.get('source_path_status')=='user_confirmed_overlay_no_native_supply_path' and e.get('connection_mode')=='user_confirmed_overlaid_supply' and e.get('path_length_complete') is False and e.get('physical_length')=='unknown' and e.get('path_length')==0 and not e.get('source_handles'))
        if not e.get('attribute_paths') and not inferred:raise ValueError(f'{eid}: missing attribute_paths; do not invent omission geometry')
        e['attribute_paths']=[points(p,eid) for p in e['attribute_paths']]
        if e.get('path_length') is None:
            evidence=e.get('calculation_source_length_evidence')
            if ('path_length' not in e or e.get('path_length_complete') is not False or e.get('path_length_scope')!='sum_of_source_edge_lengths_no_display_connector' or
                not isinstance(evidence,list) or len(evidence)<2 or not all(isinstance(x,dict) for x in evidence) or
                not any(x.get('recorded_source_length') is None for x in evidence)):
                raise ValueError(f'{eid}: unknown length requires incomplete calculation source evidence')
        else:
            e['path_length']=number(e['path_length'],eid)
            if e['path_length']<0:raise ValueError(f'{eid}: negative path length')
        adj[e['start_node_id']].append(e);adj[e['end_node_id']].append(e)
        for item in e.get('equipment_inventory',[]):
            t=type_for(item.pop('equipment_type',item.get('label','')));item['type']=t['code'];item['label']=t['label'];count=int(item['count'])
            if count<0:raise ValueError(f'{eid}: negative inventory')
            expected[eid,t['code']]+=count
            names=[]
            for name in item.get('device_names',[]):
                for alias in sorted(t['source_names'],key=len,reverse=True):name=name.replace(alias,t['label'])
                names.append(name)
            item['device_names']=names
            if len(names)!=count:raise ValueError(f'{eid}: inventory names do not match count')
            expected_names[eid,t['code']].update(names)
    for n in nodes:
        if n['node_type']=='physical_junction':
            incident={e['system'] for e in adj[n['node_id']]};system=n.get('system') or (next(iter(incident)) if len(incident)==1 else None)
            explicit_mixed=bool(n.get('mixed_source_contact') and n.get('system_review_required') and n.get('source_handles') and set(n.get('incident_systems',[]))==incident)
            if system not in systems or (incident-{system} and not explicit_mixed):raise ValueError(f'{n["node_id"]}: mixed junction needs explicit source evidence and pending classification')
            n['system']=system
    seen=set();actual=Counter();actual_names=defaultdict(Counter);used=set()
    for i,d in enumerate(instances,1):
        name=safe(d['device_name'],'device_name');t=type_for(d.pop('equipment_type'));eid=d['edge_id']
        if name in seen:raise ValueError(f'Duplicate device name {name}')
        seen.add(name)
        if eid not in edge_ids or d['assignment_status']!='assigned':raise ValueError(f'{name}: unresolved assignment; resolve extraction before full viewer delivery')
        normalize_instance_position(d,name)
        d.update(id=f'I{i:04d}',type=t['code'],label=t['label'],source_device_name=d.pop('device_name'));d['name']=d['source_device_name']
        related=d.get('related_edge_ids') or []
        if isinstance(related,str):related=json.loads(related)
        if not isinstance(related,list)or any(e not in edge_ids for e in related):raise ValueError(f'{name}: invalid related edge IDs')
        d['related_edge_ids']=sorted(set([eid]+related))
        tags=d.get('source_instrument_tags')or []
        if isinstance(tags,str):tags=json.loads(tags)
        if not isinstance(tags,list):raise ValueError('Invalid source instrument tags')
        d['source_instrument_tags']=[safe(tag,'source instrument tag',True)for tag in tags]
        attrs=d.get('source_attributes') or []
        if isinstance(attrs,str):attrs=json.loads(attrs)
        d['source_attributes']=attrs
        for alias in sorted(t['source_names'],key=len,reverse=True):d['name']=d['name'].replace(alias,t['label'])
        for k in ('source_kind','source_block_name','source_top_handle','owner_equipment'):d.setdefault(k,'')
        actual[eid,t['code']]+=1;actual_names[eid,t['code']].update([d['name']]);used.add(t['code'])
    if actual!=+expected:raise ValueError('Per-edge/type inventory differs from the instance audit')
    if dict(actual_names)!=dict(expected_names):raise ValueError('Inventory names differ from the instance audit')
    ports=read_csv(paths['ports']) if 'ports' in paths else []
    for n in nodes:
        if n['node_type']!='virtual_equipment':continue
        source=n.get('ports') or [p for p in ports if p['node_id']==n['node_id']]
        if not source and n.get('boundary_type') in ('unresolved_source_terminal','source_declared_capped_branch_interface'):
            # Logical boundary bindings are not claims of a physical equipment port.
            source=[]
            for e in adj[n['node_id']]:
                key='start_port_id' if e['start_node_id']==n['node_id'] else 'end_port_id'
                pid=n['node_id']+'-'+e['edge_id'];e[key]=pid
                source.append(dict(port_id=pid,x=n['x'],y=n['y'],system=e['system'],status='unverified_logical_boundary',physical_port_verified=False))
            if ports:ports.extend(dict(p,node_id=n['node_id']) for p in source)
        if not source:raise ValueError(f'{n["node_id"]}: missing explicit ports')
        n['ports']=[]
        for p in source:
            p=copy.deepcopy(p);pid=safe(p['port_id'],'port_id');matches=[e for e in adj[n['node_id']] if pid in (e.get('start_port_id'),e.get('end_port_id'))]
            if len(matches)!=1:raise ValueError(f'{pid}: must bind one adjacent edge')
            p['x']=number(p.get('x',p.get('port_x')),pid);p['y']=number(p.get('y',p.get('port_y')),pid);p['system']=p.get('system') or matches[0]['system']
            if p['system']!=matches[0]['system']:raise ValueError(f'{pid}: port/edge system mismatch')
            p.setdefault('source_marker_handle',n.get('source_marker_handle',''));n['ports'].append(p)
    if not ports:ports=[copy.deepcopy(p)|{'node_id':n['node_id']} for n in nodes for p in n.get('ports',[])]
    floor_ids={str(n['floor']) for n in nodes}
    if cfg.get('floors'):
        floors=copy.deepcopy(cfg['floors'])
        if any(not isinstance(f['id'],str) for f in floors) or len({f['id'] for f in floors})!=len(floors) or {f['id'] for f in floors}!=floor_ids:raise ValueError('Configured string floor IDs must cover all input floors exactly once')
    else:
        ids=sorted(floor_ids,key=lambda f:sum(n['y'] for n in nodes if str(n['floor'])==f)/sum(str(n['floor'])==f for n in nodes),reverse=True)
        floors=[{'id':f,'label':f'{f}F' if f.isdigit() else f} for f in ids]
    for f in floors:
        safe(f['id'],'floor ID');safe(f['label'],'floor label',True);f['equipmentCount']=sum(n['node_type']=='equipment' and str(n['floor'])==f['id'] for n in nodes)
    xs=[n['x'] for n in nodes];ys=[n['y'] for n in nodes];span=max(max(xs)-min(xs),max(ys)-min(ys)) or 1;scale=span/1000;x0=min(xs)-span*.015;ymax=max(ys)+span*.015
    project_point=lambda x,y:((x-x0)/scale,(ymax-y)/scale)
    for n in nodes:
        n['px'],n['py']=project_point(n['x'],n['y'])
        for p in n.get('ports',[]):p['px'],p['py']=project_point(p['x'],p['y'])
    docs={'main':ezdxf.readfile(paths['main_dxf'],errors='strict')}
    for e in edges:
        e['points']=[project_point(*p) for p in e['path_points']];known,unknown=partition_source_coverage(e,docs['main'],main_source_digest);e['sourcePaths']=[[project_point(*p) for p in path] for path in known];e['unverifiedPaths']=[[project_point(*p) for p in path] for path in unknown]
    for p in g.get('pendingSourcePaths',[]):p['points']=[project_point(*z) for z in points(p['path_points'],'pending source path')]
    for d in instances:d['px'],d['py']=project_point(d['assignment_x'],d['assignment_y']);d['sourceX'],d['sourceY']=project_point(d['x'],d['y'])
    source_components={c['device_name']:c for c in g.pop('componentSourceGeometry',[])}
    for d in instances:
        record=source_components.get(d['source_device_name'])
        if record:
            d['sourceGeometry']=[{'points':[project_point(*p)for p in points(path['points'],'component source geometry')],'fill':bool(path.get('fill'))}for path in record['paths']]
    g['display']=cfg.get('display',{})
    for e in edges:
        validate_partial_line_evidence(docs['main'],e,main_source_digest)
        e['deviceSourcePaths']=[[project_point(*p) for p in path] for path in device_source_paths(docs['main'],e,main_source_digest)]
    if 'legend_dxf' in paths:docs['legend']=ezdxf.readfile(paths['legend_dxf'])
    for instance in instances:
        if instance.get('source_top_handle') or instance.get('source_handles'):continue
        handle=native_component_display_reference(instance,docs['main'],g.get('metadata',{}).get('source_sha256'),main_source_digest)
        if handle:
            instance['source_top_handle']=handle;instance['source_handles']=[handle]
            instance['display_source_basis']='native_insert_from_canonical_audit_handle'
    recover_folded_valve_chains(docs['main'],instances)
    recover_exploded_ball_valve_chains(docs['main'],instances)
    recover_block_insert_chains(docs['main'],instances)
    for instance in instances:native_attributes(docs['main'],instance)
    # Confirmed interface glyphs remain source markers at their original CAD
    # positions, even though their graph endpoints now belong to equipment.
    for e in edges:
        if 'source_sideview_equipment_interface' in e:
            from source_evidence import sideview_interface_glyph
            g.setdefault('sourceTerminalGlyphs',[]).append(sideview_interface_glyph(g,e))
            continue
        calibrated=bool(e.get('source_layout_equipment_interface'))
        record=e.get('source_layout_equipment_interface') if calibrated else e.get('confirmed_equipment_interface')
        if not record:continue
        original=record.get('original_interface',{});side=record.get('interface_side')
        if side not in ('start','end'):raise ValueError('Invalid confirmed interface side')
        g.setdefault('sourceTerminalGlyphs',[]).append({'id':('CALIBRATED-' if calibrated else 'CONFIRMED-')+str(original.get('node_id','')),'kind':'calibrated_source_equipment_interface' if calibrated else 'confirmed_equipment_interface','node_id':e[side+'_node_id'],'edge_id':e['edge_id'],'original_interface_id':original.get('node_id'),'source_handles':original.get('source_handles'),'system':e['system'],'floor':original.get('floor'),'remote_continuation_confirmed':not calibrated})
    for n in nodes:
        conflict=n.get('source_glyph_system_conflict')
        if not conflict:continue
        g.setdefault('sourceTerminalGlyphs',[]).append({'id':'CONFLICT-'+n['node_id'],'kind':'native_system_conflict','node_id':n['node_id'],'edge_id':conflict.get('edge_id'),'source_handles':[conflict.get('circle_handle')]+conflict.get('glyph_handles',[]),'system':conflict.get('pipe_source_system'),'floor':n['floor'],'remote_continuation_confirmed':False})
    glyph_ids=set();glyph_handles=set()
    for glyph in g.get('sourceTerminalGlyphs',[]):
        safe(glyph['id'],'native source terminal glyph ID')
        if glyph['id'] in glyph_ids or glyph_handles.intersection(glyph.get('source_handles',[])):raise ValueError('Duplicate native terminal glyph ownership')
        glyph_ids.add(glyph['id']);glyph_handles.update(glyph.get('source_handles',[]))
        geometry=terminal_geometry(docs['main'],glyph,{n['node_id']:n for n in nodes},{e['edge_id']:e for e in edges},graph=g)
        glyph['sourceGeometry']=[{'points':[project_point(*p)for p in path['points']],'fill':path['fill']}for path in geometry]
    pending_ids=set()
    for obj in g.get('pendingSourceObjects',[]):
        safe(obj['id'],'pending source object ID')
        if obj['id']in pending_ids:raise ValueError('Duplicate pending source object ID')
        pending_ids.add(obj['id'])
        if obj.get('edge_id'):raise ValueError('Unresolved source display must not assert an edge owner')
        obj['source_device_name']=obj['id'];obj['assignment_status']='unresolved_source_context'
        geometry=source_paths(docs['main'],obj.get('source_handles'),obj.get('display_source_chain'))
        if not geometry:raise ValueError('Pending source object has no native display geometry')
        obj['sourceGeometry']=[{'points':[project_point(*p)for p in path['points']],'fill':path['fill']}for path in geometry]
    # Explicit display handles describe a source-scale body independently of
    # hydraulic port boundaries and normalized list/legend symbol prototypes.
    for n in nodes:
        if not(n.get('display_source_handles')or n.get('display_source_chain')):
            handles=native_equipment_display_handles(n,docs['main'],g.get('metadata',{}).get('source_sha256'),main_source_digest)
            if handles:n['display_source_handles']=handles;n['display_source_status']='native_body_geometry_only_identity_and_ports_separate'
        if n['node_type']!='equipment' or not(n.get('display_source_handles')or n.get('display_source_chain')):continue
        geometry=[{'points':[project_point(*p)for p in path['points']],'fill':path['fill']}for path in source_paths(docs['main'],n.get('display_source_handles'),n.get('display_source_chain'))]
        if not geometry:raise ValueError(f'{n["node_id"]}: empty native equipment source geometry')
        n['sourceGeometry']=geometry
    # New conversions carry exact component source handles in their instance audit.
    # Generate native display geometry here so future sheets need no custom adapter.
    for d in instances:
        chain=d.get('display_source_chain')
        if isinstance(chain,str):chain=json.loads(chain)if chain.strip()else None
        if chain:
            d['display_source_chain']=chain;d['sourceGeometry']=[{'points':[project_point(*p)for p in path['points']],'fill':path['fill']}for path in source_paths(docs['main'],chain=chain)]
        if d.get('sourceGeometry')or not d.get('source_handles'):continue
        handles=d['source_handles']
        if isinstance(handles,str):handles=json.loads(handles)
        if not isinstance(handles,list)or any(h not in docs['main'].entitydb for h in handles):raise ValueError(f'{d["name"]}: invalid native component source handles')
        geometry=[]
        for handle in handles:
            for entity in recursive_decompose([docs['main'].entitydb[handle]]):
                for vertices,fill in strokes(entity):
                    if len(vertices)>=2:geometry.append({'points':[project_point(*p)for p in vertices],'fill':bool(fill)})
        if geometry:d['sourceGeometry']=geometry
    symbols={code:load_symbol(by_code[code]['symbol'],docs,code) for code in used};symbols['EQUIPMENT']=load_symbol(cfg['equipment_symbol'],docs,'equipment')
    equipment_symbols=cfg.get('equipment_symbols',{})
    for key,spec in equipment_symbols.items():
        if not re.fullmatch(r'EQ_[A-Za-z0-9_-]+',key):raise ValueError('Invalid equipment symbol key')
        safe(spec['label'],'equipment symbol label',True)
        symbols[key]=load_symbol(spec['symbol'],docs,key)
    for n in nodes:
        key=n.get('symbol_key','EQUIPMENT')
        if n['node_type']=='equipment' and key not in symbols:raise ValueError('Missing equipment source symbol: '+key)
        n['symbol_key']=key
    reviews=[]
    for n in nodes:
        reasons=[]
        if n['node_type']=='physical_junction' and len(adj[n['node_id']])!=3:reasons.append('Expected junction degree 3; source connectivity requires review')
        if n.get('interface_destination'):reasons.append('Source destination known; remote port identity pending')
        elif n.get('review_queue')=='source_comparison':reasons.append('Algorithm interpretation pending; handled by source-comparison families, not an expert error')
        elif n.get('boundary_type')=='unresolved_source_terminal':reasons.append('Unresolved source terminal; equipment or external connection is unconfirmed')
        if n.get('system_review_required'):reasons.append('Hydraulic system classification differs between source contacts')
        if reasons:reviews.append({'id':n['node_id'],'floor':n['floor'],'degree':len(adj[n['node_id']]),'expected':3 if n['node_type']=='physical_junction'else None,'reason':'; '.join(reasons),'automatic_hint':True})
    hashes={key:digest(p) for key,p in paths.items()}
    from equipment_label_source_annotations import extract as extract_equipment_label_source_annotations
    equipment_labels=extract_equipment_label_source_annotations(docs['main'],nodes,hashes['main_dxf'])
    if equipment_labels:
        existing=g.setdefault('sourceAnnotations',[])
        if {r['id'] for r in existing} & {r['id'] for r in equipment_labels}:
            raise ValueError('duplicate source annotation identity')
        existing.extend(equipment_labels)
    template_hashes={p.relative_to(SKILL/'assets/viewer').as_posix():digest(p) for p in sorted((SKILL/'assets/viewer').rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    implementation_hashes={n:digest(SKILL/'scripts'/n) for n in ('build_visualization.py','cad_geometry.py','validate_visualization.py','post_drawing_gate.py','instance_geometry.py','architecture_context.py','typed_boundary_adapter.py','coverage_display_paths.py','device_source_paths.py','named_leader_viewer_evidence.py','equipment_label_source_annotations.py','gap_joint_viewer_evidence.py','partial_line_evidence.py')}
    build_id=hashlib.sha256(json.dumps({'hashes':hashes,'project':project,'port':port,'template':template_hashes,'implementation':implementation_hashes},sort_keys=True).encode()).hexdigest()[:20]
    g.update(equipmentTypes=[{'code':key,'label':spec['label']} for key,spec in equipment_symbols.items()],project=project,systems=systems,floors=floors,instances=instances,symbols=symbols,types=[{'code':t['code'],'label':t['label'],'block':t['symbol']['block']} for t in cfg.get('device_types',[]) if t['code'] in used],ports=ports,review=reviews,transform={'originX':x0,'originY':ymax,'scale':scale},provenance={'dxf':paths['main_dxf'].name,'sha256':hashes['main_dxf'],'legendDxf':paths['legend_dxf'].name if 'legend_dxf' in paths else '', 'legendSha256':hashes.get('legend_dxf'),'symbols':'Source CAD geometry; tessellated curves and native fills','sourceGeometry':'Real DXF vectors; text omitted; no inferred flow'})
    g['componentReview']=[{'id':d['id'],'edge_id':d['edge_id'],'name':d['name'],'reason':'Sensor body assigned; tagged head association is unconfirmed in source geometry','automatic_hint':True}for d in instances if str(d.get('source_head_status','')).startswith('pending_')]
    native_heads={r['source_sensor_handle']:r for r in g.get('sourceInstrumentHeadCoverage',[])}
    for d in instances:
        head=native_heads.get(d.get('source_top_handle'))
        if head and head.get('source_service_tag_conflict'):
            d['source_service_tag_conflict']=True;d['source_service_tags']=head.get('source_service_tags',[])
            g['componentReview'].append({'id':d['id'],'edge_id':d['edge_id'],'name':d['name'],'reason':'Native head and exact pipe tap are complete; source service tag conflicts with the tapped source pipe layer. Original tag and pipe classification retained.','automatic_hint':True})
    g['display']=cfg.get('display',{})
    annotation_markup=[]
    for annotation in g.get('sourceAnnotations',[]):
        px,py=project_point(*annotation['position']);height=number(annotation['height'],'source annotation height')/scale
        rotation=number(annotation.get('rotation',0),'source annotation rotation')
        annotation.update(px=px,py=py,fontHeight=height,rotation=rotation)
        width=number(annotation.get('width_factor',1),'source annotation width')
        if width<=0:raise ValueError('source annotation width must be positive')
        annotation_markup.append(f'<text data-source-annotation="{html.escape(annotation["id"],quote=True)}" x="0" y="0" font-size="{height}" transform="translate({px} {py}) rotate({-rotation}) scale({width} 1)" font-family="Microsoft YaHei, Noto Sans CJK SC, SimSun, sans-serif" fill="#b14667" stroke="none">{html.escape(annotation["text"])}</text>')
    if annotation_markup:g['provenance']['sourceGeometry']='Real DXF vectors plus hash-pinned source annotation text; no inferred flow'
    dependency=verify_building_dependency()
    manifest={'schemaVersion':1,'viewerVersion':(SKILL/'VERSION').read_text(encoding='utf-8').strip()+'-HIL','visualizationSkill':(SKILL/'VERSION').read_text(encoding='utf-8').strip()+'-HIL','pipelineContractVersion':'1.0.1','buildingDependency':dependency,'bundleId':build_id,'projectId':project['id'],'preferredPort':port,'nodes':len(nodes),'edges':len(edges),'instances':len(instances),'ports':len(ports),'reviews':len(reviews),'sourceHashes':hashes,'templateHashes':template_hashes,'implementationHashes':implementation_hashes,'symbols':{k:{'block':v['block'],'source':v['source'],'primitiveCount':v['primitiveCount']} for k,v in symbols.items()}}
    manifest['pendingSourceObjects']=len(g.get('pendingSourceObjects',[]))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.cad-viewer-build-',dir=output.parent) as tmp:
        stage=Path(tmp)/'viewer';shutil.copytree(SKILL/'assets/viewer',stage,ignore=shutil.ignore_patterns('__pycache__','*.pyc','annotations'));dd=stage/'public/data';dd.mkdir()
        (dd/'graph.json').write_text(json.dumps(g,ensure_ascii=True,separators=(',',':')),encoding='utf8')
        if typed_boundary_input:
            shutil.copyfile(paths['graph'],dd/'canonical-typed-boundaries.json')
        if g.get('metadata',{}).get('extraction_status')=='partial':
            coverage={'status':'partial_unreviewed','metadata':g['metadata'],'loaded_nodes':len(nodes),'loaded_edges':len(edges),'loaded_components':len(instances),'pending_source_path_groups':len(g.get('pendingSourcePaths',[])),'equipment_ports':[{'node_id':n['node_id'],'source_ports':len(n['source_ports']),'ports_with_edges':sum(bool(p.get('edge_id'))for p in n['source_ports'])}for n in nodes if isinstance(n.get('source_ports'),list)],'scope':'Loaded graph input only. Preserve the full extraction audits separately; Finish Review does not confirm unresolved source geometry.'}
            (dd/'extraction-report.json').write_text(json.dumps(coverage,ensure_ascii=True,indent=2),encoding='utf8')
        building=read_json(paths['building_context']) if 'building_context'in paths else extract_building(docs['main'],g['transform'],hashes['main_dxf'],max(span/100000,.001))
        manifest['buildingPreparationMode']='external_stage' if 'building_context'in paths else 'compatibility_adapter'
        validate_context(building,g)
        if cfg.get('display',{}).get('building_label_language')=='source':validate_native_building_text(building)
        references=cfg.get('cad_reference_context',[])
        if references and 'building_context'not in paths:raise ValueError('CAD reference context requires an externally prepared building sidecar')
        if references:validate_reference_equipment_coverage(nodes,references)
        chunks,entities=cad_reference_chunks(docs['main'],building,references,project_point,max(span/100000,.001))
        if references:manifest['cadReferenceContext']=references
        enabled=cfg.get('building_context',{}).get('enabled',any(building['summary']['categories'].get(k,0)for k in ['wall','column','door','window','grid','outline','floor']))
        if 'building_context'in paths:enabled=True
        # Bind review identity to the actual enriched graph, not just its input.
        # A changed projection or attached evidence conservatively invalidates
        # previous review rather than applying it to different objects.
        content={'viewer_graph':digest(dd/'graph.json')}
        if g.get('sourceFullPlanBatchAttributes'):
            from uniform_path_group_DN_context import from_artifact
            manifest['attributeValueContext']=from_artifact(paths['graph'],dd/'graph.json',paths['full_batch_plan_policy'],hashes['graph'],hashes['full_batch_plan_policy'])
            content['attribute_value_context']=hashlib.sha256(json.dumps(manifest['attributeValueContext'],sort_keys=True).encode()).hexdigest()
        annotations=''.join(annotation_markup)
        if enabled:
            if any(i['reason']!='translation_pending' for i in building['issues']):raise ValueError('Building context has unrendered source geometry: '+json.dumps(building['issues']))
            (dd/'architecture.json').write_text(json.dumps(building,ensure_ascii=False,separators=(',',':')),encoding='utf8')
            (dd/'architecture.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg">'+building_svg(building)+'</svg>',encoding='utf8')
            annotations+=building_svg(building,labels_only=True)
            manifest['buildingContext']=building['summary']
            content['architecture']=building_semantic_hash(building)
        if 'parameters'in paths:
            params=read_json(paths['parameters'])
            if params.get('source_sha256')!=hashes['main_dxf'] or params.get('task_id')!=project['id']:
                raise ValueError('Effective parameter artifact must bind this source SHA256 and task/project ID')
            (dd/'effective-parameters.json').write_text(json.dumps(params,ensure_ascii=False,sort_keys=True),encoding='utf8')
            content['parameters']=hashlib.sha256(json.dumps(params,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        if 'named_leader_screen' in paths:content['named_leader_screen']=hashes['named_leader_screen']
        if content:manifest['reviewContentHashes']=content
        (dd/'cad.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="currentColor" stroke-width=".14">'+''.join(chunks)+annotations+'</g></svg>',encoding='utf8')
        from cad_geometry import RENDER_WARNINGS
        (dd/'source-render-warnings.json').write_text(json.dumps(RENDER_WARNINGS,ensure_ascii=True,indent=2),encoding='utf8')
        manifest['sourceRenderWarnings']=len(RENDER_WARNINGS)
        manifest['sourceEntities']=entities;(dd/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
        p=stage/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace('__BUILD_ID__',build_id),encoding='utf8')
        (stage/'visualization-config.json').write_text(json.dumps(cfg|{'project':project},ensure_ascii=True,indent=2),encoding='utf8')
        (stage/'README.md').write_text(f'''# {project['id']} Pipe Topology

English local viewer with HIL review, generated from CAD results. Python 3.10+ is the only runtime requirement. No npm, cloud service or external script is required.

## Start

Double-click start.cmd on Windows. The launcher checks Python 3.10+ and preserves startup failures. Run `python launch_review.py --check-only` for diagnostics in startup-logs. Extract the complete ZIP first. Alternatively run `python serve.py --open` in this directory. Preferred port: {port}. If a different project occupies it, the launcher finds a free port and prints/opens the actual address. Keep the server terminal open. Use --strict-port to disable port fallback. The launcher only reuses this exact bundle identity.

## Use

Select pipes in either view; choose Current segment or Same-system network; inspect connected equipment, components, per-instance source audit and virtual ports; search IDs or English component names; query shortest same-system paths; filter floors and layers; compare actual DXF vectors; export PNG/SVG/CSV. Drag to pan, wheel to zoom, use the overview map or Fit view. Equipment/interfaces are traversal boundaries. Floor filtering changes the display, not an existing network scope.

## Human review

Click Review. Select one node/edge or Shift-click a combination; Box select also captures missing-object regions. Mark Error opens the annotation immediately. Save stores the issue, Cancel discards it. Notes accept any language. Click a listed issue to locate it; Edit updates its annotation. To change targets, adjust the selection, then Edit and Use current selection / region. Finish Review attests to the entire dataset except active errors, regardless of current filters. Changing the error scope invalidates that attestation; note-only edits do not.

Records persist under annotations/ beside this server. Keep that folder when moving a working copy; generated releases begin unreviewed. Export backup before replacing files or reloading after a conflict. A read-only folder or concurrent edit shows a save failure; no successful save is claimed.

Pair previews export local CAD/topology original and annotated PNG/SVG, context and an offline review.html form. Open that form, enter an expert explanation, download JSON and Import JSON in this viewer. Expert import never overwrites your annotation or changes topology. Wrong-version explanations remain historical. Large batches create several ZIPs of up to six issues. Building labels use English aliases; originals are retained in local context JSON. Vectors are not native DXF.

## Evidence

{len(nodes)} nodes, {len(edges)} edges, {len(instances)} components, {len(ports)} virtual ports and {len(reviews)} automatic topology hints. See validation-report.json, public/data/manifest.json and visualization-config.json. Counts and floors come from this dataset, not a prior project. Source CAD/results were read-only. Original symbol geometry, fills and polyline widths are retained; curves are tessellated. Graph dots/diamonds are overlays. Building annotations use English aliases with original text retained separately. Lengths use drawing units; no installed length, flow direction, telemetry or confirmed error is inferred. Pending review is not a confirmed fault.

The app is self-contained for viewing. Regeneration requires the originating graph/instance CSV/DXF/config and the installed visualize-cad-pipe-topology skill.
''',encoding='utf8')
        gate=post_drawing_check(stage,paths['main_dxf'])
        if gate['status']=='FAIL':raise ValueError('Post-drawing fidelity gate failed: '+json.dumps(gate['blocking_defects']))
        report=validate_bundle(stage,native_doc=docs['main'],native_source_sha256=main_source_digest);(stage/'validation-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        staged_zip=Path(tmp)/'viewer.zip'
        with zipfile.ZipFile(staged_zip,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file():z.write(p,Path(output.name)/p.relative_to(stage))
        shutil.move(str(stage),str(output));shutil.move(str(staged_zip),str(archive))
    print(json.dumps({'status':'built','output':str(output),'archive':str(archive),'validation':report},indent=2))

def build(args):
    import sys
    owner=SKILL.parent/'orchestrate-cad-drawing-pipeline/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(SKILL.parent):
        return _build(args)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('graph','devices','dxf','config','output'):p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--ports',type=Path);p.add_argument('--legend-dxf',type=Path);p.add_argument('--project-id');p.add_argument('--port',type=int)
    p.add_argument('--building-context',type=Path,help='Prepared building-owned architecture JSON, matching final graph transform')
    p.add_argument('--parameters',type=Path,help='Source/task-bound effective parameter JSON included in review identity')
    p.add_argument('--named-leader-screen',type=Path);p.add_argument('--named-leader-source-graph',type=Path)
    p.add_argument('--gap-joint-screen',type=Path);p.add_argument('--gap-joint-stage',type=Path);p.add_argument('--gap-joint-source-graph',type=Path)
    p.add_argument('--plan-line-task',type=Path,help='Source/graph-bound task with final plan line and micro-family evidence')
    p.add_argument('--plan-line-source-graph',type=Path,help='Canonical task graph if viewer graph only adds verified display/inventory fields')
    try:build(p.parse_args())
    except (ValueError,KeyError,TypeError,OSError,ezdxf.DXFError) as e:p.exit(1,f'BUILD FAILED: {e}\n')

if __name__=='__main__':main()
