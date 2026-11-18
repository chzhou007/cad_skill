"""Independently validate and classify inline source-system conflicts, read-only."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from native_line_path_evidence import LAYERS, _on
from source_readability import read_source

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def triage(doc, graph, source_sha256, tol=.05):
    if graph.get('sourceInlineOwnershipRepair',{}).get('source_sha256')!=source_sha256:
        raise ValueError('source does not match ownership audit')
    if not math.isfinite(tol) or not 0<tol<=.05:
        raise ValueError('invalid tolerance')
    edges={e['edge_id']:e for e in graph['edges']}
    if len(edges)!=len(graph['edges']):raise ValueError('duplicate edge IDs')
    layers={v:k for k,v in LAYERS.items()};results=[]
    conflicts=graph.get('sourceInlineSystemConflicts')
    if not isinstance(conflicts,list):raise ValueError('missing conflict inventory')
    for c in conflicts:
        if c.get('status')!='source_system_conflict':raise ValueError('unexpected conflict status')
        joint=doc.entitydb.get(c['joint_handle']);assigned=edges.get(c['assigned_edge_id'])
        if joint is None or joint.dxftype()!='INSERT' or joint not in doc.modelspace() or assigned is None:
            raise ValueError('missing native joint or assigned edge')
        glyph=list(joint.virtual_entities());bars=[x for x in glyph if x.dxftype()=='LINE']
        if len(bars)!=2 or len(glyph)!=6 or sum(x.dxftype()=='ARC' for x in glyph)!=4:
            raise ValueError('unexpected joint shape')
        actual=[tuple((x.dxf.start+x.dxf.end)/2) for x in bars];contacts=[]
        for contact in c['contacts']:
            midpoint=contact['midpoint']
            if sum(math.dist(midpoint,p)<=tol for p in actual)!=1:raise ValueError('stale joint contact')
            lines=[]
            for old in contact['lines']:
                line=doc.entitydb.get(old['source_handle'])
                if line is None or line.dxftype()!='LINE' or line not in doc.modelspace():raise ValueError('missing native pipe')
                system=layers.get(line.dxf.layer)
                if system!=old['system'] or min(math.dist(midpoint,tuple(line.dxf.start)),math.dist(midpoint,tuple(line.dxf.end)))>tol:raise ValueError('stale source pipe contact')
                if math.dist(old['line_start'],tuple(line.dxf.start))>tol or math.dist(old['line_end'],tuple(line.dxf.end))>tol:raise ValueError('stale pipe geometry')
                witnesses=[];a=tuple(line.dxf.start)[:2];b=tuple(line.dxf.end)[:2]
                for e in edges.values():
                    if e.get('system')==system and any(_on(a,u,v,tol) and _on(b,u,v,tol) for path in e.get('attribute_paths',[]) for u,v in zip(path,path[1:])):
                        witnesses.append(e['edge_id'])
                if sorted(witnesses)!=sorted(old['graph_edges']):raise ValueError('stale graph witness')
                lines.append({'source_handle':line.dxf.handle,'source_layer':line.dxf.layer,'system':system,'graph_edges':sorted(witnesses)})
            contacts.append({'midpoint':midpoint,'lines':lines})
        if len(contacts)!=2 or any(len(x['lines'])!=1 for x in contacts):raise ValueError('ambiguous joint contacts')
        if math.dist(contacts[0]['midpoint'],contacts[1]['midpoint'])<=tol:raise ValueError('duplicate joint contact')
        if len({x['lines'][0]['system'] for x in contacts})!=2:raise ValueError('source systems no longer conflict')
        witness_ids=sorted({e for x in contacts for e in x['lines'][0]['graph_edges']})
        if witness_ids!=sorted(c['witness_edge_ids']):raise ValueError('conflict witness changed')
        if len(witness_ids)!=1:category='ambiguous_or_no_witness'
        else:
            target=edges[witness_ids[0]]
            if target['edge_id']==assigned['edge_id']:category='assigned_edge_matches_one_contact_system_conflict_remains'
            elif target.get('device_label')==assigned.get('device_label') and target.get('device_label'):
                category='different_edge_same_device_system_conflict_remains'
            else:category='different_edge_different_device_system_conflict_remains'
        results.append({'joint_handle':c['joint_handle'],'component_name':c['device_name'],
            'assigned_edge_id':assigned['edge_id'],'assigned_system':assigned.get('system'),
            'assigned_device_label':assigned.get('device_label'),'contacts':contacts,'witness_edge_ids':witness_ids,
            'witness_device_labels':[edges[x].get('device_label') for x in witness_ids],
            'classification':category,'resolution':'unresolved','human_accepted':False})
    return {'source_sha256':source_sha256,'status':'read_only_triage_not_repair',
            'records':results,'graph_mutated':False,'hil_ready':False,
            'limitations':['One source-supported edge does not prove joint ownership or settle the conflicting system of the other contact.',
                           'A matching device label is not proof of physical port or inter-view correspondence.']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','graph','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();doc,proof=read_source(a.source);graph=json.loads(a.graph.read_text(encoding='utf8'))
    result=triage(doc,graph,proof['source_sha256']);result.update(graph_sha256=digest(a.graph),script_sha256=digest(__file__),source_preflight=proof)
    with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'records':len(result['records']),'status':result['status']}))
if __name__=='__main__':main()
