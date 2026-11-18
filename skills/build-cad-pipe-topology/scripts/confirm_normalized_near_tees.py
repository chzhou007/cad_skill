"""Close only explicitly answered normalized contacts; keep unrelated reviews."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
from screen_applied_near_tees import screen
from source_readability import read_source

DECISION='接入同系统主管，供回水独立'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))


def confirm(doc,graph,normalization,policy,reply,hashes):
    evidence=screen(doc,graph,normalization,policy,hashes)
    questions={q['id']:q for section in reply['sections'] for q in section['questions']}
    images={q['id']:section['image']['sha256'] for section in reply['sections'] for q in section['questions']}
    if len(questions)!=sum(len(section['questions']) for section in reply['sections']):raise ValueError('duplicate reply IDs')
    out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};records=[];history=[]
    for item,spec in zip(evidence['records'],policy['selections']):
        q=questions.get(spec['question_id']);n=nodes[item['node_id']];old=n.get('source_near_tee_evidence') or {}
        if (not q or q.get('answer',{}).get('decision')!=DECISION or item['branch_handle'] not in q['text']
            or item['main_handle'] not in q['text'] or images[q['id']]!=policy['pair_sha256']):
            raise ValueError('missing exact native Pair confirmation')
        if (n.get('resolution_state')!='source_contact_reconstructed_pending_comparison' or n.get('review_required') is not True
            or old.get('source_sha256')!=hashes['source_sha256'] or old.get('branch_handle')!=item['branch_handle']
            or old.get('main_handle')!=item['main_handle'] or old.get('incident_edge_ids')!=item['incident_edge_ids']):
            raise ValueError('pending native incidence changed')
        history.append(dict(node_id=n['node_id'],resolution_state=n['resolution_state'],review_required=n['review_required'],source_near_tee_evidence=copy.deepcopy(old)))
        proof=dict(status='user_confirmed_normalized_source_tee',source_sha256=hashes['source_sha256'],input_graph_sha256=hashes['graph_sha256'],
             normalization_sha256=hashes['normalization_sha256'],branch_handle=item['branch_handle'],main_handle=item['main_handle'],
             incident_edge_ids=item['incident_edge_ids'],question_id=q['id'],question=q['text'],explicit_answer=q['answer'],
             reply_sha256=policy['reply_sha256'],pair_sha256=policy['pair_sha256'],physical_length='unknown',whole_graph_accepted=False)
        n.update(resolution_state='source_contact_reconstructed_user_confirmed',review_required=False,source_near_tee_confirmation=proof)
        records.append(dict(node_id=n['node_id'],question_id=q['id'],branch_handle=item['branch_handle'],main_handle=item['main_handle'],incident_edge_ids=item['incident_edge_ids']))
    remaining=[n['node_id'] for n in out['nodes'] if n.get('resolution_state')=='source_contact_reconstructed_pending_comparison']
    def close_family(comparison):
        if not isinstance(comparison,dict):return
        if not remaining:
            for family in comparison.get('families',[]):
                if family.get('id')=='normalized-near-tee':family.update(status='resolved',disposition='Scoped explicit Pair answers replayed against native lines and normalization; other families unchanged.')
        close_family(comparison.get('previous_comparison'))
    close_family(out.get('preHilComparison'))
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_scoped_near_tee_confirmation')
    out['sourceNearTeeConfirmations']=dict(source_sha256=hashes['source_sha256'],input_graph_sha256=hashes['graph_sha256'],reply_sha256=policy['reply_sha256'],records=records,prior_states=history,whole_graph_accepted=False)
    return out,records


def reproduce(source,graph,normalization,policy_file):
    doc,proof=read_source(source);policy=load(policy_file)
    for key in ('reply','pair'):
        if sha(policy[key])!=policy[key+'_sha256']:raise ValueError('stale '+key)
    hashes=dict(source_sha256=proof['source_sha256'],graph_sha256=sha(graph),normalization_sha256=sha(normalization))
    return confirm(doc,load(graph),load(normalization),policy,load(policy['reply']),hashes)


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'near-tee-confirmation-audit.json')
    if audit['script_sha256']!=sha(__file__) or audit['screen_sha256']!=sha(Path(__file__).with_name('screen_applied_near_tees.py')):raise ValueError('stale near-tee confirmation implementation')
    for key in ('source','graph','normalization','policy','devices'):
        if sha(audit[key])!=audit[key+'_sha256']:raise ValueError('stale near-tee '+key)
    out,records=reproduce(audit['source'],audit['graph'],audit['normalization'],audit['policy'])
    expected=json.dumps(out,ensure_ascii=False,indent=2)+'\n'
    if (expected!=(directory/'graph_with_confirmed_near_tees.json').read_text(encoding='utf8')
        or sha(directory/'graph_with_confirmed_near_tees.json')!=audit['output_graph_sha256'] or records!=audit['records']
        or sha(directory/'assigned_edge_device_instances.csv')!=audit['devices_sha256']):raise ValueError('near-tee confirmation replay differs')
    return {r['node_id'] for r in records}


def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','normalization','devices','policy','output'):p.add_argument('--'+key,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    out,records=reproduce(a.source,a.graph,a.normalization,a.policy)
    a.output.mkdir(parents=True);target=a.output/'graph_with_confirmed_near_tees.json'
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
    audit={key:str(getattr(a,key).resolve()) for key in ('source','graph','normalization','devices','policy')}
    audit.update({key+'_sha256':sha(getattr(a,key)) for key in ('source','graph','normalization','devices','policy')})
    audit.update(records=records,output_graph_sha256=sha(target),script_sha256=sha(__file__),screen_sha256=sha(Path(__file__).with_name('screen_applied_near_tees.py')),whole_graph_accepted=False)
    (a.output/'near-tee-confirmation-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(confirmed_nodes=sorted(r['node_id'] for r in records),graph_sha256=sha(target))))


if __name__=='__main__':main()
