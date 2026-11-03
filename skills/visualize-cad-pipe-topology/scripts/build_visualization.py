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
from post_drawing_gate import check as post_drawing_check
from instance_geometry import source_paths
from architecture_context import extract as extract_building, svg_markup as building_svg, validate_context

SKILL=Path(__file__).resolve().parents[1]
def read_json(p):return json.loads(p.read_text(encoding='utf-8-sig'))

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
            markup=svg_shapes(strokes(entity,tolerance=tolerance),project_point)
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
            markup=svg_shapes([(p['points'],p['fill'])for p in paths],project_point)
            entities+=1;chunks.append(f'<g data-vector-id="v{entities}" data-mep-source-chain="{html.escape("/".join(chain),quote=True)}">{markup}</g>')
    return chunks,entities
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
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
    if english and not s.isascii():raise ValueError(f'{name}: use an English display label and retain originals as source_names')
    return s
def number(v,name):
    v=float(v)
    if not math.isfinite(v):raise ValueError(f'{name} must be finite')
    return v
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

def build(args):
    paths={'graph':args.graph.resolve(),'devices':args.devices.resolve(),'main_dxf':args.dxf.resolve(),'config':args.config.resolve()}
    if args.legend_dxf:paths['legend_dxf']=args.legend_dxf.resolve()
    if args.ports:paths['ports']=args.ports.resolve()
    if getattr(args,'building_context',None):paths['building_context']=args.building_context.resolve()
    if getattr(args,'parameters',None):paths['parameters']=args.parameters.resolve()
    for name,p in paths.items():
        if not p.is_file():raise ValueError(f'Missing {name}: {p}')
    output=args.output.resolve();archive=output.with_name(output.name+'.zip')
    if output.exists() or archive.exists():raise ValueError('Output or ZIP exists; choose a new versioned directory')
    g=copy.deepcopy(read_json(paths['graph']));cfg=read_json(paths['config']);project=copy.deepcopy(cfg['project'])
    if args.project_id:project['id']=args.project_id
    for k in ('id','title','description','equipmentLabel'):project[k]=safe(project[k],f'project.{k}',True)
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
        for k in ('code','name'):safe(s[k],f'{system}.{k}',True)
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
    nodes=g.get('nodes',[]);edges=g.get('edges',[])
    if not nodes:raise ValueError('Graph has no nodes')
    node_map={};adj=defaultdict(list);kind_map={'equipment':'equipment','physical_equipment':'equipment','tee':'physical_junction','physical_junction':'physical_junction','virtual_equipment':'virtual_equipment'}
    for n in nodes:
        nid=safe(n['node_id'],'node_id')
        if nid in node_map:raise ValueError(f'Duplicate node ID {nid}')
        if n['node_type'] not in kind_map:raise ValueError(f'Unknown node_type {n["node_type"]}')
        n['node_type']=kind_map[n['node_type']];n['floor']=n.get('floor',n.get('floor_band'))
        if n['floor'] is None or str(n['floor'])=='all':raise ValueError(f'{nid}: missing/reserved floor ID')
        safe(n['floor'],f'{nid} floor');n['x']=number(n['x'],nid);n['y']=number(n['y'],nid)
        n['source_label']=n.get('label','')
        n['label']=f'Unresolved boundary {nid}' if n.get('boundary_type')=='unresolved_source_terminal' else nid if n['node_type']!='virtual_equipment' else f'External Interface {nid}';node_map[nid]=n
    edge_ids=set();expected=Counter();expected_names=defaultdict(Counter)
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
        if not e.get('attribute_paths'):raise ValueError(f'{eid}: missing attribute_paths; do not invent omission geometry')
        e['attribute_paths']=[points(p,eid) for p in e['attribute_paths']];e['path_length']=number(e['path_length'],eid)
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
    instances=read_csv(paths['devices']);seen=set();actual=Counter();actual_names=defaultdict(Counter);used=set()
    for i,d in enumerate(instances,1):
        name=safe(d['device_name'],'device_name');t=type_for(d.pop('equipment_type'));eid=d['edge_id']
        if name in seen:raise ValueError(f'Duplicate device name {name}')
        seen.add(name)
        if eid not in edge_ids or d['assignment_status']!='assigned':raise ValueError(f'{name}: unresolved assignment; resolve extraction before full viewer delivery')
        for k in ('x','y','assignment_x','assignment_y','edge_distance'):d[k]=number(d[k],name)
        d.update(id=f'I{i:04d}',type=t['code'],label=t['label'],source_device_name=d.pop('device_name'));d['name']=d['source_device_name']
        related=d.get('related_edge_ids') or []
        if isinstance(related,str):related=json.loads(related)
        if not isinstance(related,list)or any(e not in edge_ids for e in related):raise ValueError(f'{name}: invalid related edge IDs')
        d['related_edge_ids']=sorted(set([eid]+related))
        tags=d.get('source_instrument_tags')or []
        if isinstance(tags,str):tags=json.loads(tags)
        if not isinstance(tags,list):raise ValueError('Invalid source instrument tags')
        d['source_instrument_tags']=[safe(tag,'source instrument tag',True)for tag in tags]
        for alias in sorted(t['source_names'],key=len,reverse=True):d['name']=d['name'].replace(alias,t['label'])
        for k in ('source_kind','source_block_name','source_top_handle','owner_equipment'):d.setdefault(k,'')
        actual[eid,t['code']]+=1;actual_names[eid,t['code']].update([d['name']]);used.add(t['code'])
    if actual!=+expected:raise ValueError('Per-edge/type inventory differs from the instance audit')
    if dict(actual_names)!=dict(expected_names):raise ValueError('Inventory names differ from the instance audit')
    ports=read_csv(paths['ports']) if 'ports' in paths else []
    for n in nodes:
        if n['node_type']!='virtual_equipment':continue
        source=n.get('ports') or [p for p in ports if p['node_id']==n['node_id']]
        if not source and n.get('boundary_type')=='unresolved_source_terminal':
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
    for e in edges:
        e['points']=[project_point(*p) for p in e['path_points']];e['sourcePaths']=[[project_point(*p) for p in path] for path in e['attribute_paths']]
    for p in g.get('pendingSourcePaths',[]):p['points']=[project_point(*z) for z in points(p['path_points'],'pending source path')]
    for d in instances:d['px'],d['py']=project_point(d['assignment_x'],d['assignment_y']);d['sourceX'],d['sourceY']=project_point(d['x'],d['y'])
    source_components={c['device_name']:c for c in g.pop('componentSourceGeometry',[])}
    for d in instances:
        record=source_components.get(d['source_device_name'])
        if record:
            d['sourceGeometry']=[{'points':[project_point(*p)for p in points(path['points'],'component source geometry')],'fill':bool(path.get('fill'))}for path in record['paths']]
    g['display']=cfg.get('display',{})
    docs={'main':ezdxf.readfile(paths['main_dxf'])}
    if 'legend_dxf' in paths:docs['legend']=ezdxf.readfile(paths['legend_dxf'])
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
    template_hashes={p.relative_to(SKILL/'assets/viewer').as_posix():digest(p) for p in sorted((SKILL/'assets/viewer').rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    implementation_hashes={n:digest(SKILL/'scripts'/n) for n in ('build_visualization.py','cad_geometry.py','validate_visualization.py','post_drawing_gate.py','instance_geometry.py','architecture_context.py')}
    build_id=hashlib.sha256(json.dumps({'hashes':hashes,'project':project,'port':port,'template':template_hashes,'implementation':implementation_hashes},sort_keys=True).encode()).hexdigest()[:20]
    g.update(equipmentTypes=[{'code':key,'label':spec['label']} for key,spec in equipment_symbols.items()],project=project,systems=systems,floors=floors,instances=instances,symbols=symbols,types=[{'code':t['code'],'label':t['label'],'block':t['symbol']['block']} for t in cfg.get('device_types',[]) if t['code'] in used],ports=ports,review=reviews,transform={'originX':x0,'originY':ymax,'scale':scale},provenance={'dxf':paths['main_dxf'].name,'sha256':hashes['main_dxf'],'legendDxf':paths['legend_dxf'].name if 'legend_dxf' in paths else '', 'legendSha256':hashes.get('legend_dxf'),'symbols':'Source CAD geometry; tessellated curves and native fills','sourceGeometry':'Real DXF vectors; text omitted; no inferred flow'})
    g['componentReview']=[{'id':d['id'],'edge_id':d['edge_id'],'name':d['name'],'reason':'Sensor body assigned; tagged head association is unconfirmed in source geometry','automatic_hint':True}for d in instances if str(d.get('source_head_status','')).startswith('pending_')]
    g['display']=cfg.get('display',{})
    annotation_markup=[]
    for annotation in g.get('sourceAnnotations',[]):
        px,py=project_point(*annotation['position']);height=number(annotation['height'],'source annotation height')/scale
        rotation=number(annotation.get('rotation',0),'source annotation rotation')
        annotation.update(px=px,py=py,fontHeight=height,rotation=rotation)
        annotation_markup.append(f'<text data-source-annotation="{html.escape(annotation["id"],quote=True)}" x="{px}" y="{py}" font-size="{height}" transform="rotate({-rotation} {px} {py})" font-family="Microsoft YaHei, Noto Sans CJK SC, SimSun, sans-serif" fill="#b14667" stroke="none">{html.escape(annotation["text"])}</text>')
    if annotation_markup:g['provenance']['sourceGeometry']='Real DXF vectors plus hash-pinned source annotation text; no inferred flow'
    dependency=verify_building_dependency()
    manifest={'schemaVersion':1,'viewerVersion':'2.9.1-HIL','visualizationSkill':'2.9.1-HIL','pipelineContractVersion':'1.0.1','buildingDependency':dependency,'bundleId':build_id,'projectId':project['id'],'preferredPort':port,'nodes':len(nodes),'edges':len(edges),'instances':len(instances),'ports':len(ports),'reviews':len(reviews),'sourceHashes':hashes,'templateHashes':template_hashes,'implementationHashes':implementation_hashes,'symbols':{k:{'block':v['block'],'source':v['source'],'primitiveCount':v['primitiveCount']} for k,v in symbols.items()}}
    manifest['pendingSourceObjects']=len(g.get('pendingSourceObjects',[]))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.cad-viewer-build-',dir=output.parent) as tmp:
        stage=Path(tmp)/'viewer';shutil.copytree(SKILL/'assets/viewer',stage,ignore=shutil.ignore_patterns('__pycache__','*.pyc','annotations'));dd=stage/'public/data';dd.mkdir()
        (dd/'graph.json').write_text(json.dumps(g,ensure_ascii=True,separators=(',',':')),encoding='utf8')
        if g.get('metadata',{}).get('extraction_status')=='partial':
            coverage={'status':'partial_unreviewed','metadata':g['metadata'],'loaded_nodes':len(nodes),'loaded_edges':len(edges),'loaded_components':len(instances),'pending_source_path_groups':len(g.get('pendingSourcePaths',[])),'equipment_ports':[{'node_id':n['node_id'],'source_ports':len(n['source_ports']),'ports_with_edges':sum(bool(p.get('edge_id'))for p in n['source_ports'])}for n in nodes if isinstance(n.get('source_ports'),list)],'scope':'Loaded graph input only. Preserve the full extraction audits separately; Finish Review does not confirm unresolved source geometry.'}
            (dd/'extraction-report.json').write_text(json.dumps(coverage,ensure_ascii=True,indent=2),encoding='utf8')
        building=read_json(paths['building_context']) if 'building_context'in paths else extract_building(docs['main'],g['transform'],hashes['main_dxf'],max(span/100000,.001))
        manifest['buildingPreparationMode']='external_stage' if 'building_context'in paths else 'compatibility_adapter'
        validate_context(building,g)
        references=cfg.get('cad_reference_context',[])
        if references and 'building_context'not in paths:raise ValueError('CAD reference context requires an externally prepared building sidecar')
        chunks,entities=cad_reference_chunks(docs['main'],building,references,project_point,max(span/100000,.001))
        if references:manifest['cadReferenceContext']=references
        enabled=cfg.get('building_context',{}).get('enabled',any(building['summary']['categories'].get(k,0)for k in ['wall','column','door','window','grid','outline','floor']))
        if 'building_context'in paths:enabled=True
        content={}
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
        report=validate_bundle(stage);(stage/'validation-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        staged_zip=Path(tmp)/'viewer.zip'
        with zipfile.ZipFile(staged_zip,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file():z.write(p,Path(output.name)/p.relative_to(stage))
        shutil.move(str(stage),str(output));shutil.move(str(staged_zip),str(archive))
    print(json.dumps({'status':'built','output':str(output),'archive':str(archive),'validation':report},indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('graph','devices','dxf','config','output'):p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--ports',type=Path);p.add_argument('--legend-dxf',type=Path);p.add_argument('--project-id');p.add_argument('--port',type=int)
    p.add_argument('--building-context',type=Path,help='Prepared building-owned architecture JSON, matching final graph transform')
    p.add_argument('--parameters',type=Path,help='Source/task-bound effective parameter JSON included in review identity')
    try:build(p.parse_args())
    except (ValueError,KeyError,TypeError,OSError,ezdxf.DXFError) as e:p.exit(1,f'BUILD FAILED: {e}\n')

if __name__=='__main__':main()
