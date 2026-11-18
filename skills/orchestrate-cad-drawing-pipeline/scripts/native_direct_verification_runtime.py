"""Explicit native-only compatibility backend for a fresh worker process.

The pinned optional cache library's no-session behavior is simply a direct
verifier call. This backend provides that behavior without registering unused
cache-read audit hooks. It never reuses results or substitutes geometry rules.
Historical library bytes and receipts remain in their versioned packages.
Cache options remain disabled in this direct backend, including newer flags.
"""
import contextlib,hashlib,sys,types
from pathlib import Path

LEGACY_CACHE_LIBRARY_SHA256='14c1da94f6f12b15c6c55b3312fd1dd789a5d5db0a593934c2598c362edd61a3'
SUPPORTED_CACHE_LIBRARY_SHA256='4c43202b5bd89aec56bcc47f9cc8e0df03d0e434b1fe5a2caf5475f05522b4b8'
SUPPORTED_CACHE_LIBRARY_VERSIONS=frozenset((LEGACY_CACHE_LIBRARY_SHA256,SUPPORTED_CACHE_LIBRARY_SHA256))


def install(expected_cache_hash):
    if 'native_replay_session' in sys.modules:raise RuntimeError('native-only backend requires a fresh worker; an imported runtime must not be replaced')
    original=Path(__file__).with_name('native_replay_session.py');digest=hashlib.sha256(original.read_bytes()).hexdigest()
    if expected_cache_hash not in SUPPORTED_CACHE_LIBRARY_VERSIONS or digest!=expected_cache_hash:raise ValueError('unsupported optional cache library version')
    state=dict(verify_once_requests=0)
    def verify_once(directory,verifier):
        state['verify_once_requests']+=1
        return verifier(directory)
    class Session:
        def __init__(self):self.start=state['verify_once_requests']
        def statistics(self):return dict(native_replays=state['verify_once_requests']-self.start,same_batch_reuses=0,invalidations=0,dependency_files=0,persistent_trust=False)
    @contextlib.contextmanager
    def replay_session(*,allow_owned_scratch=False,python_replay_entries=()):yield Session()
    module=types.ModuleType('native_replay_session','Explicit native-only backend; no verification result cache or optional read tracking.')
    module.__file__=str(Path(__file__).resolve());module.verify_once=verify_once;module.replay_session=replay_session;module.Session=Session
    module.execution_backend='native_direct_verification_v1';sys.modules['native_replay_session']=module
    def information():return dict(execution_backend=module.execution_backend,original_cache_library_path=str(original.resolve()),original_cache_library_sha256=digest,
        runtime_path=str(Path(__file__).resolve()),runtime_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        verify_once_requests=state['verify_once_requests'],cached_results_reused=0,optional_cache_read_tracking=False,all_requested_verifiers_called=True)
    return information
