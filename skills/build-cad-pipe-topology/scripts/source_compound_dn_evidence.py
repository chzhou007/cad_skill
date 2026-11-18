"""Inventory slash-separated DN labels without binding either value to a pipe."""
import argparse,hashlib,json,re
from pathlib import Path
from pipe_annotation_attributes import parse_dn_annotation,source_texts
from source_dn_annotation_risks import scan
from source_readability import read_source


def parse(text):
    if not isinstance(text,str):return None
    parts=re.split(r'\s*/\s*',text.strip())
    if len(parts)!=2:return None
    values=[parse_dn_annotation(p) for p in parts]
    if any(v is None for v in values):return None
    return [{'order_in_text':i+1,'nominal_mm':v['nominal_mm'],'parenthesized_source_value':v['parenthesized_source_value']} for i,v in enumerate(values)]


def extract(texts,edges,layers):
    risk=scan(texts,edges,layers);rows=[]
    for x in risk['observations']:
        values=parse(x['source_text']['text'])
        if values is None:continue
        rows.append({'source_text':x['source_text'],'values_in_text_order':values,'candidate_edge_ids':x['geometric_candidate_edge_ids'],'status':'compound_values_unbound','edge_binding_confirmed':False,'parenthesized_value_meaning':'uninterpreted','human_accepted':False})
    return {'status':'compound_dn_text_evidence_not_binding','records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Only slash-separated pairs of whole single-DN annotations are parsed; other compound or multiline formats remain out of scope.','Text order, proximity and parenthesized values do not establish pipe order, system, elevation, reducer or edge-wide diameter.','Modelspace text on explicitly selected layers only; duplicates and detail/main relationships are preserved.']}


def main():
    p=argparse.ArgumentParser()
    for name in ('source','graph','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--text-layer',required=True,action='append');a=p.parse_args();doc,proof=read_source(a.source);raw=a.graph.read_bytes();graph=json.loads(raw)
    if graph.get('metadata',{}).get('source_sha256')!=proof['source_sha256']:raise ValueError('source hash mismatch')
    result=extract(source_texts(doc,a.source.stem,proof['source_sha256']),graph['edges'],set(a.text_layer));result.update(source_sha256=proof['source_sha256'],graph_sha256=hashlib.sha256(raw).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_preflight=proof,text_layers=sorted(set(a.text_layer)))
    with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'records':len(result['records'])}))
if __name__=='__main__':main()
