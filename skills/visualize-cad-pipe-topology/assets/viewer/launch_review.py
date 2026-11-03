"""Standard-library launch diagnostics and single-drawing local review entry."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent


def confined(root, path):
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('Task path leaves the extracted package')
    return result


def targets(root):
    if (root / 'batch.json').is_file():
        rows = []
        for item in json.loads((root / 'batch.json').read_text(encoding='utf-8-sig'))['tasks']:
            task = confined(root, item['path'])
            td = task.parent
            if (td / 'viewer/serve.py').is_file():
                rows.append({'sheet': item['sheet'], 'task_id': item['task_id'], 'directory': td / 'viewer'})
        return rows
    if (root / 'serve.py').is_file():
        return [{'sheet': 'single', 'task_id': root.name, 'directory': root}]
    raise ValueError('No batch.json or serve.py. Extract the entire ZIP before running start.cmd.')


def preflight(root, rows):
    result = {'time_utc': datetime.now(timezone.utc).isoformat(), 'python_version': platform.python_version(),
              'python_executable': sys.executable, 'architecture': platform.architecture()[0],
              'os': platform.platform(), 'package': str(root), 'errors': [], 'warnings': [], 'viewers': []}
    if sys.version_info < (3, 10):
        result['errors'].append('Python 3.10 or newer is required.')
    if sys.maxsize <= 2 ** 32:
        result['warnings'].append('32-bit Python detected; 64-bit is preferable for large drawings.')
    for row in rows:
        directory = row['directory']
        missing = [s for s in ['serve.py', 'hil_server.py', 'public/index.html', 'public/data/manifest.json',
                              'public/data/graph.json', 'public/data/cad.svg'] if not (directory / s).is_file()]
        if missing:
            result['errors'].append(row['sheet'] + ': missing extracted files: ' + ', '.join(missing))
            continue
        manifest = json.loads((directory / 'public/data/manifest.json').read_text(encoding='utf8'))
        if row['sheet'] != 'single' and manifest['projectId'] != row['task_id']:
            result['errors'].append(row['sheet'] + ': viewer project identity mismatch')
        result['viewers'].append({'sheet': row['sheet'], 'project_id': manifest['projectId'],
                                  'cad_svg_mib': round((directory / 'public/data/cad.svg').stat().st_size / 1048576, 2)})
    result['status'] = 'FAIL' if result['errors'] else 'PASS'
    return result


def run_child(cmd, log):
    print('Keep this window open while reviewing. Closing it stops this launch.', flush=True)
    child = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding='utf8', errors='replace')
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
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
        child.stdout.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sheet', help='Drawing sheet ID, e.g. 04')
    parser.add_argument('--all', action='store_true', help='Start every drawing service')
    parser.add_argument('--check-only', action='store_true', help='Write diagnostics without launching services')
    args = parser.parse_args(argv)
    if args.sheet and args.all:
        parser.error('Choose --sheet or --all')
    logdir = ROOT / 'startup-logs'
    logdir.mkdir(exist_ok=True)
    with (logdir / 'startup.log').open('a', encoding='utf8') as log:
        try:
            rows = targets(ROOT)
            if not rows:
                raise ValueError('No extracted drawing viewers found')
            diagnostic = preflight(ROOT, rows)
            (logdir / 'diagnostics.json').write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding='utf8')
            log.write(json.dumps(diagnostic, ensure_ascii=False) + '\n')
            print('Diagnostics: ' + str(logdir / 'diagnostics.json'))
            if diagnostic['errors']:
                raise ValueError('; '.join(diagnostic['errors']))
            for warning in diagnostic['warnings']:
                print(warning)
            if args.check_only:
                print('PASS: runtime and extracted viewer files are available. No service started.')
                return 0
            if not args.sheet and not args.all and (ROOT / 'batch.json').exists():
                print('\nChoose one drawing for review (lower memory). Type ALL for the full dashboard.')
                for row in rows:
                    print(row['sheet'] + ': ' + row['task_id'])
                answer = input('Sheet ID [04]: ').strip() or '04'
                if answer.upper() == 'ALL':
                    args.all = True
                else:
                    args.sheet = answer
            if args.all:
                if not (ROOT / 'serve_tasks.py').is_file():
                    raise ValueError('The batch dashboard is missing')
                cmd = [sys.executable, '-X', 'utf8', '-u', str(ROOT / 'serve_tasks.py'), '--open']
            else:
                row = next((r for r in rows if not args.sheet or r['sheet'] == args.sheet.zfill(2)), None)
                if row is None:
                    raise ValueError('Unknown drawing sheet. Choose one of: ' + ', '.join(r['sheet'] for r in rows))
                cmd = [sys.executable, '-X', 'utf8', '-u', str(row['directory'] / 'serve.py'), '--open']
            log.write('Command: ' + repr(cmd) + '\n');log.flush()
            return run_child(cmd, log)
        except (OSError, ValueError, KeyError, json.JSONDecodeError, EOFError) as error:
            log.write(traceback.format_exc());log.flush()
            print('STARTUP FAILED: ' + str(error))
            print('Send startup-logs/startup.log and diagnostics.json for diagnosis.')
            return 1


if __name__ == '__main__':
    raise SystemExit(main())
