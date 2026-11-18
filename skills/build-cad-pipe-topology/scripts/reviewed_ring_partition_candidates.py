"""Apply one reviewed upper/lower rule across independently labelled riser arms.

The expert permits values, local native evidence chooses among them. Original
annotation, T, direct/F boundaries and inference implementations are reused.
"""
import argparse,copy,importlib,math,re
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require,current_plan_reader
from source_readability import read_source
from current_junction_plan_DN import collect,preserve_known
from rebuild_inherited_full_plan_DN import configuration,implementation_hashes as original_hashes
from projected_circle_plan_DN import infer
from batch_native_path_coverage import collect as coverage

MODE='native_reviewed_alternative_ring_partition_DN_v1'


def declared_candidates(message):
    require(isinstance(message,str) and '\ufffd' not in message,'readable explicit partition reply required')
    a,b=message.find('上'),message.find('下')
    require(0<=a<b,'explicit upper and lower clauses required')
    pattern=r'(?:DN\s*((?:[1-9][0-9]*\s*[/／或]\s*)*[1-9][0-9]*)|((?:[1-9][0-9]*\s*[/／或]\s*)*[1-9][0-9]*)\s*DN)'
    result={}
    for side,clause in [('upper',message[a:b]),('lower',message[b:])]:
        hits=re.findall(pattern,clause,re.I)
        require(bool(hits),'explicit DN candidates required for both sides')
        result[side]=sorted({int(v) for hit in hits for v in re.findall(r'[1-9][0-9]*',hit[0] or hit[1])})
    return result


def add_candidate_partition_seeds(graph,baseline,policy,candidates,allowed):
    edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']}
    rows={r['edge_id']:r for r in baseline['records']};seeds=copy.deepcopy(baseline['direct_seed_evidence'])
    direct={s['edge_id'] for s in seeds};selected={};known=[];seen=set()
    direction=policy['upper_direction_WCS']
    require(len(direction)==2 and all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in direction)
        and math.hypot(*direction)>0,'finite independent upper direction required')
    direction=[v/math.hypot(*direction) for v in direction]
    boundaries=policy['boundaries']
    require(boundaries and {b['system'] for b in boundaries}=={'supply','return'},'both independent systems required')
    for boundary in boundaries:
        nid=boundary['boundary_T'];system=boundary['system'];node=nodes[nid]
        require(nid not in seen,'duplicate reviewed boundary');seen.add(nid)
        require(node['system']==system and node.get('node_type') in ('tee','physical_junction')
            and node.get('review_required') is not True and nid in baseline['native_current_T_evidence'],
            'original same-system native riser T required')
        role=baseline['roles'].get(nid,{})
        require(set(role.get('through',[]))=={boundary['upper_entry'],boundary['lower_entry']},
            'partition entries are not the two actual through arms')
        for side,sign in [('upper',1),('lower',-1)]:
            entry=boundary[side+'_entry'];ids=boundary[side+'_edges']
            require(len(set(ids))==len(ids) and (entry in ids or rows[entry]['nominal_mm'] is not None),
                'selected arm or unchanged known entry required')
            scope=list(dict.fromkeys([entry,*ids]));reached={nid};remaining=set(scope)
            while remaining:
                connected=[eid for eid in remaining if {edges[eid]['start_node_id'],edges[eid]['end_node_id']} & reached]
                require(bool(connected),'reviewed arm disconnected from its riser boundary')
                for eid in connected:
                    reached.update([edges[eid]['start_node_id'],edges[eid]['end_node_id']]);remaining.remove(eid)
            for eid in scope:
                edge,row=edges[eid],rows[eid]
                require(edge['system']==system,'reviewed partition crosses systems')
                offsets=[sign*sum((p[i]-node[k])*direction[i] for i,k in enumerate(('x','y')))
                    for path in edge['attribute_paths'] for p in path]
                require(offsets and min(offsets)>=-.05 and max(offsets)>.05,'arm crosses or opposes the declared partition')
                require({edge['start_node_id'],edge['end_node_id']} <= baseline['native_current_T_evidence'].keys(),
                    'both main endpoints need original native T evidence')
                if row['nominal_mm'] is not None:
                    require(row['nominal_mm'] in candidates[side],'known arm contradicts reviewed candidates')
                    known.append(dict(edge_id=eid,nominal_mm=row['nominal_mm'],side=side,boundary_T=nid,
                                      direct=eid in direct,status='known_native_DN_preserved'))
                    continue
                require(eid in ids and eid in allowed and eid not in selected and eid not in direct
                    and row['status']=='conflict','only reviewed unknown conflict arms may receive seeds')
                values=set(candidates[side]) & {r['nominal_mm'] for r in row['lineage']}
                require(len(values)==1,'local source does not uniquely choose an allowed DN')
                value=next(iter(values));selected[eid]=dict(side=side,boundary_T=nid,nominal_mm=value,system=system,
                    allowed_values=copy.deepcopy(candidates[side]),choice='unique_original_native_lineage_candidate')
                seeds.append(dict(edge_id=eid,nominal_mm=value,evidence_id='reviewed-main-partition:'+policy['scope_id']+':'+eid,
                    source_kind='explicit_expert_main_partition_boundary_not_native_TEXT'))
    return seeds,selected,known


