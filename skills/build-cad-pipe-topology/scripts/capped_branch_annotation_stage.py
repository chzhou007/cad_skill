"""Optional family-owned annotation sidecar; no topology rewrite or HIL closure."""
import hashlib,json,subprocess,sys
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text('utf-8-sig'))


def load_policy_map(path,eligible=None):
    if path is None:return {}
    path=Path(path).resolve();values=load(path)
    if not isinstance(values,dict) or eligible is not None and set(values)-set(eligible):raise ValueError('invalid capped-branch annotation task map')
    result={}
    for task,value in values.items():
        if not isinstance(task,str) or not task or not isinstance(value,dict) or set(value)!={'policy'} or not isinstance(value['policy'],str) or not value['policy'].strip():raise ValueError('annotation map can select only a policy, not source/graph/output')
        policy=Path(value['policy']);policy=(policy if policy.is_absolute() else path.parent/policy).resolve()
        if not policy.is_file():raise ValueError('missing annotation policy')
        result[task]=policy
    return result


def run_stage(source,graph,policy,task_root):
    from native_capped_branch_annotations import verify_output
    source,graph,policy,task_root=(Path(p).resolve() for p in (source,graph,policy,task_root))
    if not graph.is_relative_to(task_root):raise ValueError('annotation graph must be owned by current family task')
    paths=dict(source=source,graph=graph,policy=policy);before={key:digest(p) for key,p in paths.items()}
    out=task_root/'reports/native-capped-branch-annotations';stage=task_root/'reports/native-capped-branch-annotations-stage.json'
    if out.exists() or stage.exists():raise FileExistsError('annotation stage already exists')
    owner=Path(__file__).with_name('native_capped_branch_annotations.py')
    subprocess.run([sys.executable,'-X','utf8',str(owner),'--source',str(source),'--graph',str(graph),'--policy',str(policy),'--output',str(out)],check=True)
    audit=verify_output(out)
    if any(digest(paths[key])!=value for key,value in before.items()):raise ValueError('annotation input changed during family stage')
    if audit['inputs']['graph']['sha256']!=before['graph'] or audit['inputs']['source']['sha256']!=before['source'] or audit['graph_mutated'] or audit['hil_ready']:
        raise ValueError('annotation stage must preserve exact current graph/source and unaccepted state')
    receipt=dict(status='source_annotation_sidecar_native_replayed_topology_unchanged',source_sha256=before['source'],graph_sha256=before['graph'],
        policy_sha256=before['policy'],reader_sha256=digest(owner),entry_sha256=digest(__file__),audit_sha256=digest(out/'native-capped-branch-annotations-audit.json'),
        artifact_directory=str(out),records=audit['records'],graph_mutated=False,connections_added=0,retired_nodes=0,physical_lengths_assigned=0,hil_ready=False,human_accepted=False)
    stage.parent.mkdir(parents=True,exist_ok=True);stage.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return receipt
