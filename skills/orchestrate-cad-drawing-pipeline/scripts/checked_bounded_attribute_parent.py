"""Apply an immutable bounded-attribute parent with current byte checks."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
from checked_native_parent_application import tree,sha,encode
import hashlib
LAST_APPLICATION={}
OWNER='rebuild_bounded_main_complete_extents'

def check(spec,current_root):
    if spec.get('owner')!=OWNER:raise ValueError('unsupported bounded attribute parent')
    root=Path(spec['skills_root']).resolve();files=tree(root)
    if hashlib.sha256(encode(files)).hexdigest()!=spec['skill_tree_sha256']:raise ValueError('immutable bounded parent rule version changed')
    for name,digest in files.items():
        if not name.endswith('.py')or '/scripts/'not in name or not name.startswith(('build-cad-pipe-topology/','orchestrate-cad-drawing-pipeline/'))or name=='orchestrate-cad-drawing-pipeline/scripts/pipeline.py':continue
        target=Path(current_root)/name
        if not target.is_file()or sha(target)!=digest:raise ValueError('inherited native algorithm changed; requalify bounded parent: '+name)
    policy=Path(spec['environment_policy']);proof=Path(spec['native_run'])/'bounded-main-extents.json'
    if sha(policy)!=spec['environment_policy_sha256']or sha(proof)!=spec['proof_sha256']:raise ValueError('bounded parent policy or complete proof changed')
    return root,proof,json.loads(policy.read_text(encoding='utf-8'))

def apply(spec,current_root):
    root,proof,policy=check(spec,current_root)
    if policy.get('scope')!='isolated_pure_native_worker_only':raise ValueError('unexpected bounded parent environment policy')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',CAD_NATIVE_WORKERS=str(spec['workers']),CAD_NATIVE_OWNER_BATCH_VERSION='1')
    env.pop('PYTHONPATH',None);env['CODEX_TOOL_CALL_ID']=policy['stable_transport_context']
    with tempfile.TemporaryDirectory(prefix='cad-bounded-parent-')as scratch:
        output=Path(scratch)/'application'
        cmd=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/pipeline.py'),'reuse-bounded-attribute-artifact','--native-run',str(Path(spec['native_run']).resolve()),'--cache-root',str(Path(spec['cache_root']).resolve()),'--output',str(output),'--skills-root',str(root),'--hash-workers','16']
        result=subprocess.run(cmd,cwd=spec['cwd'],env=env,capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise ValueError('bounded parent current dependency checks failed: '+(result.stdout+result.stderr)[-2000:])
        audit=json.loads((output/'execution.json').read_text(encoding='utf-8'));raw=(output/'proof.json').read_bytes()
        if audit.get('owner')!=OWNER or audit.get('mode')!='content_checked_complete_native_artifact_reuse_v1'or audit.get('proof_sha256')!=spec['proof_sha256']or audit.get('human_accepted')is not False or not(audit.get('native_replay_performed')is True or audit.get('dependency_checked_reuse')is True)or raw!=proof.read_bytes():raise ValueError('complete bounded parent application differs')
    check(spec,current_root);LAST_APPLICATION.clear();LAST_APPLICATION.update(audit)
    return json.loads(raw),dict(owner=OWNER,proof_sha256=spec['proof_sha256'],original_skill_tree_sha256=spec['skill_tree_sha256'],current_inherited_algorithm_bytes_equal=True,current_dependency_checked=True,parent_application_is_not_new_family_native_reconstruction=True,human_accepted=False)
