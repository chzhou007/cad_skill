"""Validate generated data, geometry references and bundle completeness."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

def validate_bundle(root):
    root=Path(root)
    for name in ('public/index.html','public/app.js','public/core.js','public/style.css','public/polish.css','public/hil.js','public/hil.css','hil_server.py','public/data/graph.json','public/data/cad.svg','public/data/manifest.json','serve.py','start.cmd','README.md','visualization-config.json'):
        if not (root/name).is_file():raise ValueError(f'Missing viewer output {name}')
    g=json.loads((root/'public/data/graph.json').read_text(encoding='utf8'))
    m=json.loads((root/'public/data/manifest.json').read_text(encoding='utf8'))
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
        if not e['sourcePaths'] or len(e['sourcePaths'])!=len(e['attribute_paths']):raise ValueError('Source path coverage changed')
        for path in [e['points']]+e['sourcePaths']:
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
    expected_reviews={n['node_id'] for n in nodes.values() if (n['node_type']=='physical_junction' and adj[n['node_id']]!=3)or n.get('boundary_type')=='unresolved_source_terminal'or n.get('system_review_required')or n.get('interface_destination')}
    if {r['id'] for r in g['review']}!=expected_reviews:raise ValueError('Automatic topology hint list differs from graph')
    expected_component_hints={d['id']for d in g['instances']if str(d.get('source_head_status','')).startswith('pending_')}
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);a=p.parse_args()
    try:print(json.dumps(validate_bundle(a.bundle),indent=2))
    except (ValueError,KeyError,TypeError,OSError,ET.ParseError) as e:p.exit(1,f'VALIDATION FAILED: {e}\n')
