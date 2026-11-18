"""Compare ambiguous native mains without deciding physical pipe identity."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from source_readability import read_source


def same_line(a,b,tol):
    if a.dxftype()!='LINE' or b.dxftype()!='LINE' or a.dxf.layer!=b.dxf.layer:return False
    ap=(a.dxf.start,a.dxf.end);bp=(b.dxf.start,b.dxf.end)
    if not all(math.isfinite(v) for p in (*ap,*bp) for v in p):raise ValueError('nonfinite source line')
    return min(max(math.dist(ap[0],bp[0]),math.dist(ap[1],bp[1])),
               max(math.dist(ap[0],bp[1]),math.dist(ap[1],bp[0])))<=tol


def diagnose(doc,graph,screen,source_sha256,graph_sha256,tol=.05):
    if (graph.get('metadata',{}).get('source_sha256')!=source_sha256 or
        screen.get('source_sha256')!=source_sha256 or screen.get('graph_sha256')!=graph_sha256):
        raise ValueError('stale source or graph')
    if not math.isfinite(tol) or tol<=0:raise ValueError('invalid tolerance')
    if not isinstance(screen.get('ambiguous_native_geometry'),list):raise ValueError('missing ambiguous source geometry inventory')
    records=[]
    for candidate in screen.get('ambiguous_native_geometry',[]):
        handles=candidate.get('main_handles',[]);branches=candidate.get('branch_handles',[])
        if len(handles)<2 or len(set(handles))!=len(handles) or not branches:raise ValueError('invalid ambiguous main inventory')
        lines=[doc.entitydb.get(h) for h in handles];symbol=doc.entitydb.get(candidate.get('circle_handle'))
        if any(e is None or e not in doc.modelspace() or e.dxftype()!='LINE' for e in lines) or symbol is None or symbol not in doc.modelspace() or symbol.dxftype()!='CIRCLE':
            raise ValueError('missing native entity')
        if any(doc.entitydb.get(h) is None or doc.entitydb[h] not in doc.modelspace() or doc.entitydb[h].dxftype()!='LINE' for h in branches):raise ValueError('missing native branch')
        groups=[]
        for handle,line in zip(handles,lines):
            matches=[group for group in groups if same_line(line,doc.entitydb[group[0]],tol)]
            if len(matches)>1:raise ValueError('ambiguous tolerance grouping')
            if matches:
                if not all(same_line(line,doc.entitydb[h],tol) for h in matches[0]):raise ValueError('nontransitive tolerance grouping')
                matches[0].append(handle)
            else:groups.append([handle])
        owners={h:[e['edge_id'] for e in graph['edges'] if h in e.get('source_handles',[])] for h in handles}
        branch_owners={h:[e['edge_id'] for e in graph['edges'] if h in e.get('source_handles',[])] for h in branches}
        # Graph incidence is separate from the native lines' physical identity.
        # An existing same-system three-way node is evidence of what the graph
        # currently contains, not proof that the source interpretation is right.
        junctions=[]
        for node in graph.get('nodes',[]):
            if node.get('node_type')!='tee' or node.get('system')!=candidate.get('system'):continue
            if math.dist((node['x'],node['y']),(symbol.dxf.center.x,symbol.dxf.center.y))>tol:continue
            incident=[e for e in graph['edges'] if node['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
            if len(incident)!=3 or any(e.get('system')!=candidate['system'] for e in incident):continue
            main=[e for e in incident if set(handles).intersection(e.get('source_handles',[]))]
            branch=[e for e in incident if set(branches).intersection(e.get('source_handles',[]))]
            if len(main)==2 and len(branch)==1 and branch[0] not in main:
                junctions.append({'node_id':node['node_id'],'edge_ids':[e['edge_id'] for e in incident]})
        records.append({'circle_handle':candidate['circle_handle'],'system':candidate.get('system'),
            'main_handles':handles,'branch_handles':branches,'native_same_layer_3d_groups':groups,
            'main_graph_edge_references':owners,'branch_graph_edge_references':branch_owners,
            'graph_junction_state':'existing_same_system_three_way_unreviewed' if len(junctions)==1 else 'not_proven_or_ambiguous',
            'graph_junction_candidates':junctions,
            'status':'source_geometry_comparison_only_identity_and_connection_pending'})
    return {'status':'source_geometry_diagnostic_not_connectivity_proof','source_sha256':source_sha256,
            'graph_sha256':graph_sha256,'tolerance_native_units':tol,'records':records,
            'physical_identity_resolved':False,'graph_mutated':False,'hil_ready':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','graph','screen','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    doc,proof=read_source(a.source);graph=json.loads(a.graph.read_text(encoding='utf8'));screen=json.loads(a.screen.read_text(encoding='utf8'))
    report=diagnose(doc,graph,screen,proof['source_sha256'],sha(a.graph));report['screen_sha256']=sha(a.screen);report['source_preflight']=proof
    with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'records':len(report['records']),'graph_mutated':False,'hil_ready':False}))

if __name__=='__main__':main()
