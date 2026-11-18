"""Compose unchanged source readers with corrected native main DN roles."""
import types
from full_plan_DN_source import collect as source_collect
from current_circle_plan_DN import collect as current_collect
from user_circle_endpoint_plan_DN import collect as user_collect
from confirmed_overlap_plan_DN import collect as overlap_collect
from source_main_DN_continuity import infer


def bind(function,**dependencies):
    namespace=dict(function.__globals__);namespace.update(dependencies)
    return types.FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,function.__closure__)


def collect(doc,graph,source_hash,graph_hash,reviewed_seeds=(),announce=lambda x:None,
            circle_policy=None,annotation_config=None,lineage_parents=(),endpoint_review=None,overlap_owners=()):
    source=bind(source_collect,infer=infer)
    current=bind(current_collect,source_collect=source)
    user=bind(user_collect,previous_collect=current)
    overlap=bind(overlap_collect,previous_collect=user)
    return overlap(doc,graph,source_hash,graph_hash,reviewed_seeds,announce,circle_policy,annotation_config,lineage_parents,endpoint_review,overlap_owners)
