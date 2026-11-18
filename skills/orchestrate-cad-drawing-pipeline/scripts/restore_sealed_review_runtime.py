"""Restore the qualified review/attribute leg from sealed blobs, not live files.

This is not the raw-CAD reconstruction entry. Historical absolute proof paths
remain verbatim evidence. Runtime, facade execution and public viewer files are
restored to fresh confined namespaces, without touching the source installation.
"""
from pathlib import Path, PureWindowsPath
import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys



def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checked_relative(source, prefix):
    p, base = PureWindowsPath(source), PureWindowsPath(prefix)
    if not p.is_absolute() or '..' in p.parts:
        raise ValueError('Unsafe logical input')
    if not p.is_relative_to(base):
        return None
    parts = p.relative_to(base).parts
    if not parts or any(':' in x or x in ('.', '..') for x in parts):
        raise ValueError('Unsafe relative input')
    return parts


def plan(files, binding):
    spellings = {}
    for name, digest in binding['runtime_and_skill_files'].items():
        key = str(PureWindowsPath(name)).lower()
        if key in spellings and spellings[key] != (name, digest):
            raise ValueError('Conflicting bound path spelling')
        spellings[key] = (name, digest)
    roots = {}
    for filename, key in [('python312.dll', 'runtime/python'), ('node.exe', 'runtime/node')]:
        candidates = {str(PureWindowsPath(n).parent) for n in files if PureWindowsPath(n).name == filename}
        if len(candidates) != 1:
            raise ValueError('One bound runtime namespace required: ' + filename)
        roots[key] = candidates.pop()
    roots.update({'skills': binding['skills_root'], 'viewer': binding['directory'],
                  'runtime/site-packages': str(PureWindowsPath(binding['executable_path']).parent.parent/'Lib'/'site-packages')})
    result, targets = [], set()
    for logical, digest in files.items():
        if not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Invalid blob digest')
        spelling, bound_digest = spellings.get(str(PureWindowsPath(logical)).lower(), (logical, digest))
        if bound_digest != digest:
            raise ValueError('Bound original spelling has a different digest')
        matches = [(root, parts) for root, prefix in roots.items()
                   if (parts := checked_relative(spelling, prefix)) is not None]
        if not matches:
            continue
        if len(matches) != 1:
            raise ValueError('Overlapping restore namespaces')
        root, parts = matches[0]
        relative = Path(root).joinpath(*parts).as_posix()
        if relative.lower() in targets:
            raise ValueError('Case-insensitive destination collision')
        targets.add(relative.lower())
        result.append({'logical': logical, 'bound_spelling': spelling, 'relative': relative, 'sha256': digest})
    if not all(any(x['relative'].startswith(k + '/') for x in result) for k in roots):
        raise ValueError('A required namespace is absent')
    return result


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


WORKER = '''from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
for name in ('visualize-cad-pipe-topology','build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
 sys.path.insert(0,str(ROOT/'skills'/name/'scripts'))
import numpy,ezdxf
import refresh_reviewed_ring_partition_DN as reader
assert Path(reader.__file__).resolve().is_relative_to(ROOT/'skills')
for module in (numpy,ezdxf):
 assert Path(module.__file__).resolve().is_relative_to(ROOT/'runtime')
actual=reader.effective(ROOT/'viewer')
expected=json.loads((ROOT/'viewer/effective-provider-refresh/current-effective.json').read_text('utf8'))
if actual!=expected:raise ValueError('Independent current attribute values differ')
result=dict(mode='isolated_delivered_current_facade_reexecution_v1',edge_count=len(actual),
 every_effective_field_exact=True,python=sys.executable,sys_path=sys.path,
 reader_file=reader.__file__,numpy_file=numpy.__file__,ezdxf_file=ezdxf.__file__,
 isolated=sys.flags.isolated,ignore_environment=sys.flags.ignore_environment,
 raw_CAD_reconstruction_performed=False,human_accepted=False)
(ROOT/'verification/actual-effective.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2)+'\\n',encoding='utf8')
(ROOT/'verification/attribute-replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='sys_path'},ensure_ascii=False))
'''


LAUNCHER = '''"""Run the original standard-library viewer with the bundled interpreter."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,os,datetime
ROOT=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');p.add_argument('--port',type=int,default=10420);p.add_argument('--open',action='store_true');a=p.parse_args()
 if not 1024<=a.port<=65535:raise ValueError('Invalid local port')
 if Path(sys.executable).resolve()!=ROOT/'runtime/python/python.exe':raise ValueError('Use the supplied interpreter')
 entries=json.loads((ROOT/'payload-manifest.json').read_text('utf8'))['files']
 for rel,digest in entries.items():
  raw=ROOT/rel
  path=raw.resolve()
  if not path.is_relative_to(ROOT) or any(q.is_symlink() for q in [raw,*raw.parents] if q!=ROOT and q.is_relative_to(ROOT)):raise ValueError('Unsafe payload path')
  if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Payload changed: '+rel)
 print('Payload verified; original graph, source and attribute evidence preserved.',flush=True)
 logs=ROOT/'startup-logs';logs.mkdir(exist_ok=True)
 (logs/'diagnostics.json').write_text(json.dumps(dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),payload_files=len(entries),python=sys.executable,isolated=sys.flags.isolated,port=a.port,check_only=a.check_only,raw_CAD_reconstruction_performed=False),indent=2)+'\\n',encoding='utf8')
 if a.check_only:return
 env=dict(os.environ,PYTHONHOME='Z:/absent-python-home',PYTHONPATH='Z:/absent-python-path',PYTHONNOUSERSITE='1')
 command=[str(ROOT/'runtime/python/python.exe'),'-I','-X','utf8','-B','-u',str(ROOT/'viewer/serve.py'),'--strict-port','--port',str(a.port)]
 if a.open:command.append('--open')
 result=subprocess.run(command,cwd=ROOT/'viewer',env=env)
 raise SystemExit(result.returncode)
if __name__=='__main__':main()
'''


