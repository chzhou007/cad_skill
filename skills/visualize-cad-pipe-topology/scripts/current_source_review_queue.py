"""Compose source-qualified external review items into the canonical queue.

Old questions, answers and comments are immutable here. This entry publishes
unresolved questions only: it assigns no graph, DN, length or review acceptance.
"""
import argparse,copy,hashlib,json,re
from pathlib import Path
from review_page_preflight import validate_dataset

MODE='unified_current_source_review_queue_v1'
HASH=re.compile(r'^[0-9a-f]{64}$')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def checked(spec):
    if not isinstance(spec,dict)or not isinstance(spec.get('path'),str)or not HASH.fullmatch(spec.get('sha256','')):raise ValueError('pinned source file required')
    path=Path(spec['path'])
    if not path.is_file()or sha(path)!=spec['sha256']:raise ValueError('review source or qualification artifact changed: '+str(path))
    return path
def questions(data):
    return [(section,question)for field in('sections','followup_sections')for section in data.get(field,[])for question in section['questions']]
def received(data):
    result={}
    for field in('received_feedback','received_followup_feedback','received_compound_lane_feedback'):result.update(data.get(field,{}).get('answers',{}))
    return result
def queue_summary(data):
    answers=received(data);followups={q['id']for s in data.get('followup_sections',[])for q in s['questions']};archived=[];pending=[]
    for s,q in questions(data):
        a=answers.get(q['id'],{})
        valid=bool(a.get('decision'))and(q['id']not in followups or a.get('source_pair_sha256')==s['image']['sha256'])
        (archived if valid else pending).append(q['id'])
    return dict(total_questions=len(archived)+len(pending),archived_received_questions=archived,pending_question_ids=pending)

def compose(existing,proposals,page_root):
    before=copy.deepcopy(existing);data=copy.deepcopy(existing);validate_dataset(data,page_root)
    if not isinstance(proposals,list):raise ValueError('review proposal list required')
    index={q['id']:(s,q)for s,q in questions(data)};new=[];deduplicated=[];sources=copy.deepcopy(data.get('current_review_queue_sources',{}));aliases={a:qid for qid,r in sources.items()for a in r.get('aliases',[])}
    for proposal in proposals:
        if not isinstance(proposal,dict):raise ValueError('review proposal object required')
        section=proposal.get('section');qs=section.get('questions',[])if isinstance(section,dict)else[]
        if len(qs)!=1:raise ValueError('one canonical question per external scope required')
        q=qs[0];qid=q['id'];qualification=load(checked(proposal.get('qualification')))
        inputs=proposal.get('source_inputs')
        if not isinstance(inputs,list)or not inputs or len({s.get('path')for s in inputs})!=len(inputs):raise ValueError('unique current source inputs required')
        for spec in inputs:checked(spec)
        if (qualification.get('mode')!=MODE or qualification.get('question_id')!=qid or qualification.get('source_inputs')!=inputs
            or qualification.get('review_ready')is not True or qualification.get('graph_mutated')is not False
            or qualification.get('physical_values_assigned')!=0 or qualification.get('human_accepted')is not False):raise ValueError('current unresolved source scope not ready for the review queue')
        if not isinstance(proposal.get('origin'),str)or not proposal['origin'].strip()or not HASH.fullmatch(proposal.get('original_question_sha256','')):raise ValueError('original external question identity required')
        if q.get('source_evidence',{}).get('external_question_sha256')!=proposal['original_question_sha256']:raise ValueError('canonical question lost its external identity')
        origin_aliases=proposal.get('aliases',[])
        if not isinstance(origin_aliases,list)or len(origin_aliases)!=len(set(origin_aliases))or any(not isinstance(a,str)or not a for a in origin_aliases):raise ValueError('unique external aliases required')
        for alias in origin_aliases:
            if alias in aliases and aliases[alias]!=qid or alias in index and alias!=qid:raise ValueError('external alias maps to competing review questions')
            aliases[alias]=qid
        if qid in index:
            old_section,old_question=index[qid]
            if old_question!=q or old_section['image']!=section['image']:raise ValueError('existing question or Pair changed; preserve history and create an explicit new review version')
            deduplicated.append(qid)
        else:
            data.setdefault('followup_sections',[]).append(copy.deepcopy(section));index[qid]=(section,q);new.append(qid)
        binding=dict(origin=proposal['origin'],original_question_sha256=proposal['original_question_sha256'],qualification=copy.deepcopy(proposal['qualification']),source_inputs=copy.deepcopy(inputs),aliases=copy.deepcopy(origin_aliases))
        if qid in sources and sources[qid]!=binding:raise ValueError('review queue source binding changed; version the source scope explicitly')
        sources[qid]=binding
    data['current_review_queue_sources']=sources
    preflight=validate_dataset(data,page_root)
    for field in('sections','received_feedback','received_followup_feedback','received_compound_lane_feedback','review_workflow'):
        if data.get(field)!=before.get(field):raise ValueError('historical review data changed')
    if data.get('followup_sections',[])[:len(before.get('followup_sections',[]))]!=before.get('followup_sections',[]):raise ValueError('old followup questions changed')
    if existing!=before:raise ValueError('composition mutated caller review data')
    return data,dict(mode=MODE,status='current_source_review_queue_composed_not_human_acceptance',new_canonical_question_ids=new,deduplicated_question_ids=deduplicated,queue=queue_summary(data),preflight=preflight,old_questions_answers_and_comments_exact=True,graph_mutated=False,physical_values_assigned=0,human_accepted=False)

def produce(existing,proposals,page_root,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    pins={k:dict(path=str(Path(p).resolve()),sha256=sha(p))for k,p in [('existing',existing),('proposals',proposals)]}
    data,report=compose(load(existing),load(proposals),page_root)
    if any(sha(spec['path'])!=spec['sha256']for spec in pins.values()):raise ValueError('review input changed during composition')
    output.mkdir(parents=True);target=output/'review-queue.json';target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report.update(inputs=pins,page_root=str(Path(page_root).resolve()),implementation_sha256=sha(__file__),output_sha256=sha(target));(output/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return report
def main():
    p=argparse.ArgumentParser()
    for key in('existing','proposals','page-root','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();report=produce(a.existing,a.proposals,a.page_root,a.output);print(json.dumps(report,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
