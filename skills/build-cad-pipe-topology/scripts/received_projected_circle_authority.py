"""Consume source-bound explicit circle replies through the original native owner.

No source ray, local graph, original issue or historical receipt is edited.
The newer reply is a separate authority for its exact archived locator only.
"""
import copy,importlib,math,sys
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from native_projected_circle_main_role import collect as original_collect,AUTHORITY

MODE='received_source_bound_projected_circle_authority_v1'
OLD_HOLD='projected circle connection lies outside an explicit expert source extent; similar-location inference remains pending'


def checked(spec):
    if sha(spec['path'])!=spec['sha256']:raise ValueError('received circle dependency changed')
    return Path(spec['path'])


def intake_module():
    scripts=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(scripts)not in sys.path:sys.path.insert(0,str(scripts))
    import receive_current_review_answers as intake
    return intake


def replay_intake(spec,page_root):
    """Re-execute the original intake on its archived originals and actual Pair."""
    path=checked(spec);receipt=load(path);intake=intake_module()
    if receipt['mode']!=intake.MODE or receipt['implementation_sha256']!=sha(intake.__file__):
        raise ValueError('received circle intake implementation differs')
    definitions=intake.load(checked(receipt['inputs']['definitions']))
    reply=intake.load(checked(receipt['inputs']['reply']))
    ids=[r['question_id']for r in receipt['records']]
    data,fresh=intake.receive(definitions,reply,page_root,ids)
    output=path.parent/'review-queue.json'
    if sha(output)!=receipt['output_sha256'] or data!=load(output):
        raise ValueError('received circle intake replay differs')
    if any(receipt.get(k)!=v for k,v in fresh.items()):
        raise ValueError('received circle receipt fields differ')
    checked(spec)
    return definitions,copy.deepcopy(receipt['records'])


def select_authority(definitions,records,binding,source_spec,graph_spec,graph,intake_spec,page_root):
    from current_source_review_queue import questions
    selected=[(s,q)for s,q in questions(definitions)if q['id']==binding['question_id']]
    replies=[r for r in records if r['question_id']==binding['question_id']]
    if len(selected)!=1 or len(replies)!=1:raise ValueError('one exact received circle question required')
    section,q=selected[0];r=replies[0];evidence=q['source_evidence'];answer=r['explicit_answer']
    if (r['question']!=q['text'] or r['options']!=q['options'] or r['source_evidence']!=evidence
        or answer.get('decision')!=binding['expected_decision'] or binding['expected_decision']not in q['options']
        or evidence['source']!=source_spec or evidence['graph']!=graph_spec
        or evidence['node_id']!=binding['node_id'] or r['pair_sha256']!=section['image']['sha256']
        or answer['source_pair_sha256']!=section['image']['sha256']):
        raise ValueError('received circle decision, source, graph or Pair differs')
    for image in [section['image'],*section.get('contexts',[])]:
        path=(Path(page_root)/image['path']).resolve()
        if not path.is_relative_to(Path(page_root).resolve())or sha(path)!=image['sha256']:
            raise ValueError('received circle source image changed')
    context=section['contexts'][binding['context_index']]
    locator=context['locators'][binding['locator_index']]
    box=locator['bbox']
    if (len(box)!=4 or any(type(v)not in(int,float)or not math.isfinite(v)for v in box)
        or box[1]<=box[0]or box[3]<=box[2]):raise ValueError('original source locator bounds required')
    nodes=[n for n in graph['nodes']if n['node_id']==binding['node_id']]
    if len(nodes)!=1:raise ValueError('reviewed circle identity missing')
    meta=nodes[0].get('expert_circle_evidence',{});entities={e['handle']:e for e in evidence['source_entities']}
    if (not meta or entities.get(meta.get('circle_handle'),{}).get('type')!='CIRCLE'
        or any(entities.get(meta.get(k),{}).get('type')!='LINE'for k in('main_handle','branch_handle'))):
        raise ValueError('question does not name exact original circle and pipe identities')
    return dict(issue=copy.deepcopy(intake_spec),basis=AUTHORITY,source_sha256=source_spec['sha256'],
        issue_label=meta['expert_issue'],source_bounds=[box[0],box[2],box[1]-box[0],box[3]-box[2]],
        explicit_expert_note=answer['decision'],received_question_id=q['id'],
        authority_kind=MODE,original_topology_issue_label_retained=True,
        source_locator=copy.deepcopy(locator),source_pair=copy.deepcopy(section['image']),
        received_answer=copy.deepcopy(answer),original_expert_issue_rewritten=False)


def prepare(manifest,source_spec,graph_spec,graph):
    checked(source_spec);checked(graph_spec)
    if graph!=load(graph_spec['path']):raise ValueError('reviewed circle graph differs from pinned input')
    definitions,records=replay_intake(manifest['intake_receipt'],manifest['page_root'])
    result={}
    for binding in manifest['connections']:
        nid=binding['node_id']
        if nid in result:raise ValueError('duplicate received circle authority')
        result[nid]=select_authority(definitions,records,binding,source_spec,graph_spec,graph,
            manifest['intake_receipt'],manifest['page_root'])
    if not result:raise ValueError('explicit received circle authorities required')
    return result


def collect(doc,graph,nid,source_hash,graph_hash,authorities):
    if nid not in authorities:raise ValueError('circle has no explicit received answer')
    before=encode(graph);proof=original_collect(doc,graph,nid,source_hash,graph_hash,[authorities[nid]])
    if encode(graph)!=before:raise ValueError('received authority changed source graph')
    proof['received_source_authority']=copy.deepcopy(authorities[nid])
    proof['previous_issue_extent_expanded']=False
    return proof


def reader(previous,authorities):
    def read(doc,graph,nid,sh,gh):
        try:return previous(doc,graph,nid,sh,gh)
        except ValueError as exc:
            if str(exc)!=OLD_HOLD or nid not in authorities:raise
        return collect(doc,graph,nid,sh,gh,authorities)
    return read


def implementations():
    intake_module()
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in
        ('native_projected_circle_main_role','receive_current_review_answers','current_source_review_queue','review_page_preflight')})
