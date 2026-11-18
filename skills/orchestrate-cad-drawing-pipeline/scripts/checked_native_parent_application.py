"""Apply an immutable original parent version with fresh dependency checks.

Only the separate content-checked native entry is called. Its complete original
proof bytes, current source bindings and current inherited algorithm bytes are
required; neither a prior execution status nor a stored pass flag is consumed.
"""
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path

NAMES=('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology','extract-cad-building-context')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def encode(value):return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8')
def tree(root):
    root=Path(root);result={}
    for name in NAMES:
        if not (root/name).is_dir():raise ValueError('complete immutable parent skill version required')
        for p in (root/name).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':result[p.relative_to(root).as_posix()]=sha(p)
    return dict(sorted(result.items()))
def check(spec,current_root):
    if spec.get('owner')!='rebuild_compound_member_projections':raise ValueError('unsupported checked parent owner')
    root=Path(spec['skills_root']).resolve();files=tree(root)
    digest=hashlib.sha256(encode(files)).hexdigest()
    if digest!=spec['skill_tree_sha256']:raise ValueError('immutable parent rule version changed')
    # New rules may extend a version; an edited inherited algorithm needs a new
    # parent reconstruction, even if the historical frozen tree is untouched.
    for name,digest_file in files.items():
        if not name.endswith('.py') or '/scripts/' not in name:continue
        if not name.startswith(('build-cad-pipe-topology/','orchestrate-cad-drawing-pipeline/')):continue
        if name=='orchestrate-cad-drawing-pipeline/scripts/pipeline.py':continue
        target=Path(current_root)/name
        if not target.is_file() or sha(target)!=digest_file:raise ValueError('inherited native algorithm changed; requalify parent: '+name)
    policy=Path(spec['environment_policy'])
    if sha(policy)!=spec['environment_policy_sha256']:raise ValueError('native parent execution policy changed')
    if not Path(spec['cwd']).is_dir() or not Path(spec['native_run']).is_dir():raise ValueError('original parent paths missing')
    proof=Path(spec['native_run'])/'member-projections.json'
    if sha(proof)!=spec['proof_sha256']:raise ValueError('original parent artifact changed')
    return root,proof,json.loads(policy.read_text(encoding='utf8'))

def apply(spec,current_root):
    root,proof,policy=check(spec,current_root)
    if policy.get('scope')!='isolated_pure_native_worker_only':raise ValueError('unexpected parent environment policy')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CAD_NATIVE_WORKERS=str(spec['workers']),CAD_NATIVE_OWNER_BATCH_VERSION='1')
    env.pop('PYTHONPATH',None);env['CODEX_TOOL_CALL_ID']=policy['stable_transport_context']
    with tempfile.TemporaryDirectory(prefix='cad-checked-parent-') as scratch:
        output=Path(scratch)/'application'
        command=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/pipeline.py'),'reuse-native-artifact',
            '--owner',spec['owner'],'--native-run',str(Path(spec['native_run']).resolve()),'--cache-root',str(Path(spec['cache_root']).resolve()),'--output',str(output),'--hash-workers','16']
        result=subprocess.run(command,cwd=spec['cwd'],env=env,capture_output=True,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise ValueError('current original-parent dependency checks failed: '+(result.stdout+result.stderr)[-2000:])
        audit=json.loads((output/'execution.json').read_text(encoding='utf8'));raw=(output/'proof.json').read_bytes()
        if (audit.get('mode')!='content_checked_complete_native_artifact_reuse_v1' or audit.get('owner')!=spec['owner']
            or audit.get('proof_sha256')!=spec['proof_sha256'] or audit.get('human_accepted')is not False
            or (audit.get('native_replay_performed')is not True and audit.get('dependency_checked_reuse')is not True)
            or raw!=proof.read_bytes()):raise ValueError('original parent application output differs')
    check(spec,current_root)
    # Stable semantic provenance; cold/warm timing and execution mode belong in
    # the operational child receipt, not in a source proof's changing bytes.
    return json.loads(raw),dict(owner=spec['owner'],proof_sha256=spec['proof_sha256'],original_skill_tree_sha256=spec['skill_tree_sha256'],
        current_inherited_algorithm_bytes_equal=True,current_dependency_checked=True,qualification_policy='original_complete_verifier_or_current_content_checked_artifact_application',human_accepted=False)
