"""Execute only existing fingerprint-qualified pure Node attribute readers.

This stages source bytes, never caches values or rewrites the inline program.
"""
from pathlib import Path
import hashlib,importlib,json,sys,threading,re

STATIC_IMPORTS=re.compile(r"\b(?:import|export)\b\s*[^;]+?\bfrom\s*['\"]([^'\"]+)['\"]")

def qualify_root(runtime,owner):
    """Bind a current or explicitly indexed historical reader policy."""
    modes=('exact_current_attribute_reader_inputs_v1','shipped_pure_attribute_reader_inputs_v1')
    root=Path(owner.root).resolve();policy=Path(owner.policy_path).resolve()
    if owner.policy.get('mode')not in modes:
        raise PermissionError('Node reader policy mode differs')
    if root==runtime.package/'skills':return
    for binding in runtime.index.get('qualified_node_reader_roots',[]):
        if runtime.key(binding['root'])!=runtime.key(root)or runtime.key(binding['policy'])!=runtime.key(policy):continue
        if policy.parent!=root/'orchestrate-cad-drawing-pipeline/assets':
            raise PermissionError('Historical Node policy leaves its declared root')
        declaration=runtime.files.get(runtime.key(policy))
        if (not declaration or declaration['sha256']!=binding['sha256']
                or binding['mode']!=owner.policy['mode']or owner.policy_hash!=binding['sha256']):
            raise PermissionError('Historical Node policy is not byte-bound to delivered inputs')
        runtime.checked_file(runtime.key(policy))
        return
    raise PermissionError('Node reader qualification root or policy differs')


def install(runtime):
    import native_attribute_read_runtime as base
    import current_attribute_read_runtime as current
    # The historical frozen reader misses valid compact `}from` statements.
    # Expand its dependency matcher; original function/policy checks stay on.
    base.IMPORTS=STATIC_IMPORTS;current.IMPORTS=STATIC_IMPORTS
    index=runtime.package/'indexes'/(runtime.index_sha256+'.json')
    dependencies=[runtime.adapter_path,Path(__file__),index]
    for cls in (base.Runtime,current.Runtime):
        original=cls.snapshot
        def snapshot(owner,bundle,fn,_original=original):
            value=_original(owner,bundle,fn)
            if value is not None:
                # These reads happen in the original active dependency trace,
                # before its bounded native call, and again after execution.
                value.update({str(path):base.sha(path)for path in dependencies})
            return value
        cls.snapshot=snapshot

def locate(runtime,argv,kwargs):
    if not isinstance(argv,(list,tuple))or not argv or Path(str(argv[0])).name.lower()not in('node','node.exe'):return None
    if kwargs.get('env')is not None or kwargs.get('cwd')is not None:raise PermissionError('Readonly Node reader changed startup settings')
    from native_attribute_read_runtime import Runtime as Original
    frame=sys._getframe(1);found=None
    while frame:
        if frame.f_code is Original.call.__code__ and isinstance(frame.f_locals.get('before'),dict):found=frame;break
        frame=frame.f_back
    if found is None:raise PermissionError('Node call is outside the original qualified reader bridge')
    owner=found.f_locals['self'];original=found.f_locals['original'];bundle=found.f_locals['bundle'];before=found.f_locals['before']
    qualify_root(runtime,owner)
    from current_attribute_read_runtime import command,command_inputs,module_closure
    if list(argv)!=command(original,bundle)or owner.snapshot(bundle,original)!=before:raise ValueError('Qualified Node inputs or command changed')
    entry,graph,manifest,script_sha=command_inputs(argv,bundle);modules=module_closure(entry)
    for name,digest in modules.items():
        if before.get(str(entry.parent/name))!=digest:raise ValueError('Node module is outside the qualified closure')
    package_source=None;package_bytes=b'{}\n'
    for folder in(entry.parent,*entry.parent.parents):
        candidate=folder/'package.json'
        if str(candidate)in before:package_source=candidate;package_bytes=candidate.read_bytes();break
    values={name:(entry.parent/name).read_bytes()for name in modules}
    values.update({'data/graph.json':graph.read_bytes(),'data/manifest.json':manifest.read_bytes()})
    key=hashlib.sha256(json.dumps(dict(module=modules,graph=before[str(graph)],manifest=before[str(manifest)],package=hashlib.sha256(package_bytes).hexdigest()),sort_keys=True).encode()).hexdigest()
    stage=runtime.work/'readonly-node-inputs'/key;stage.mkdir(parents=True,exist_ok=True)
    targets={'public/'+name:data for name,data in values.items()};targets['package.json']=package_bytes
    for relative,data in targets.items():
        path=stage/relative;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():
            if path.read_bytes()!=data:raise ValueError('Readonly Node staged input changed')
        else:path.write_bytes(data)
    count=len(argv)-4
    if count==3:tail=[str(stage/'public'/entry.name),str(stage/'public/data/graph.json'),str(stage/'public/data/manifest.json')]
    elif count==2:tail=[str(stage),entry.name]
    elif count==1:tail=[str(stage)]
    else:raise ValueError('Unsupported qualified Node argument shape')
    actual=[runtime.translate(owner.node,'qualified Node engine'),*argv[1:4],*tail]
    proof=dict(role='original_fingerprinted_pure_attribute_reader',inline_script_sha256=script_sha,
        original_bundle=str(bundle),staged_bundle=str(stage),engine_sha256=before[owner.node],
        source_files=before,staged_files={name:hashlib.sha256(data).hexdigest()for name,data in targets.items()},
        package_source=str(package_source)if package_source else None,values_cached=False,inline_script_rewritten=False)
    return actual,proof
