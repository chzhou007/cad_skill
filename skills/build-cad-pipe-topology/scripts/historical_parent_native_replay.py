"""Replay an original parent in its actual pinned historical skill namespace.

No hash substitution or persisted pass flags. The original runtime/library and
all original owners execute from their actual paths, then the current module
namespace is restored. A caller's bounded read-tracking session may reuse this
fresh result only while its observed dependencies remain unchanged.
"""
import contextlib,importlib,sys,threading,functools,shutil,json
from pathlib import Path
from confirm_crossview_paths import load,sha

OWNER='adopt_current_named_prefix_evidence'
AUDIT='current-named-prefix-evidence-fusion-audit.json'
LEGACY_CACHE='14c1da94f6f12b15c6c55b3312fd1dd789a5d5db0a593934c2598c362edd61a3'
_lock=threading.RLock()

def materialize_runtime_overlay(directory,output):
    """Copy current assets with the one actually required historical library.

    All geometry owners must already match the parent receipt byte-for-byte.
    The historical library is shipped as an immutable compatibility asset.
    """
    current=Path(__file__).resolve().parents[2];output=Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    audit=load(Path(directory)/AUDIT)
    asset=current/'build-cad-pipe-topology/assets/native-runtime-legacy14/native_replay_session.py'
    if sha(asset)!=LEGACY_CACHE:raise ValueError('bundled historical runtime library bytes differ')
    for relative,digest in audit['implementation_sha256'].items():
        if relative=='native_replay_session.py':continue
        matches=[p for p in current.glob('*/scripts/'+relative)if p.is_file()and sha(p)==digest]
        if len(matches)!=1:raise ValueError('historical geometry owner needs its actual original source: '+relative)
    shutil.copytree(current,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copyfile(asset,output/'orchestrate-cad-drawing-pipeline/scripts/native_replay_session.py')
    inventory={p.relative_to(output).as_posix():sha(p)for p in output.rglob('*')if p.is_file()}
    record=dict(mode='one_library_historical_runtime_overlay_v1',source_skills_root=str(current),
        required_parent_audit_sha256=sha(Path(directory)/AUDIT),historical_cache_asset_sha256=LEGACY_CACHE,
        only_replaced_asset='orchestrate-cad-drawing-pipeline/scripts/native_replay_session.py',files=inventory)
    (output/'native-parent-runtime-overlay.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    preflight(directory,output)
    return output/'native-parent-runtime-overlay.json'

@functools.lru_cache(maxsize=8)
def verifier_for(historical_skills):
    # Cache function identity only. Each call still runs fresh unless the
    # caller's bounded native read-tracking session proves safe same-batch reuse.
    def verify(directory):return verify_parent(directory,Path(historical_skills))
    return verify

def script_module(module,roots):
    path=getattr(module,'__file__',None)
    if not path:return False
    path=Path(path).resolve()
    return any(path.is_relative_to(root)for root in roots)

@contextlib.contextmanager
def historical_namespace(historical_skills,current_skills):
    if threading.current_thread()is not threading.main_thread()or len(threading.enumerate())!=1:
        raise RuntimeError('historical native replay requires one main Python thread')
    historical_skills,current_skills=Path(historical_skills).resolve(),Path(current_skills).resolve()
    roots=[historical_skills,current_skills]
    names={p.stem for root in roots for p in root.glob('*/scripts/*.py')}
    saved_path=list(sys.path)
    with _lock:
        displaced={name:module for name,module in list(sys.modules.items())if name!='__main__'and(name in names or script_module(module,roots))}
        for name in displaced:sys.modules.pop(name,None)
        sys.path[:0]=[str(historical_skills/s/'scripts')for s in ('orchestrate-cad-drawing-pipeline','build-cad-pipe-topology','visualize-cad-pipe-topology')]
        importlib.invalidate_caches()
        try:yield
        finally:
            for name,module in list(sys.modules.items()):
                if name!='__main__'and(name in names or script_module(module,roots)):sys.modules.pop(name,None)
            sys.modules.update(displaced);sys.path[:]=saved_path;importlib.invalidate_caches()

def preflight(directory,historical_skills):
    directory=Path(directory).resolve();historical_skills=Path(historical_skills).resolve()
    current=Path(__file__).resolve().parents[2]
    if historical_skills==current:raise ValueError('distinct pinned historical skills required')
    audit=load(directory/AUDIT);cache=historical_skills/'orchestrate-cad-drawing-pipeline/scripts/native_replay_session.py'
    if sha(cache)!=LEGACY_CACHE or audit['implementation_sha256'].get('native_replay_session.py')!=LEGACY_CACHE:
        raise ValueError('historical parent cache library bytes differ')
    # Check every receipt implementation at its real source path before doing
    # any expensive parent, current mapping or DN replay.
    implementations={}
    for relative,digest in audit['implementation_sha256'].items():
        matches=[p for p in historical_skills.glob('*/scripts/'+relative)if p.is_file()and sha(p)==digest]
        if len(matches)!=1:raise ValueError('historical native implementation missing or competing: '+relative)
        implementations[relative]=dict(path=str(matches[0]),sha256=digest)
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('historical parent native input changed')
    with historical_namespace(historical_skills,current):
        runtime=importlib.import_module('native_direct_verification_runtime')
        information=runtime.install(LEGACY_CACHE)
        owner=importlib.import_module(OWNER)
        if owner.implementation_hashes()!=audit['implementation_sha256']:raise ValueError('historical original owner implementation identity differs')
    return dict(historical_skills_root=str(historical_skills),original_implementations=implementations,
        original_runtime_path=str(historical_skills/'orchestrate-cad-drawing-pipeline/scripts/native_direct_verification_runtime.py'),
        original_runtime_sha256=sha(historical_skills/'orchestrate-cad-drawing-pipeline/scripts/native_direct_verification_runtime.py'),
        original_cache_library_sha256=LEGACY_CACHE,adapter_sha256=sha(__file__))

def verify_parent(directory,historical_skills):
    directory=Path(directory).resolve();bridge=preflight(directory,historical_skills)
    current=Path(__file__).resolve().parents[2];historical_skills=Path(historical_skills).resolve()
    with historical_namespace(historical_skills,current):
        runtime=importlib.import_module('native_direct_verification_runtime');information=runtime.install(LEGACY_CACHE)
        owner=importlib.import_module(OWNER);result=owner.verify_output(directory)
        actual=information()
        if actual['original_cache_library_sha256']!=LEGACY_CACHE or actual['cached_results_reused']!=0 or actual['all_requested_verifiers_called']is not True:
            raise ValueError('historical original native replay runtime differs')
    if sha(directory/'graph_with_edges.json')!=result['output_graph_sha256']:raise ValueError('historical replay output changed')
    # This is separate new evidence; the original audit/receipt files are never
    # rewritten to claim that current runtime bytes were their old runtime.
    result=dict(result,native_historical_runtime_bridge=dict(bridge,original_owner_freshly_replayed=True,
        original_receipts_rewritten=False,persisted_pass_flags_preloaded=False,human_accepted=False))
    return result
