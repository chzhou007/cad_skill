import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'assets/viewer/launch_review.py'
spec=importlib.util.spec_from_file_location('launch_review',SCRIPT)
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)

def fixture(root):
 (root/'public/data').mkdir(parents=True)
 for name in ['serve.py','hil_server.py','public/index.html','public/data/graph.json','public/data/cad.svg']:(root/name).write_text('fixture',encoding='utf8')
 (root/'public/data/manifest.json').write_text(json.dumps({'projectId':'DEMO'}),encoding='utf8')

class PortableLauncher(unittest.TestCase):
 def test_diagnostics_without_service_or_browser_launch(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);fixture(root)
   with patch.object(launcher,'ROOT',root),patch.object(launcher,'run_child')as run:
    self.assertEqual(launcher.main(['--check-only']),0);run.assert_not_called()
   self.assertEqual(json.loads((root/'startup-logs/diagnostics.json').read_text())['status'],'PASS')
 def test_missing_files_write_failure_and_do_not_launch(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);fixture(root);(root/'hil_server.py').unlink()
   with patch.object(launcher,'ROOT',root),patch.object(launcher,'run_child')as run:
    self.assertEqual(launcher.main(['--check-only']),1);run.assert_not_called()
   self.assertIn('hil_server.py',(root/'startup-logs/startup.log').read_text())
 def test_bad_json_error_is_retained(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);(root/'batch.json').write_text('broken')
   with patch.object(launcher,'ROOT',root):self.assertEqual(launcher.main(['--check-only']),1)
   self.assertIn('JSONDecodeError',(root/'startup-logs/startup.log').read_text())
 def test_single_sheet_starts_one_selected_service(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);tasks=[]
   for sheet in ['03','04']:
    td=root/sheet;td.mkdir()
    (td/'viewer').mkdir();fixture(td/'viewer');(td/'task.json').write_text('{}')
    tasks.append({'sheet':sheet,'task_id':'DEMO','path':sheet+'/task.json'})
   (root/'batch.json').write_text(json.dumps({'tasks':tasks}))
   with patch.object(launcher,'ROOT',root),patch.object(launcher,'run_child',return_value=0)as run:
    self.assertEqual(launcher.main(['--sheet','4']),0)
    self.assertEqual(run.call_count,1);self.assertIn(str(root/'04/viewer/serve.py'),run.call_args.args[0])
    self.assertNotIn('serve_tasks.py',' '.join(run.call_args.args[0]))
 def test_task_paths_cannot_escape_package(self):
  with tempfile.TemporaryDirectory()as temp:
   with self.assertRaises(ValueError):launcher.confined(Path(temp),'../outside/task.json')

if __name__=='__main__':unittest.main()
