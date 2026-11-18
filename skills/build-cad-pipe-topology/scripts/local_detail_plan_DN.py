"""Add local source T reading while retaining all inherited DN/annotation rules."""
from full_plan_DN_source import collect as source_collect
from current_circle_plan_DN import collect as current_collect,current_tee as current_tee
from user_circle_endpoint_plan_DN import collect as user_collect,current_tee as user_tee
from confirmed_overlap_plan_DN import collect as overlap_collect,current_tee as overlap_tee
from crossview_equipment_branch_inventory import native_tee
from main_continuity_plan_DN import bind
from source_main_DN_continuity import infer
from native_local_detail_T_evidence import collect as detail_collect

def collect(doc,graph,source_hash,graph_hash,reviewed_seeds=(),announce=lambda x:None,
            circle_policy=None,annotation_config=None,lineage_parents=(),endpoint_review=None,overlap_owners=()):
    evidence={}
    def detail_tee(d,g,nid,sh,gh):
        try:return native_tee(d,g,nid,sh,gh)
        except ValueError as exc:
            if str(exc)!='missing or ambiguous graph T ray':raise
            incident=[e for e in g['edges']if nid in (e.get('start_node_id'),e.get('end_node_id'))]
            if not any(e.get('source_detail_circle_length_evidence')for e in incident):raise
            proof=detail_collect(d,g,nid,sh,gh);evidence[nid]=proof;return proof
    source=bind(source_collect,infer=infer)
    current_reader=bind(current_tee,original_tee=detail_tee)
    current=bind(current_collect,source_collect=source,current_tee=current_reader)
    user_reader=bind(user_tee,previous_tee=current_reader)
    user=bind(user_collect,previous_collect=current,current_tee=user_reader)
    overlap_reader=bind(overlap_tee,previous_tee=user_reader)
    overlap=bind(overlap_collect,previous_collect=user,current_tee=overlap_reader)
    result=overlap(doc,graph,source_hash,graph_hash,reviewed_seeds,announce,circle_policy,annotation_config,lineage_parents,endpoint_review,overlap_owners)
    result['native_local_detail_T_evidence']=evidence;result['native_local_detail_T_nodes']=sorted(evidence)
    return result
