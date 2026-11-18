"""Verify and launch a published review package with its own Python runtime."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import runpy
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent
MUTABLE = ('startup-logs', 'viewer/annotations', 'viewer/startup-logs')


def resolved_path(path):
    resolved = str(Path(path).resolve())
    # Windows can retain the extended-length prefix while another thread is
    # creating an ancestor. It is the same namespace, not a path escape.
    if os.name == 'nt':
        if resolved.startswith('\\\\?\\UNC\\'):
            resolved = '\\\\' + resolved[8:]
        elif resolved.startswith('\\\\?\\'):
            resolved = resolved[4:]
    return Path(resolved)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, relative):
    parts = PurePosixPath(relative)
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or ':' in relative or parts.is_absolute()
            or any(p in ('', '.', '..') for p in relative.split('/'))):
        raise ValueError('Invalid package-relative path: ' + str(relative))
    path = root.joinpath(*parts.parts)
    resolved, resolved_root = resolved_path(path), resolved_path(root)
    if not resolved.is_relative_to(resolved_root):
        raise ValueError('Package path escapes root: ' + relative + ' (' + str(resolved) + ' outside ' + str(resolved_root) + ')')
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)():
            raise ValueError('Linked package path: ' + relative)
    return path


def mutable(relative):
    return any(relative == p or relative.startswith(p + '/') for p in MUTABLE)


def verify_payload(root, workers=8):
    root = Path(root).resolve()
    manifest = json.loads(confined(root, 'payload-manifest.json').read_text('utf8'))
    if manifest['schema'] != 'published_current_review_payload_v1':
        raise ValueError('Unsupported published review payload')
    entries = manifest['files']
    keys = list(entries)
    if len({k.casefold() for k in keys}) != len(keys):
        raise ValueError('Case-insensitive payload collision')
    if any(mutable(k) or k == 'payload-manifest.json' for k in keys):
        raise ValueError('Mutable review data cannot be immutable payload')
    expected = set(keys) | {'payload-manifest.json'}
    for path in root.rglob('*'):
        rel = path.relative_to(root).as_posix()
        confined(root, rel)
        if path.is_file() and not mutable(rel) and rel not in expected:
            raise ValueError('Unlisted immutable payload file: ' + rel)

    def check(item):
        name, record = item
        path = confined(root, name)
        if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
            raise ValueError('Payload changed: ' + name)

    with ThreadPoolExecutor(max_workers=max(1, min(workers, 32))) as pool:
        list(pool.map(check, entries.items()))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--port', type=int)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--serve-child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = ROOT.resolve()
    logs = confined(root, 'startup-logs')
    logs.mkdir(exist_ok=True)
    diagnostic = dict(checked_at=datetime.now(timezone.utc).isoformat(), status='FAIL',
                      raw_CAD_reconstruction_performed=False, human_accepted=False)
    try:
        if Path(sys.executable).resolve() != confined(root, 'runtime/python.exe'):
            raise ValueError('Use the bundled runtime through start.cmd or diagnose.cmd')
        if not sys.flags.isolated:
            raise ValueError('The bundled runtime must use isolation mode')
        manifest = verify_payload(root, args.workers)
        port = args.port if args.port is not None else manifest['preferred_port']
        if not 1024 <= port <= 65535:
            raise ValueError('Invalid local port')
        viewer = confined(root, 'viewer')
        # The standard runtime deliberately excludes the script directory. Add
        # only this verified package viewer for the original sibling imports.
        sys.path.insert(0, str(viewer))
        if args.serve_child:
            sys.argv = [str(viewer / 'serve.py'), '--port', str(port)]
            if args.open:
                sys.argv.append('--open')
            runpy.run_path(str(viewer / 'serve.py'), run_name='__main__')
            return 0
        original = runpy.run_path(str(viewer / 'launch_review.py'), run_name='_portable_preflight_')
        checks = original['preflight'](viewer, original['targets'](viewer))
        if checks['status'] != 'PASS':
            raise ValueError('; '.join(checks['errors']))
        diagnostic.update(status='PASS', payload_files=len(manifest['files']),
                          python=sys.executable, isolated=sys.flags.isolated,
                          original_preflight=checks, preferred_port=port,
                          check_only=args.check_only, scope=manifest['scope'])
        (logs / 'diagnostics.json').write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        print('PASS: published review payload and bundled runtime verified.', flush=True)
        if args.check_only:
            return 0
        env = dict(os.environ, PYTHONHOME='Z:/absent-python-home',
                   PYTHONPATH='Z:/absent-python-path', PYTHONNOUSERSITE='1')
        command = [sys.executable, '-I', '-X', 'utf8', '-B', '-u', str(root / 'launch_portable_review.py'),
                   '--serve-child', '--port', str(port)]
        if args.open:
            command.append('--open')
        with (logs / 'server.log').open('a', encoding='utf8') as log:
            child = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace')
            try:
                for line in child.stdout:
                    print(line, end='', flush=True)
                    log.write(line)
                    log.flush()
                return child.wait()
            except KeyboardInterrupt:
                return 0
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=10)
                child.stdout.close()
    except Exception as error:
        diagnostic['error'] = str(error)
        (logs / 'diagnostics.json').write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        with (logs / 'startup.log').open('a', encoding='utf8') as log:
            log.write(traceback.format_exc())
        print('STARTUP FAILED: ' + str(error), flush=True)
        print('See startup-logs/diagnostics.json and startup.log.', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
