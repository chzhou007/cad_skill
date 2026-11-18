"""Reuse current source T adapters without running or using DN inheritance.

Private function bindings preserve every original implementation and its exact
fall-through conditions. Native geometry errors remain errors, never broad snaps.
"""
from confirm_crossview_paths import load,sha
from crossview_equipment_branch_inventory import native_tee
from main_continuity_plan_DN import bind
from current_circle_plan_DN import current_tee as circle_tee
from user_circle_endpoint_plan_DN import current_tee as endpoint_tee
from confirmed_overlap_plan_DN import current_tee as overlap_tee
from native_local_detail_T_evidence import collect as detail_collect
from native_projected_circle_main_role import collect as projected_collect,authorities

def make_reader(manifest,source_hash,graph_hash):
    selected=[r for r in manifest['plans']if r['inputs']['graph']['sha256']==graph_hash and r['inputs']['source']['sha256']==source_hash]
    if len(selected)!=1:raise ValueError('current junction reader needs one exact source/graph configuration')
    config=selected[0]
    for spec in [config['inputs']['source'],config['inputs']['graph'],*config.get('circle_main_lineage_parents',[])]:
        if sha(spec['path'])!=spec['sha256']:raise ValueError('current junction lineage input changed')
    allowed=authorities(manifest.get('projected_circle_expert_authorities',[]))
    parents=config.get('circle_main_lineage_parents',[]);review=config.get('circle_endpoint_review');owners=config.get('confirmed_overlap_owners',[])
    circle_input=config['inputs'].get('circle_policy');circle_policy=None
    if circle_input is not None:
        if sha(circle_input['path'])!=circle_input['sha256']:raise ValueError('inherited circle policy changed')
        circle_policy=load(circle_input['path'])
    if review is not None and sha(review['path'])!=review['sha256']:raise ValueError('current junction endpoint review changed')
    def projected(doc,g,nid,sh,gh):
        try:return native_tee(doc,g,nid,sh,gh)
        except ValueError as exc:
            if str(exc)!='missing or ambiguous graph T ray':raise
            node=next(n for n in g['nodes']if n['node_id']==nid)
            if not node.get('expert_circle_evidence'):raise
            return projected_collect(doc,g,nid,sh,gh,allowed)
    def detail(doc,g,nid,sh,gh):
        try:return projected(doc,g,nid,sh,gh)
        except ValueError as exc:
            if str(exc)!='missing or ambiguous graph T ray':raise
            incident=[e for e in g['edges']if nid in(e.get('start_node_id'),e.get('end_node_id'))]
            if not any(e.get('source_detail_circle_length_evidence')for e in incident):raise
            return detail_collect(doc,g,nid,sh,gh)
    current=bind(circle_tee,original_tee=detail)
    endpoint=bind(endpoint_tee,previous_tee=current)
    overlap=bind(overlap_tee,previous_tee=endpoint)
    def reader(doc,graph,nid,sh,gh):
        if sh!=source_hash or gh!=graph_hash:raise ValueError('current T reader used for another native scope')
        waves={r['tee_id']:r for r in graph.get('sourceWaveMainCohort',{}).get('records',[])}
        node=next(n for n in graph['nodes']if n['node_id']==nid)
        if nid in waves:
            from rebuild_wave_cohort_crossview_batch import wave_branch
            row=waves[nid]
            return wave_branch(doc,graph,row['equipment_id'],row['system'],sh,gh)['junction_evidence']
        if node.get('expert_confirmed_circle')or node.get('calibrated_duplicate_circle')or nid in(circle_policy or{}).get('external_cases',{}):
            from native_inherited_duplicate_circle_evidence import collect
            return collect(doc,graph,nid,sh,gh,circle_policy)
        return overlap(doc,graph,nid,sh,gh,parents,review,owners)
    return reader
