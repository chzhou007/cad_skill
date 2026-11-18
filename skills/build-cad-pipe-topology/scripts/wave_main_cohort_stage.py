"""Family-owned wave/main cohort tail; only review/calibration inputs external."""
from pathlib import Path
import subprocess
import sys
from confirm_crossview_paths import load,sha,encode

SETTINGS={'reviewed_graph','reply','receipt','definitions','pair','calibration'}
CALIBRATION={'question_id','confirmed_decision','floor','control_equipment','control_main_handles','wave_block','wave_fingerprint'}
DESTINATION='topology-wave-main-cohorts'
STAGE='reports/wave-main-cohort-stage.json'


def load_policy_map(path,eligible=None):
    if path is None:return {}
    path=Path(path).resolve();data=load(path)
    if not isinstance(data,dict) or (eligible is not None and set(data)-set(eligible)):
        raise ValueError('wave cohort map contains unrecognized tasks')
    out={}
    for task,settings in data.items():
        if not isinstance(task,str) or not task or not isinstance(settings,dict) or set(settings)!=SETTINGS:
            raise ValueError('wave cohort map accepts only pinned review/calibration inputs')
        if any(not isinstance(p,str) or not p.strip() for p in settings.values()):raise ValueError('invalid wave cohort path')
        out[task]={k:(Path(p) if Path(p).is_absolute() else path.parent/p).resolve() for k,p in settings.items()}
        if any(not p.is_file() for p in out[task].values()):raise ValueError('missing wave cohort evidence')
    return out


def run_stage(source,graph,settings,task_root):
    source,graph,task_root=(Path(p).resolve() for p in (source,graph,task_root))
    if not graph.is_relative_to(task_root):raise ValueError('wave cohort parent must be owned by current family task')
    if set(settings)!=SETTINGS:raise ValueError('wave cohort entry cannot override local inputs or output')
    calibration=load(settings['calibration'])
    if set(calibration)!=CALIBRATION:raise ValueError('calibration cannot override family-owned source paths')
    paths=dict(source=source,graph=graph,devices=graph.parent/'assigned_edge_device_instances.csv',
        **{k:Path(v).resolve() for k,v in settings.items() if k!='calibration'})
    before={k:sha(p) for k,p in paths.items()};calibration_hash=sha(settings['calibration'])
    destination=task_root/DESTINATION;stage=task_root/STAGE
    if destination.exists() or stage.exists():raise FileExistsError('wave cohort family stage already exists')
    policy=dict(calibration,inputs={k:dict(path=str(p),sha256=before[k]) for k,p in paths.items()})
    pp=task_root/'reports/wave-main-cohort-policy.json';pp.parent.mkdir(parents=True,exist_ok=True);pp.write_bytes(encode(policy))
    from reconstruct_wave_main_cohorts import verify_output,MODE
    command=[sys.executable,'-X','utf8',str(Path(__file__).with_name('reconstruct_wave_main_cohorts.py'))]
    for key,value in paths.items():command+=['--'+key.replace('_','-'),str(value)]
    subprocess.run(command+['--policy',str(pp),'--output',str(destination)],check=True)
    audit=verify_output(destination);target=destination/'graph_with_edges.json'
    if any(sha(p)!=before[k] for k,p in paths.items()) or sha(settings['calibration'])!=calibration_hash:
        raise ValueError('wave cohort family inputs changed')
    if audit['mode']!=MODE or audit['output_graph_sha256']!=sha(target):raise ValueError('wave cohort child evidence differs')
    current=load(target)
    if current['derivedEvidenceInvalidation'].get('historical_annotations_preserved') is not True:
        raise ValueError('wave cohort failed to invalidate dependent review while preserving history')
    record=dict(status='native_paired_wave_main_cohort_replayed_mapping_and_HIL_pending',
        graph_sha256=sha(target),parent_graph_sha256=before['graph'],source_sha256=before['source'],
        audit_sha256=sha(destination/'wave-main-cohort-audit.json'),artifact_directory=str(destination),
        entry_sha256=sha(__file__),calibration_sha256=calibration_hash,
        equipment=audit['proof']['equipment'],connections=audit['proof']['connections'],
        physical_lengths_assigned=0,human_accepted=False,hil_ready=False)
    stage.write_bytes(encode(record));return target,audit


def rebase_unchanged_annotation_policy(source,parent_graph,graph,policy,task_root):
    """Replay both source selections before rebinding an unchanged sidecar scope."""
    from native_capped_branch_annotations import collect
    from source_readability import read_source
    source,parent_graph,graph,policy,task_root=(Path(p).resolve() for p in (source,parent_graph,graph,policy,task_root))
    original=load(policy)
    if original['source_sha256']!=sha(source) or original['graph_sha256']!=sha(parent_graph):
        raise ValueError('capped annotation control is not the pre-wave current graph')
    doc,_=read_source(source)
    before=collect(doc,load(parent_graph),sha(source),original['selections'])
    after=collect(doc,load(graph),sha(source),original['selections'])
    if before!=after:raise ValueError('wave cohort changed a capped-annotation scope; explicit reconstruction required')
    result=dict(original,graph_sha256=sha(graph));target=task_root/'reports/wave-rebased-capped-annotation-policy.json'
    target.write_bytes(encode(result))
    (target.with_name('wave-rebased-capped-annotation-proof.json')).write_bytes(encode(dict(
        source_sha256=sha(source),parent_graph_sha256=sha(parent_graph),current_graph_sha256=sha(graph),
        original_policy_sha256=sha(policy),current_policy_sha256=sha(target),
        unchanged_native_selection_evidence=after,human_accepted=False)))
    return target
