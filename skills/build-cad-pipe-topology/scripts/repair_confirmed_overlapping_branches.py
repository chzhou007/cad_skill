"""Repair individually confirmed plan branches hidden by overlapping mains.

Visual connectors are symbolic only; neither their geometry nor their length
is physical source evidence. A policy names every branch and native circle.
"""
import argparse
import collections
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
from edge_endpoint_semantics import reconcile
from repair_confirmed_circle_junctions import TOL, assign_sources, pos, segments_for_interval, slice_path
from source_readability import read_source


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def apply(doc, graph, rows, policy, source_hash, graph_hash, evidence_hash):
    if (policy.get('source_sha256') != source_hash or policy.get('graph_sha256') != graph_hash or
        graph.get('metadata', {}).get('source_sha256') != source_hash or policy.get('evidence_manifest_sha256') != evidence_hash):
        raise ValueError('source, graph or evidence identity mismatch')
    if policy.get('confirmed_by') != 'user':
        raise ValueError('explicit user confirmation required')
    selected = policy.get('connections')
    if not isinstance(selected, list) or not selected:
        raise ValueError('empty connection selection')
    g = copy.deepcopy(graph)
    nodes = {n['node_id']: n for n in g['nodes']}
    edges = {e['edge_id']: e for e in g['edges']}
    if len(nodes) != len(g['nodes']) or len(edges) != len(g['edges']):
        raise ValueError('duplicate graph IDs')
    grouped = collections.defaultdict(list)
    used_terminals, used_branches, used_circles = set(), set(), set()
    for c in selected:
        main, branch, terminal = edges[c['main_edge']], edges[c['branch_edge']], nodes[c['terminal']]
        circle = doc.entitydb.get(c['circle_handle'])
        main_line = doc.entitydb.get(c['main_handle'])
        branch_line = doc.entitydb.get(c['branch_handle'])
        if not circle or circle.dxftype() != 'CIRCLE' or not main_line or main_line.dxftype() != 'LINE' or not branch_line or branch_line.dxftype() != 'LINE':
            raise ValueError('native circle or line missing')
        if main_line.dxf.layer != c['pipe_layer'] or branch_line.dxf.layer != c['pipe_layer']:
            raise ValueError('native pipe layer mismatch')
        if main['system'] != c['system'] or branch['system'] != c['system'] or terminal.get('system') != c['system']:
            raise ValueError('system mismatch')
        if c['main_handle'] not in main['source_handles'] or c['branch_handle'] not in branch['source_handles']:
            raise ValueError('graph source mismatch')
        if terminal.get('subtype') != 'unresolved_source_terminal' or sum(terminal['node_id'] in (e.get('start_node_id'), e.get('end_node_id')) for e in edges.values()) != 1:
            raise ValueError('terminal not unique unresolved endpoint')
        if c['terminal'] in used_terminals or c['branch_edge'] in used_branches or c['circle_handle'] in used_circles:
            raise ValueError('duplicate branch, terminal or circle')
        used_terminals.add(c['terminal']); used_branches.add(c['branch_edge']); used_circles.add(c['circle_handle'])
        point = [terminal['x'], terminal['y']]
        if min(math.dist(point, [v.x, v.y]) for v in (branch_line.dxf.start, branch_line.dxf.end)) > TOL:
            raise ValueError('terminal not at native branch endpoint')
        center = [circle.dxf.center.x, circle.dxf.center.y]
        if math.dist(center, c['circle_center']) > TOL or abs(circle.dxf.radius-c['circle_radius']) > TOL:
            raise ValueError('circle geometry mismatch')
        pos([[main_line.dxf.start.x, main_line.dxf.start.y], [main_line.dxf.end.x, main_line.dxf.end.y]], center)
        cut = pos(main['path'], center)
        length = sum(math.dist(a,b) for a,b in zip(main['path'],main['path'][1:]))
        if cut <= TOL or cut >= length-TOL:
            raise ValueError('circle not in main interior')
        if c.get('connection_mode') not in ('native_circle_rim', 'user_confirmed_hidden_overlap'):
            raise ValueError('invalid connection mode')
        if c['connection_mode'] == 'native_circle_rim' and abs(math.dist(point,center)-circle.dxf.radius) > TOL:
            raise ValueError('branch not at circle rim')
        grouped[main['edge_id']].append((cut,c,point,center,circle.dxf.layer))
    records = []
    for main_id, items in grouped.items():
        items.sort(key=lambda x:x[0]); main = edges.pop(main_id); path = main['path']
        total = sum(math.dist(a,b) for a,b in zip(path,path[1:])); cuts = [0]+[x[0] for x in items]+[total]
        if any(b-a <= TOL for a,b in zip(cuts,cuts[1:])):
            raise ValueError('ambiguous coincident circle cuts')
        if any(k.startswith('diameter_') or k in ('pipe_diameter','source_segment_dimensions','physical_length','physical_length_mm') for k in main):
            raise ValueError('split attributes require remapping')
        if main.get('equipment_names') or main.get('equipment_counts') or main.get('source_flexible_joints') or any(r.get('edge_id') == main_id for r in rows):
            raise ValueError('main components require remapping')
        tees = ['T-OVERLAP-'+x[1]['circle_handle'] for x in items]
        child_ids = [main_id]+['E-OVERLAP-'+x[1]['circle_handle'] for x in items]
        if any(t in nodes for t in tees) or any(i in edges for i in child_ids):
            raise ValueError('new ID collision')
        ends = [main['start_node_id']]+tees+[main['end_node_id']]
        children=[]
        for i,(lo,hi) in enumerate(zip(cuts,cuts[1:])):
            e=copy.deepcopy(main);e['edge_id']=child_ids[i];e['start_node_id']=ends[i];e['end_node_id']=ends[i+1]
            if i:e.pop('start_port_id',None)
            if i<len(child_ids)-1:e.pop('end_port_id',None)
            e['path']=slice_path(path,lo,hi);e['path_points']=copy.deepcopy(e['path']);e['attribute_paths']=segments_for_interval(path,main['attribute_paths'],lo,hi)
            if not e['attribute_paths']:raise ValueError('split missing native path')
            e['source_handles']=assign_sources(doc,main['source_handles'],e['attribute_paths'])
            e['path_length']=sum(math.dist(a,b) for part in e['attribute_paths'] for a,b in zip(part,part[1:]));e['split_source_edge']={'edge_id':main_id,'source_graph_sha256':graph_hash,'interval_native_units':[lo,hi]};children.append(e)
        if abs(sum(e['path_length'] for e in children)-main['path_length'])>TOL or set(h for e in children for h in e['source_handles'])!=set(main['source_handles']):
            raise ValueError('main source coverage not conserved')
        for e in children:edges[e['edge_id']]=e
        for (_,c,point,center,circle_layer),tee in zip(items,tees):
            branch=edges[c['branch_edge']]; terminal=nodes.pop(c['terminal'])
            side='start' if branch['start_node_id']==c['terminal'] else 'end' if branch['end_node_id']==c['terminal'] else None
            if not side or math.dist(branch['path'][0 if side=='start' else -1],point)>TOL:
                raise ValueError('branch path endpoint mismatch')
            # A display-only orthogonal connector can overlap a native main. It
            # must not create junctions at incidental geometric intersections.
            route = c['display_route']
            if not isinstance(route,list) or len(route)<2 or math.dist(route[0],point)>TOL or math.dist(route[-1],center)>TOL:
                raise ValueError('display route does not join confirmed endpoints')
            if any(math.dist(a,b)<=TOL for a,b in zip(route,route[1:])):
                raise ValueError('zero display segment')
            branch[side+'_node_id']=tee;branch.pop(side+'_port_id',None)
            branch['path']=(list(reversed(route[1:]))+branch['path']) if side=='start' else (branch['path']+route[1:])
            branch['path_points']=copy.deepcopy(branch['path']);branch['path_length_complete']=False
            branch['path_length_scope']='prior_graph_drawing_length_source_coverage_unverified_hidden_connection_unknown'
            branch['physical_length']='unknown'
            evidence={'circle_handle':c['circle_handle'],'circle_layer':circle_layer,'main_handle':c['main_handle'],'branch_handle':c['branch_handle'],'mode':c['connection_mode'],'source_graph_sha256':graph_hash,'user_evidence_manifest_sha256':evidence_hash,'display_route':route,'route_is_physical':False,'physical_length':'unknown'}
            branch['user_confirmed_overlap_connection']=evidence
            nodes[tee]={'node_id':tee,'node_type':'tee','subtype':'physical_tee','floor':terminal['floor'],'system':c['system'],'x':center[0],'y':center[1],'label':tee,'source_handles':[c['circle_handle'],c['main_handle'],c['branch_handle']],'user_confirmed_overlap_connection':evidence}
            records.append({'circle_handle':c['circle_handle'],'tee':tee,'retired_terminal':c['terminal'],'branch_edge':c['branch_edge'],'main_edge':main_id,'main_child_edges':child_ids,'system':c['system']})
    g['nodes'],g['edges']=list(nodes.values()),list(edges.values())
    g['virtual_equipment_ports']=[p for p in g.get('virtual_equipment_ports',[]) if p.get('virtual_equipment_id') not in used_terminals]
    g,changes=reconcile(g)
    for r in records:
        incident=[e for e in g['edges'] if r['tee'] in (e['start_node_id'],e['end_node_id'])]
        if len(incident)!=3 or any(e['system']!=r['system'] for e in incident):raise ValueError('tee invariant failed')
    g['userConfirmedOverlappingBranches']={'records':records,'source_sha256':source_hash,'input_graph_sha256':graph_hash,'evidence_manifest_sha256':evidence_hash,'physical_length':'unknown'}
    if graph.get('userConfirmedOverlappingBranches'):
        g['userConfirmedOverlappingBranches']['previous_repair']=copy.deepcopy(graph['userConfirmedOverlappingBranches'])
    # A previous source conflict is intentionally retained until its complete
    # interpretation has passed a fresh source comparison.
    g['preHilComparison']={'status':'pending','previous_comparison':copy.deepcopy(graph.get('preHilComparison')),'reason':'confirmed overlapping branches require fresh source comparison and conflict reconciliation'}
    g['metadata'].update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_semantic_change')
    return g,{'records':records,'endpoint_changes':changes,'hil_ready':False}


def main():
    p=argparse.ArgumentParser()
    for k in ('source','graph','devices','policy','evidence-manifest','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('output exists')
    policy=json.loads(a.policy.read_text(encoding='utf8')); evidence=json.loads(a.evidence_manifest.read_text(encoding='utf8'))
    if policy.get('devices_sha256')!=sha(a.devices):raise ValueError('device identity mismatch')
    if not evidence.get('items') or any(sha(x['path'])!=x['sha256'] for x in evidence['items']):raise ValueError('evidence file identity mismatch')
    doc,proof=read_source(a.source);graph=json.loads(a.graph.read_text(encoding='utf8'))
    with a.devices.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    g,audit=apply(doc,graph,rows,policy,proof['source_sha256'],sha(a.graph),sha(a.evidence_manifest))
    a.output.mkdir(parents=True);target=a.output/'graph_with_confirmed_overlapping_branches.json';target.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with (a.output/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    audit.update(output_graph_sha256=sha(target),policy_sha256=sha(a.policy),script_sha256=sha(__file__),input_devices_sha256=sha(a.devices))
    (a.output/'confirmed-overlapping-branches-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'connections':len(audit['records']),'output_graph_sha256':sha(target),'hil_ready':False}))


if __name__=='__main__':main()