def restore(corpus, output, manifest_sha, binding_sha):
    corpus, output = Path(corpus).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Fresh output required: ' + str(output))
    if not all(re.fullmatch('[0-9a-f]{64}', h) for h in (manifest_sha, binding_sha)):
        raise ValueError('Explicit trusted corpus and binding hashes required')
    if sha(corpus/'manifest.json') != manifest_sha or sha(corpus/'runtime-binding.json') != binding_sha:
        raise ValueError('Fixed corpus/binding changed')
    manifest = json.loads((corpus/'manifest.json').read_text('utf8'))
    binding = json.loads((corpus/'runtime-binding.json').read_text('utf8'))
    jobs = plan(manifest['logical_files'], binding)
    output.mkdir(parents=True)
    (output/'verification').mkdir()

    def copy_one(row):
        blob = corpus/'blobs'/row['sha256']
        if blob.is_symlink() or sha(blob) != row['sha256']:
            raise ValueError('Blob changed: ' + row['relative'])
        target = output/row['relative']
        target.parent.mkdir(parents=True, exist_ok=True)
        # Resolve after the parent exists: concurrent Windows mkdir/resolve on
        # missing ancestors can produce an inconsistent final-path namespace.
        if not target.parent.resolve().is_relative_to(output):
            raise ValueError('Destination parent escaped package: ' + str(target))
        shutil.copyfile(blob, target)
        if sha(target) != row['sha256']:
            raise ValueError('Restored bytes changed')
        return row['relative'], row['sha256']

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        inventory = dict(pool.map(copy_one, jobs))
    for name in ['python312._pth', 'python._pth', 'python3.12._pth']:
        p = output/'runtime/python'/name
        p.write_text('.\nDLLs\nLib\n../site-packages\n../../viewer\n', encoding='utf8')
        inventory[p.relative_to(output).as_posix()] = sha(p)
    for name, text in [('replay_delivered_attributes.py', WORKER), ('launch_portable_review.py', LAUNCHER)]:
        p = output/name
        p.write_text(text, encoding='utf8')
        inventory[name] = sha(p)
    for name, args in [('start.cmd', '--open'), ('diagnose.cmd', '--check-only')]:
        p = output/name
        p.write_text('@echo off\r\ncd /d "%~dp0"\r\n"%~dp0runtime\\python\\python.exe" -I -X utf8 -B "%~dp0launch_portable_review.py" '+args+' %*\r\nif errorlevel 1 pause\r\n', encoding='ascii', newline='')
        inventory[name] = sha(p)
    dump(output/'payload-manifest.json', {'mode': 'sealed_review_runtime_payload_v1',
        'source_corpus_sha256': manifest_sha, 'files': inventory,
        'scope': 'qualified attribute facade reexecution and original source viewer',
        'raw_CAD_reconstruction_performed': False, 'human_accepted': False})
    dump(output/'verification/restoration.json', {'source_corpus_sha256': manifest_sha,
        'runtime_binding_sha256': binding_sha, 'restored_files': len(jobs),
        'original_files_byte_exact': True, 'historical_proofs_rewritten': False,
        'annotation_files_in_fixed_corpus': sum('/annotations/' in x['relative'] for x in jobs),
        'annotation_state_created_or_confirmed': False, 'global_installation_modified': False})
    print(json.dumps({'restored': len(jobs), 'output': str(output)}, ensure_ascii=False), flush=True)
    env = dict(os.environ, PYTHONHOME='Z:/absent-python-home', PYTHONPATH='Z:/absent-python-path',
               PYTHONUSERBASE='Z:/absent-python-user', PATH=str(output/'runtime/node')+';'+os.environ['SystemRoot']+'\\System32')
    exe = output/'runtime/python/python.exe'
    for name, command in [('attribute-replay', [str(exe), '-I', '-X', 'utf8', '-B', str(output/'replay_delivered_attributes.py')]),
                          ('launcher-check', [str(exe), '-I', '-X', 'utf8', '-B', str(output/'launch_portable_review.py'), '--check-only'])]:
        run = subprocess.run(command, cwd=output, env=env, capture_output=True, text=True, encoding='utf8',
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        dump(output/'verification'/f'{name}-process.json', dict(exit_code=run.returncode, stdout=run.stdout, stderr=run.stderr))
        print(name, run.returncode, run.stderr[-1800:], flush=True)
        if run.returncode:
            raise RuntimeError(name + ' failed; retained process receipt')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--corpus', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--binding-sha256', required=True)
    a = p.parse_args()
    restore(a.corpus, a.output, a.manifest_sha256, a.binding_sha256)


if __name__ == '__main__':
    main()
