"""Package a hash-bound published viewer and a verified standard Python role.

This copies published results. It does not claim raw CAD reconstruction or
recompute external historical evidence references embedded in those results.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import uuid
import zipfile

ASSET = Path(__file__).resolve().parents[1] / 'assets/viewer/portable_review.py'
spec = importlib.util.spec_from_file_location('_portable_review_asset', ASSET)
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)
digest, confined = portable.digest, portable.confined


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def inventory(root, excluded=()):
    root = Path(root).resolve()
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        confined(root, relative)
        if any(relative == e or relative.startswith(e + '/') for e in excluded):
            continue
        if path.is_file():
            result[relative] = dict(sha256=digest(path), bytes=path.stat().st_size)
    if len({k.casefold() for k in result}) != len(result):
        raise ValueError('Case-insensitive input collision')
    return result


def package(binding_path, binding_sha256, output, workers=8):
    binding_path, output = Path(binding_path).resolve(), Path(output).resolve()
    if digest(binding_path) != binding_sha256:
        raise ValueError('Package binding changed')
    binding = json.loads(binding_path.read_text('utf8'))
    if binding['schema'] != 'published_current_review_binding_v1':
        raise ValueError('Unsupported current review binding')
    if not 1024 <= binding['preferred_port'] <= 65535:
        raise ValueError('Invalid local port')
    roots = {key: Path(binding[key]['path']).resolve() for key in ('viewer', 'runtime')}
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in roots.values()):
        raise ValueError('Output and source namespaces must be disjoint')
    archive = Path(str(output) + '.zip')
    if output.exists() or archive.exists():
        raise FileExistsError('Fresh output and ZIP required')
    excluded = ('startup-logs', '__pycache__', 'annotations')
    for key, root in roots.items():
        actual = inventory(root, excluded if key == 'viewer' else ('__pycache__',))
        if actual != binding[key]['files']:
            raise ValueError(key + ' input inventory changed')
    required = ['serve.py', 'hil_server.py', 'launch_review.py', 'public/index.html',
                'public/data/graph.json', 'public/data/manifest.json', 'public/data/cad.svg']
    if not all(n in binding['viewer']['files'] for n in required):
        raise ValueError('Incomplete original published viewer')
    if 'python.exe' not in binding['runtime']['files']:
        raise ValueError('Bundled interpreter missing')
    # Use the already materialized standard-library role. Do not merge arbitrary
    # host packages or alter the original path configuration during packaging.
    pth = [p for p in roots['runtime'].glob('*._pth')]
    if not pth or any(line.strip() not in ('', '.', 'DLLs', 'Lib', 'Lib/site-packages')
                      for p in pth for line in p.read_text('utf8').splitlines()):
        raise ValueError('Runtime must use the package-only standard Python role')
    stage = output.with_name(output.name + '.building-' + uuid.uuid4().hex[:10])
    stage.mkdir(parents=True)
    planned = {}
    for key, root in roots.items():
        for relative, record in binding[key]['files'].items():
            planned[key + '/' + relative] = (confined(root, relative), record)
    for extra in binding.get('extras', []):
        target = extra['relative']
        confined(stage, target)
        if target.split('/')[0] not in ('sources', 'evidence', 'skills'):
            raise ValueError('Extra inputs require an explicit evidence/source/skill namespace')
        if target in planned:
            raise ValueError('Duplicate payload destination')
        planned[target] = (Path(extra['path']).resolve(), dict(sha256=extra['sha256'], bytes=extra['bytes']))
    if len({p.casefold() for p in planned}) != len(planned):
        raise ValueError('Case-insensitive payload destination collision')

    def copy(item):
        relative, (source, expected) = item
        if source.stat().st_size != expected['bytes'] or digest(source) != expected['sha256']:
            raise ValueError('Input changed: ' + str(source))
        target = confined(stage, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if digest(target) != expected['sha256'] or digest(source) != expected['sha256']:
            raise ValueError('Input or copied bytes changed: ' + str(source))

    with ThreadPoolExecutor(max_workers=max(1, min(workers, 32))) as pool:
        list(pool.map(copy, planned.items()))
    annotations = roots['viewer'] / 'annotations'
    annotation_hashes = inventory(annotations) if annotations.exists() else {}
    if annotation_hashes != binding['annotations']:
        raise ValueError('Current annotations changed; bind the current review history again')
    if annotations.exists():
        shutil.copytree(annotations, stage / 'viewer/annotations')
        if inventory(stage / 'viewer/annotations') != annotation_hashes:
            raise ValueError('Annotation migration differs')
    shutil.copy2(ASSET, stage / 'launch_portable_review.py')
    (stage / 'evidence').mkdir(exist_ok=True)
    shutil.copy2(binding_path, stage / 'evidence/package-binding.json')
    scripts = {
        'start.cmd': '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n"%~dp0runtime\\python.exe" -I -X utf8 -B -u "%~dp0launch_portable_review.py" --open %*\r\nset "launch_exit=%errorlevel%"\r\nif "%launch_exit%"=="0" exit /b 0\r\nif "%~1"=="--check-only" exit /b %launch_exit%\r\necho See startup-logs for diagnostics.\r\npause\r\nexit /b %launch_exit%\r\n',
        'diagnose.cmd': '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n"%~dp0runtime\\python.exe" -I -X utf8 -B -u "%~dp0launch_portable_review.py" --check-only %*\r\nexit /b %errorlevel%\r\n',
    }
    for name, text in scripts.items():
        (stage / name).write_bytes(text.encode('ascii'))
    (stage / '使用说明.txt').write_text(binding['readme'], encoding='utf-8-sig')
    files = inventory(stage, ('viewer/annotations',))
    manifest = dict(schema='published_current_review_payload_v1', files=files,
                    preferred_port=binding['preferred_port'], scope='published_results_review_only',
                    binding_sha256=binding_sha256, annotation_snapshot=annotation_hashes,
                    mutable_directories=list(portable.MUTABLE), raw_CAD_reconstruction_performed=False,
                    external_historical_evidence_references_rewritten=False, human_accepted=False)
    dump(stage / 'payload-manifest.json', manifest)
    portable.verify_payload(stage, workers)
    # Publication is a rename only after byte checks. Failures retain the
    # unmistakable .building directory instead of a plausible final package.
    stage.rename(output)
    archive_temp = archive.with_name(archive.name + '.building')
    with zipfile.ZipFile(archive_temp, 'x', zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                z.write(path, (Path(output.name) / path.relative_to(output)).as_posix())
    with zipfile.ZipFile(archive_temp) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP integrity failed')
        for name, record in manifest['files'].items():
            if hashlib.sha256(z.read(output.name + '/' + name)).hexdigest() != record['sha256']:
                raise ValueError('ZIP payload mismatch: ' + name)
    archive_temp.rename(archive)
    return dict(status='published_review_package_created', directory=str(output),
                archive=dict(path=str(archive), sha256=digest(archive), bytes=archive.stat().st_size),
                payload_files=len(files), annotations_preserved=len(annotation_hashes),
                raw_CAD_reconstruction_performed=False, human_accepted=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binding', type=Path, required=True)
    p.add_argument('--binding-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    print(json.dumps(package(a.binding, a.binding_sha256, a.output, a.workers), ensure_ascii=False))


if __name__ == '__main__':
    main()