def compute(manifest):
    inputs=manifest['inputs']
    def checked():
        require(all(sha(v['path'])==v['sha256'] for v in inputs.values()),'reviewed alternative partition input changed')
    checked();reply=load(inputs['expert_receipt']['path'])
    require(reply['mode']=='explicit_chat_unified_ring_partition_answer_receipt_v1'
        and reply['DN_values_assigned']==reply['length_values_assigned']==0 and reply['human_accepted'] is False,
        'original explicit unified reply required')
    records=reply['records'];require({r['question_id'] for r in records}==set(manifest['question_ids']),
        'complete reviewed question cohort differs')
    message=reply['original_message_verbatim'];candidates=declared_candidates(message);allowed=set()
    for row in records:
        answer=row['explicit_answer']
        require(row['source_message_verbatim']==message and answer['comment']==message
            and answer['decision']=='按不同区段／变径边界，见说明'
            and answer['source_pair_sha256']==row['pair_sha256'],'unified source reply differs')
        require(sha(Path(manifest['page_root'])/manifest['pair_paths'][row['question_id']])==row['pair_sha256'],
            'original reviewed Pair changed')
        for spec in row['source_binding']['source_inputs']:
            require(sha(spec['path'])==spec['sha256'],'original reviewed source input changed')
        require(inputs['source'] in row['source_binding']['source_inputs']
            and inputs['graph'] in row['source_binding']['source_inputs'],'reply belongs to another source or graph')
        allowed.update(row['source_evidence']['source_plan_edges'])
    original=load(inputs['original_DN']['path']);receipt=load(inputs['original_DN_receipt']['path'])
    require(receipt['output_sha256']==inputs['original_DN']['sha256']
        and receipt['manifest']['sha256']==inputs['original_DN_manifest']['sha256']
        and receipt['implementation_sha256']==original_hashes(),'original whole-plan DN owner changed')
    old_manifest=load(inputs['original_DN_manifest']['path']);item=next(p for p in old_manifest['plans'] if p['floor']==manifest['floor'])
    require(item['inputs']['source']==inputs['source'] and item['inputs']['graph']==inputs['graph'],
        'original plan DN namespace differs')
    graph=load(inputs['graph']['path']);config=load(inputs['current_T_configuration']['path'])
    doc,preflight=read_source(inputs['source']['path']);sh,gh=inputs['source']['sha256'],inputs['graph']['sha256']
    baseline=collect(doc,graph,original['floors'][str(manifest['floor'])],sh,gh,current_plan_reader(config,sh,gh),configuration(item))
    seeds,selected,known=add_candidate_partition_seeds(graph,baseline,manifest['partition_policy'],candidates,allowed)
    eligible={eid for eid,p in baseline['source_path_evidence'].items() if p['edges'] and all(s['status']=='single_source_line_covers'
        for e in p['edges'] for s in e['segments'])}-set(baseline['annotation_barriers'])
    after=infer(graph,seeds,eligible,baseline['native_current_T_evidence'],sh,gh);preserve_known(baseline,after['records'])
    before={r['edge_id']:r for r in baseline['records']};changes=[r for r in after['records'] if r['nominal_mm']!=before[r['edge_id']]['nominal_mm']]
    require(changes and {r['edge_id'] for r in changes}<=allowed,'partition changes an unreviewed source extent')
    require(all(any(r['edge_id']==eid and r['nominal_mm']==p['nominal_mm'] for r in changes) for eid,p in selected.items()),
        'original inference kernel did not apply all reviewed seeds')
    edges={e['edge_id']:e for e in graph['edges']};output=[]
    for row in changes:
        eid=row['edge_id'];cov=coverage(doc,graph,[eid],sh,gh)
        require(not cov['unresolved'] and all(s['status']=='single_source_line_covers' for e in cov['edges'] for s in e['segments']),
            'affected source path lacks unique native coverage')
        tees={n:baseline['native_current_T_evidence'][n] for n in (edges[eid]['start_node_id'],edges[eid]['end_node_id'])
            if n in baseline['native_current_T_evidence']}
        output.append(dict(copy.deepcopy(row),kernel_status=row['status'],
            status='expert_reviewed_main_partition_DN' if eid in selected else 'native_T_branch_DN_inherited_after_reviewed_main_partition',
            original_conflict=copy.deepcopy(before[eid]),reviewed_main_scope=selected.get(eid),current_native_T=tees,
            current_native_path=cov,physical_reducer_position=None,physical_length_mm=None,source_graph_mutated=False,human_accepted=False))
    checked()
    return dict(mode=MODE,inputs=inputs,floor=manifest['floor'],records=output,declared_candidates=candidates,
        selected_main_scopes=selected,unchanged_known_arms=known,source_preflight=preflight,
        original_native_annotation_and_T_and_inference_owners_reexecuted=True,all_old_known_plan_DN_preserved=True,
        room_count_used_for_DN=False,source_graph_mutated=False,length_values_assigned=0,human_accepted=False,whole_goal_complete=False)


