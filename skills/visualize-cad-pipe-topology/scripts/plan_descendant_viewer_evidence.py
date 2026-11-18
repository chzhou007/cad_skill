"""Native ancestry adapter for wave/project plan descendants.

The caller keeps the current graph for display and uses only the returned
ancestor for old ownership validation. No main builder dispatch is changed here.
"""
import sys
from pathlib import Path
S=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(S) not in sys.path:sys.path.insert(0,str(S))
from confirm_crossview_paths import load,sha
from project_scoped_graph_descendants import verify_output as verify_project,asset,kind
from inherited_wave_pair_continuity import verify_output as verify_wave


def applicable(graph):
    return any(key in graph for key in ('sourceDeclaredCappedBranchInterfaces','sourceSH16RelatedCornerKnownIssue','sourceInheritedWavePairContinuity'))


def verify(graph_path,graph,snapshot_scope=None):
    graph_path=Path(graph_path).resolve()
    if load(graph_path)!=graph:raise ValueError('plan viewer current graph differs from actual input')
    if not applicable(graph):return graph_path,None,{}
    scope=None
    if 'sourceDeclaredCappedBranchInterfaces' in graph:
        if not isinstance(snapshot_scope,dict) or set(snapshot_scope)!={'path','sha256'}:raise ValueError('explicit project mapping snapshot scope required')
        scope=Path(snapshot_scope['path']).resolve()
        if sha(scope)!=snapshot_scope['sha256']:raise ValueError('project mapping snapshot changed before viewer verification')
    current=graph_path;model=graph;seen=set();chain=[];paths={};initial_hash=sha(graph_path)
    while applicable(model):
        if current in seen or len(chain)>=8:raise ValueError('cyclic or unsupported plan descendant ancestry')
        seen.add(current);index=len(chain);project='sourceDeclaredCappedBranchInterfaces' in model or 'sourceSH16RelatedCornerKnownIssue' in model
        if project:
            native=verify_project(current.parent,scope,snapshot_scope['sha256'] if scope is not None else None)
            audit=native['audit'];parent=Path(native['parent_graph']).resolve();name=native['kind']
            if native['current_graph_sha256']!=sha(current) or native['source_replay']!='passed':raise ValueError('project plan viewer native output differs')
            audit_name='source-capped-interface-roles-audit.json' if name=='capped_roles' else 'SH16-related-corner-known-issue-audit.json'
            for key in ('related_corner','capped_roles'):
                owner,digest=asset(key);paths['plan_project_owner_'+key]=owner
            paths['plan_project_owner_manifest']=owner.parent/'manifest.json'
            paths['plan_project_native_verifier']=S/'project_scoped_graph_descendants.py'
            paths['plan_source_interface_role_kernel']=S/'source_capped_branch_roles.py'
            paths['plan_source_caption_reader']=S/'native_capped_branch_annotations.py'
        else:
            audit=verify_wave(current.parent);name='inherited_wave';audit_name='inherited-wave-receipt.json';parent=Path(audit['inputs']['graph']['path']).resolve()
            if audit['output_graph_sha256']!=sha(current):raise ValueError('wave plan viewer native output differs')
            paths['plan_inherited_wave_owner']=S/'inherited_wave_pair_continuity.py'
        if sha(parent)!=audit['inputs']['graph']['sha256'] or parent==current:raise ValueError('plan descendant native parent changed or cycles')
        prefix='plan_descendant_'+str(index)+'_';paths[prefix+'graph']=current;paths[prefix+'audit']=current.parent/audit_name;paths[prefix+'parent_graph']=parent
        for key,row in audit['inputs'].items():paths[prefix+'input_'+key]=Path(row['path']).resolve()
        if name=='capped_roles':
            annotation_audit=load(audit['inputs']['native_annotation_audit']['path'])
            for key,row in annotation_audit['inputs'].items():paths[prefix+'annotation_input_'+key]=Path(row['path']).resolve()
        chain.append(dict(kind=name,current_graph_sha256=sha(current),parent_graph_sha256=sha(parent),native_audit_sha256=sha(current.parent/audit_name),
            source_replay='passed',human_accepted=False))
        current=parent;model=load(parent)
    if sha(graph_path)!=initial_hash or load(graph_path)!=graph:raise ValueError('display graph changed during plan ancestry verification')
    if scope is not None:
        if sha(scope)!=snapshot_scope['sha256']:raise ValueError('project mapping snapshot changed during viewer ancestry replay')
        paths['plan_project_mapping_snapshot_scope']=scope
    paths['plan_descendant_viewer_validator']=Path(__file__).resolve()
    for path in paths.values():
        if not path.is_file():raise ValueError('missing native plan viewer dependency '+str(path))
    proof=dict(mode='native_plan_descendant_viewer_ancestry_v1',current_graph_sha256=initial_hash,ancestor_graph_sha256=sha(current),chain=chain,
        display_current_graph_retained=True,old_receipts_rebound=False,new_human_confirmation=False,hil_ready=False,human_accepted=False)
    return current,proof,paths
