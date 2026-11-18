"""Rebase a reviewed plan/drop distinction onto unchanged native plan paths.

The answer bounds the already drawn plan branch. It does not make its value a
new annotation seed, select a reducer position or overwrite the axis drop.
"""
import copy,re
from confirm_crossview_paths import load,sha
from inherited_circle_branch_inventory import inspect


def bind_archive(paths,question_id):
    raw,definitions,receipt=(load(paths[k])for k in ('reply','definitions','receipt'))
    if receipt['input']['sha256']!=sha(paths['reply']):raise ValueError('reviewed response archive differs')
    def find(document):
        rows=[(q,s['image'])for group in ('sections','followup_sections')for s in document[group]for q in s['questions']if q['id']==question_id]
        if len(rows)!=1:raise ValueError('reviewed question missing or duplicated')
        return rows[0]
    question,image=find(raw);definition,prior_image=find(definitions)
    archived=[r for r in receipt['records']if r['question_id']==question_id]
    if (image!=prior_image or any(question.get(k)!=definition.get(k)for k in ('text','options','source_evidence'))
        or len(archived)!=1 or archived[0]['explicit_answer']!=question.get('answer')
        or archived[0]['question']!=question['text']or archived[0]['options']!=question['options']
        or archived[0]['source_evidence']!=question['source_evidence']or archived[0]['pair_sha256']!=image['sha256']
        or question['answer'].get('decision')not in question['options']
        or question['answer'].get('source_pair_sha256')!=sha(paths['pair'])or image['sha256']!=sha(paths['pair'])):
        raise ValueError('reviewed question, answer or original Pair differs')
    evidence=question['source_evidence']
    if (evidence['source_sha256']['plan']!=sha(paths['source'])or evidence['graph_sha256']['plan']!=sha(paths['reviewed_graph'])
        or evidence['plan_attribute_sha256']!=sha(paths['attributes'])or evidence['pair_sha256']!=sha(paths['pair'])
        or evidence['overview_sha256']!=sha(paths['overview'])):raise ValueError('reviewed native plan or original scope differs')
    match=re.fullmatch(r'平面已绘支路DN([1-9][0-9]*)，设备前另变DN([1-9][0-9]*)，区段见说明',question['answer']['decision'])
    if not match:raise ValueError('explicit plan versus equipment-drop DN distinction required')
    return question,float(match[1]),float(match[2])


def migrate_scopes(original,current,attributes,equipment_scope,value,drop_value,question_id):
    """Check exact historical native paths, independent of current edge IDs."""
    ids=set(equipment_scope)
    if not ids or len(ids)!=len(equipment_scope):raise ValueError('unique reviewed equipment scope required')
    if set(attributes['equipment_scope'])!=ids:raise ValueError('reviewed attribute equipment scope differs')
    old={e['edge_id']:e for e in original['edges']};now={e['edge_id']:e for e in current['edges']};records=[]
    for did in sorted(ids):
        for system in ('supply','return'):
            before=[e for e in old.values()if did in (e['start_node_id'],e['end_node_id'])and e['system']==system]
            after=[e for e in now.values()if did in (e['start_node_id'],e['end_node_id'])and e['system']==system]
            if len(before)!=1 or len(after)!=1:raise ValueError('reviewed equipment branch is no longer unique')
            a,b=before[0],after[0]
            if any(a.get(k)!=b.get(k)for k in ('system','start_node_id','end_node_id','attribute_paths','source_handles')):
                raise ValueError('reviewed drawn branch scope or owner changed')
            rows=[r for r in attributes['records']if r['kind']=='equipment_branch'and r['plan_edges']==[a['edge_id']]and r['system']==system]
            if (len(rows)!=1 or rows[0]['diameter']['nominal_mm']!=value
                or rows[0]['diameter']['scope_paths']!=a['attribute_paths']):raise ValueError('reviewed original DN extent differs')
            records.append(dict(edge_id=b['edge_id'],nominal_mm=value,evidence_id='reviewed:'+question_id+':'+b['edge_id'],scope_only=True,
                equipment_id=did,system=system,scope_paths=copy.deepcopy(b['attribute_paths']),historical_edge_id=a['edge_id'],
                separate_axis_equipment_drop_DN_mm=drop_value,reducer_position=None,physical_connector_length_mm=None,
                whole_axis_value_selected=False,source_kind='explicit_reviewed_drawn_plan_scope_not_new_annotation'))
    return records


def prepare(graph,paths,question_id,source_hash):
    question,value,drop=bind_archive(paths,question_id)
    original=load(paths['reviewed_graph']);attributes=load(paths['attributes']);evidence=question['source_evidence']
    if (source_hash!=sha(paths['source'])or graph['metadata']['source_sha256']!=source_hash
        or attributes['source_sha256']!=source_hash
        or attributes['graph_sha256']!=sha(paths['reviewed_graph'])):raise ValueError('current and reviewed source identities differ')
    records=migrate_scopes(original,graph,attributes,evidence['equipment_ids'],value,drop,question_id)
    return question,records


def collect(doc,graph,paths,question_id,source_hash,graph_hash,circle_policy):
    question,records=prepare(graph,paths,question_id,source_hash)
    proofs=[]
    for row in records:
        proof=inspect(doc,graph,row['equipment_id'],row['system'],source_hash,graph_hash,circle_policy)
        if proof['trace']['edges']!=[row['edge_id']]:raise ValueError('reviewed current native branch identity differs')
        proofs.append(proof)
    return dict(question_id=question_id,answer=question['answer'],records=records,current_native_evidence=proofs,
        source_sha256=source_hash,graph_sha256=graph_hash,graph_mutated=False,whole_axis_values_assigned=0,human_accepted=False)