def implementations():
    names=('current_junction_plan_DN','rebuild_inherited_full_plan_DN','projected_circle_plan_DN','batch_native_path_coverage',
           'legacy_named_provider_inventory','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__) for n in names})


def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh partition output required');code=implementations();result=compute(load(manifest))
    require(code==implementations(),'partition implementation changed');output.mkdir(parents=True)
    p=output/'reviewed-ring-partition-DN.json';p.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=code,output_sha256=sha(p))))
    return result


def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');p=output/'reviewed-ring-partition-DN.json'
    require(r['mode']==MODE and r['implementation_sha256']==implementations() and sha(r['manifest']['path'])==r['manifest']['sha256']
        and sha(p)==r['output_sha256'],'partition receipt changed');fresh=compute(load(r['manifest']['path']))
    require(encode(fresh)==p.read_bytes(),'partition source replay differs');return fresh


def main():
    p=argparse.ArgumentParser()
    for k in ('manifest','output','verify-output'):p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    if not a.verify_output and not(a.manifest and a.output):p.error('manifest and fresh output required')
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result=verify_output(a.verify_output) if a.verify_output else produce(a.manifest,a.output)
    print(encode(dict(mode=MODE,source_DN_records=len(result['records']),known_arms_preserved=len(result['unchanged_known_arms']),
                      candidates=result['declared_candidates'],length_values_assigned=0)).decode(),flush=True)


if __name__=='__main__':main()
