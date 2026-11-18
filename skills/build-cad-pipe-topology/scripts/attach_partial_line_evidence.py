"""Attach source-recomputed partial LINE overlap as unaccepted edge evidence."""
import argparse,copy,hashlib,json
from pathlib import Path
from partial_native_line_coverage import audit
from source_readability import read_source


def attach(doc,graph,coverage,screen,policy,source_hash,graph_hash,coverage_hash,screen_hash):
    expected=audit(doc,graph,coverage,policy,source_hash,graph_hash,coverage_hash)
    for k in ('status','source_sha256','graph_sha256','coverage_sha256','records','graph_mutated','human_accepted','hil_ready'):
        if expected[k]!=screen.get(k):raise ValueError('partial line screen mismatch: '+k)
    if any('_partial_line_rows' in e for e in graph['edges']):raise ValueError('reserved temporary field')
    g=copy.deepcopy(graph);edges={e['edge_id']:e for e in g['edges']};count=0
    for record in expected['records']:
        # Only add information beyond the prior whole-segment check; fully
        # unwitnessed or ambiguous intervals remain in the existing audit.
        if record['unique_source_drawing_length']<=.05:continue
        e=edges[record['edge_id']]
        if e.get('path_length_complete') is not False or e.get('physical_length')!='unknown':raise ValueError('edge must retain unknown length')
        if e.get('source_partial_line_evidence') is not None:raise ValueError('edge already has partial line evidence')
        e.setdefault('_partial_line_rows',[]).append(copy.deepcopy(record));count+=1
    if not count:raise ValueError('no partial overlaps to attach')
    for e in g['edges']:
        rows=e.pop('_partial_line_rows',None)
        if rows is not None:e['source_partial_line_evidence']={'source_sha256':source_hash,'input_graph_sha256':graph_hash,'coverage_sha256':coverage_hash,'screen_sha256':screen_hash,'status':'partial_source_overlap_candidate_not_physical_length','records':rows,'physical_length':'unknown','connection_confirmed':False,'human_accepted':False}
    g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed_after_source_evidence_change')
    return g,{'status':'partial_line_evidence_attached_not_accepted','source_sha256':source_hash,'input_graph_sha256':graph_hash,'coverage_sha256':coverage_hash,'screen_sha256':screen_hash,'attached_segments':count,'physical_length_changed':False,'connectivity_changed':False,'review_inherited':False,'hil_ready':False}


def main():
    p=argparse.ArgumentParser()
    for name in ('source','graph','coverage','screen','policy','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));doc,proof=read_source(a.source)
    graph,report=attach(doc,load(a.graph),load(a.coverage),load(a.screen),load(a.policy),proof['source_sha256'],sha(a.graph),sha(a.coverage),sha(a.screen));a.output.mkdir(parents=True,exist_ok=False)
    out=a.output/'graph_with_edges.json';out.write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n',encoding='utf8');report.update(output_graph_sha256=sha(out),policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)));(a.output/'partial_line_attachment_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':report['status'],'segments':report['attached_segments']}))
if __name__=='__main__':main()
