"""Formal ceiling-family tail for independently controlled wave omission pairs."""
import hashlib,json,subprocess,sys
from pathlib import Path

SETTINGS={'policy','control_source','control_graph','control_confirmation','control_issue','control_image'}
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text('utf-8-sig'))


def load_policy_map(path,eligible=None):
    if path is None:return {}
    path=Path(path).resolve();values=load(path)
    if not isinstance(values,dict):raise ValueError('invalid inherited wave continuity map')
    if eligible is not None and set(values)-set(eligible):raise ValueError('inherited wave map contains unrecognized task IDs')
    result={}
    for task,settings in values.items():
        if not isinstance(task,str) or not task or not isinstance(settings,dict) or set(settings)!=SETTINGS:
            raise ValueError('inherited wave map requires only pinned controls and policy')
        if any(not isinstance(value,str) or not value.strip() for value in settings.values()):raise ValueError('invalid inherited wave dependency path')
        resolved={key:(Path(value) if Path(value).is_absolute() else path.parent/value).resolve() for key,value in settings.items()}
        if any(not value.is_file() for value in resolved.values()):raise ValueError('missing inherited wave control or policy file')
        result[task]=resolved
    return result


def run_stage(source,graph,settings,task_root):
    source=Path(source).resolve();graph=Path(graph).resolve();task_root=Path(task_root).resolve()
    if not graph.is_relative_to(task_root):raise ValueError('inherited wave parent must be the current task graph')
    if set(settings)!=SETTINGS:raise ValueError('inherited wave entry cannot override source, graph, devices or output')
    paths=dict(source=source,graph=graph,devices=graph.parent/'assigned_edge_device_instances.csv',**{key:Path(value).resolve() for key,value in settings.items()})
    before={key:digest(path) for key,path in paths.items()}
    destination=task_root/'topology-inherited-wave-pair-continuity';stage=task_root/'reports/source-inherited-wave-continuity-stage.json'
    if destination.exists() or stage.exists():raise FileExistsError('inherited wave family output already exists')
    from inherited_wave_pair_continuity import verify_output,MODE
    command=[sys.executable,'-X','utf8',str(Path(__file__).with_name('inherited_wave_pair_continuity.py'))]
    for key,value in paths.items():command+=['--'+key.replace('_','-'),str(value)]
    command+=['--output',str(destination)];subprocess.run(command,check=True)
    audit=verify_output(destination);target=destination/'graph_with_edges.json';current=load(target);root=current['sourceInheritedWavePairContinuity']
    if any(digest(path)!=before[key] for key,path in paths.items()):raise ValueError('inherited wave family inputs changed during execution')
    if (audit['mode']!=MODE or digest(target)!=audit['output_graph_sha256']
        or any(audit['inputs'][key]['sha256']!=before[key] or Path(audit['inputs'][key]['path']).resolve()!=path for key,path in paths.items())
        or root.get('source_sha256')!=before['source'] or root.get('input_graph_sha256')!=before['graph']
        or root.get('physical_lengths_assigned')!=0 or root.get('dependent_mapping_attributes_and_HIL_invalidated') is not True
        or root.get('human_accepted') is not False or current.get('metadata',{}).get('hil_ready') is not False):
        raise ValueError('inherited wave family evidence or invalidation differs')
    receipt=dict(status='native_inherited_wave_pairs_rebuilt_and_independently_replayed_hil_pending',
        source_sha256=before['source'],parent_graph_sha256=before['graph'],graph_sha256=audit['output_graph_sha256'],
        artifact_directory=str(destination),audit_sha256=digest(destination/'inherited-wave-receipt.json'),entry_sha256=digest(__file__),
        paired_omissions=audit['proof']['pairs'],components=audit['proof']['components'],physical_lengths_assigned=0,
        recompute_required=['crossview_inventory','mapping','DN_inheritance','attribute_fusion','source_comparison','HIL'],
        human_accepted=False,hil_ready=False)
    stage.parent.mkdir(parents=True,exist_ok=True);stage.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n','utf8')
    return target,audit
