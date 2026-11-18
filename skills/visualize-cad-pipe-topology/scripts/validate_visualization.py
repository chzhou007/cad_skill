"""Validate generated data, geometry references and bundle completeness."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from coverage_display_paths import partition as partition_source_coverage
from validate_axis_riser_attributes import validate as validate_axis_riser_attributes
from validate_full_batch_plan_attributes import validate as validate_full_batch_plan_attributes

def validate_bundle(root,native_doc=None,native_source_sha256=None):
    root=Path(root)
    for name in ('public/index.html','public/app.js','public/core.js','public/style.css','public/polish.css','public/hil.js','public/hil.css','hil_server.py','public/data/graph.json','public/data/cad.svg','public/data/manifest.json','serve.py','start.cmd','README.md','visualization-config.json'):
        if not (root/name).is_file():raise ValueError(f'Missing viewer output {name}')
    g=json.loads((root/'public/data/graph.json').read_text(encoding='utf8'))
    m=json.loads((root/'public/data/manifest.json').read_text(encoding='utf8'))
    if native_doc is not None and native_source_sha256!=m['sourceHashes']['main_dxf']:raise ValueError('native validation source hash mismatch')
    validate_axis_riser_attributes(g,native_doc,native_source_sha256)
    validate_full_batch_plan_attributes(g,native_doc,native_source_sha256)
    nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']}
    if len(nodes)!=len(g['nodes']) or len(edges)!=len(g['edges']):raise ValueError('Duplicate graph IDs')
    for node in nodes.values():
        if node.get('system') and node['system'] not in g['systems']:
            raise ValueError('Node hidden by missing system filter: '+node['node_id'])
    instance_ids=[d['id'] for d in g['instances']]
    if len(instance_ids)!=len(set(instance_ids)):raise ValueError('Duplicate instance IDs')
    actual=Counter();expected=Counter();actual_names={};expected_names={};adj=Counter();port_ids=[]
    for e in edges.values():
        if e['start_node_id'] not in nodes or e['end_node_id'] not in nodes:raise ValueError('Missing endpoint node')
        adj.update((e['start_node_id'],e['end_node_id']))
        if e['system'] not in g['systems']:raise ValueError('Unknown edge system')
        if e.get('path_length') is None:
            evidence=e.get('calculation_source_length_evidence')
            if ('path_length' not in e or e.get('path_length_complete') is not False or e.get('path_length_scope')!='sum_of_source_edge_lengths_no_display_connector' or
                not isinstance(evidence,list) or len(evidence)<2 or not all(isinstance(x,dict) for x in evidence) or
                not any(x.get('recorded_source_length') is None for x in evidence)):
                raise ValueError('Unknown length lacks incomplete calculation source evidence')
        inferred=(e.get('source_path_status')=='user_confirmed_overlay_no_native_supply_path' and e.get('connection_mode')=='user_confirmed_overlaid_supply' and e.get('path_length_complete') is False and e.get('physical_length')=='unknown' and e.get('path_length')==0 and not e.get('source_handles'))
        known,unknown=partition_source_coverage(e,native_doc,m['sourceHashes']['main_dxf'])
        if e.get('source_path_coverage') and e['source_path_coverage'].get('source_sha256')!=m['sourceHashes']['main_dxf']:raise ValueError('Partial coverage source hash mismatch')
        extra=e.get('deviceSourcePaths',[]);ext=e.get('source_device_extension');exploded=e.get('source_exploded_device_chain')
        if ext and exploded:raise ValueError('Multiple device source path types')
        if ext:
            if ext.get('source_sha256')!=m['sourceHashes']['main_dxf'] or ext.get('changes_topology') is not False or ext.get('physical_port_verified') is not False or ext.get('physical_length')!='unknown' or len(extra)!=1 or len(extra[0])!=2:raise ValueError('Invalid device source path')
        elif exploded:
            if exploded.get('source_sha256')!=m['sourceHashes']['main_dxf'] or exploded.get('physical_port_verified') is not False or exploded.get('physical_length')!='unknown' or exploded.get('additional_line_length_not_added') is not True or len(extra)!=1 or len(extra[0])!=2:raise ValueError('Invalid exploded device source path')
        elif extra:raise ValueError('Device source path lacks source evidence')
        if (not e['sourcePaths'] and not inferred) or len(e['sourcePaths'])!=len(known) or len(e.get('unverifiedPaths',[]))!=len(unknown):raise ValueError('Source path coverage changed')
        transform=g['transform'];project=lambda p:[(p[0]-transform['originX'])/transform['scale'],(transform['originY']-p[1])/transform['scale']]
        if exploded and any(math.dist(project(x),y)>1e-6 for x,y in zip(exploded['inner_line_endpoints'],extra[0])):raise ValueError('Exploded device source path coordinates changed')
        for expected_paths,actual_paths in ((known,e['sourcePaths']),(unknown,e.get('unverifiedPaths',[]))):
            if any(len(a)!=len(b) or any(math.dist(project(x),y)>1e-6 for x,y in zip(a,b)) for a,b in zip(expected_paths,actual_paths)):raise ValueError('Source path coordinates changed')
        for path in [e['points']]+e['sourcePaths']+e.get('unverifiedPaths',[])+extra:
            if len(path)<2 or any(not math.isfinite(v) for p in path for v in p):raise ValueError('Invalid geometry')
        for item in e.get('equipment_inventory',[]):
            key=(e['edge_id'],item['type']);expected[key]+=int(item['count'])
            expected_names.setdefault(key,Counter()).update(item['device_names'])
        port_ids.extend(p for p in (e.get('start_port_id'),e.get('end_port_id')) if p)
    for d in g['instances']:
        if d['edge_id'] not in edges or d['assignment_status']!='assigned':raise ValueError('Unassigned instance')
        if d['type'] not in g['symbols']:raise ValueError('Device symbol missing')
        if re.search('[\u3400-\u9fff]',d['name']):raise ValueError('Non-English instance name: provide a full alias adapter')
        actual[d['edge_id'],d['type']]+=1
        actual_names.setdefault((d['edge_id'],d['type']),Counter()).update([d['name']])
    if actual!=+expected:raise ValueError('Inventory and per-instance counts differ')
    if actual_names!=expected_names:raise ValueError('Inventory and instance names differ')
    if len({d['name'] for d in g['instances']})!=len(g['instances']):raise ValueError('Duplicate English instance names')
    declared=[]
    for n in nodes.values():
        for p in n.get('ports',[]):
            declared.append(p['port_id'])
            if port_ids.count(p['port_id'])!=1:raise ValueError('Port does not have one adjacent edge')
    if len(set(declared))!=len(declared) or set(declared)!=set(port_ids):raise ValueError('Port identities or coverage differ')
    if len(declared)!=len(g['ports']):raise ValueError('Port table and node ports differ')
    if set(declared)!={p['port_id'] for p in g['ports']}:raise ValueError('Port table identities differ')
    owners={p['port_id']:n['node_id'] for n in nodes.values() for p in n.get('ports',[])}
    if any(p['node_id']!=owners[p['port_id']] for p in g['ports']):raise ValueError('Port table owner differs from the incident virtual node')
    expected_reviews={n['node_id'] for n in nodes.values() if (n['node_type']=='physical_junction' and adj[n['node_id']]!=3)or n.get('boundary_type')=='unresolved_source_terminal'or n.get('review_queue')=='source_comparison'or n.get('system_review_required')or n.get('interface_destination')}
    if {r['id'] for r in g['review']}!=expected_reviews:raise ValueError('Automatic topology hint list differs from graph')
    expected_component_hints={d['id']for d in g['instances']if str(d.get('source_head_status','')).startswith('pending_')or d.get('source_service_tag_conflict')}
    if {r['id']for r in g.get('componentReview',[])}!=expected_component_hints:raise ValueError('Component completeness hints differ from instance audit')
    for n in g['nodes']:
        if n['node_type']=='equipment' and n.get('symbol_key','EQUIPMENT') not in g['symbols']:raise ValueError('Equipment symbol missing')
    for s in g['symbols'].values():
        if not s['markup'] or s['primitiveCount']<1:raise ValueError('Empty symbol geometry')
        ET.fromstring('<svg>'+s['markup']+'</svg>')
    ET.parse(root/'public/data/cad.svg')
    if m.get('buildingContext'):
        from architecture_context import validate_context
        a=json.loads((root/'public/data/architecture.json').read_text(encoding='utf8'))
        validate_context(a,g)
        ET.parse(root/'public/data/architecture.svg')
    index=(root/'public/index.html').read_text(encoding='utf8')
    if m['bundleId'] not in index or '__BUILD_ID__' in index:raise ValueError('Missing build identity')
    if {str(n['floor']) for n in nodes.values()}!={f['id'] for f in g['floors']}:raise ValueError('Floor coverage differs')
    observed={'nodes':len(nodes),'edges':len(edges),'instances':len(g['instances']),'ports':len(declared),'reviews':len(g['review'])}
    for key,v in observed.items():
        if m[key]!=v:raise ValueError(f'Manifest count differs: {key}')
    for p in (root/'public').glob('*'):
        if p.suffix in ('.html','.js','.css') and re.search('[\u3400-\u9fff]',p.read_text(encoding='utf8')):
            raise ValueError(f'Non-English template text in {p.name}')
    return {'status':'passed','checks':['unique IDs','valid endpoints','finite paths','source-path coverage','instance assignments','inventory reconciliation','explicit port bindings','degree review reconciliation','source symbol vectors','CAD XML','manifest counts','floor coverage','build identity','English template labels'],**observed}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('--native-dxf',type=Path);a=p.parse_args()
    try:
        doc=None;source_hash=None
        if a.native_dxf:
            import ezdxf,hashlib
            source_hash=hashlib.sha256(a.native_dxf.read_bytes()).hexdigest();doc=ezdxf.readfile(a.native_dxf,errors='strict')
        print(json.dumps(validate_bundle(a.bundle,native_doc=doc,native_source_sha256=source_hash),indent=2))
    except (ValueError,KeyError,TypeError,OSError,ET.ParseError) as e:p.exit(1,f'VALIDATION FAILED: {e}\n')
