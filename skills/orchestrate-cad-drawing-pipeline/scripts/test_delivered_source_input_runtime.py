"""Check source fidelity and failure barriers before running the CAD owners."""
from pathlib import Path
import hashlib
import json
import os
import tempfile
import unittest
import errno
import shutil
import sys
from unittest.mock import patch
from delivered_source_input_runtime import Runtime,MissingDeliveredInput,NATIVE_STAT
import delivered_source_input_runtime as runtime_module


class SealedSourceInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.package=self.root/'package';self.package.mkdir()
        self.work=self.root/'work';self.work.mkdir()
        self.host=self.root/'historical-source.txt';self.host.write_text('host changed',encoding='utf8')
        self.delivered=self.package/'data/original.txt';self.delivered.parent.mkdir();self.delivered.write_text('已交付原始数据',encoding='utf8')
        self.digest=hashlib.sha256(self.delivered.read_bytes()).hexdigest()
        self.index=dict(files={os.path.normcase(str(self.host)):dict(relative='data/original.txt',sha256=self.digest)},
            directories={os.path.normcase(str(self.root/'logical-dir')):'data'},negative=[os.path.normcase(str(self.root/'absent.txt'))],
            forbidden_historical_final_graph_hashes=[],adapter_sha256=hashlib.sha256(Path(runtime_module.__file__).read_bytes()).hexdigest())
    def runtime(self):
        p=self.package/'logical-input-index.json';p.write_text(json.dumps(self.index,ensure_ascii=False),encoding='utf8')
        return Runtime(self.package,self.work,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_existing_host_source_is_replaced_by_delivered_bytes_without_modifying_it(self):
        runtime=self.runtime()
        with runtime.open(self.host,encoding='utf8')as f:self.assertEqual(f.read(),'已交付原始数据')
        self.assertEqual(self.host.read_text('utf8'),'host changed')
        self.assertEqual(len(runtime.events),1)

    def test_unlisted_existing_input_never_falls_back_to_host(self):
        runtime=self.runtime();p=self.root/'unlisted.txt';p.write_text('must not leak into replay')
        with self.assertRaises(MissingDeliveredInput):runtime.open(p)
        self.assertEqual(runtime.misses[0]['path'],os.path.normcase(str(p)))

    def test_recorded_missing_input_preserves_native_enoent_contract(self):
        runtime=self.runtime()
        with self.assertRaises(FileNotFoundError)as error:runtime.stat(self.root/'absent.txt')
        self.assertEqual(error.exception.errno,errno.ENOENT)
        self.assertEqual(runtime.misses,[])

    def test_logical_directory_does_not_expose_unrelated_physical_aliases(self):
        runtime=self.runtime()
        self.assertEqual(runtime.listdir(self.root/'logical-dir'),[])
        self.assertEqual(list(runtime.scandir(self.root/'logical-dir')),[])

    def test_actual_delivered_stat_is_returned_and_old_identity_is_not_faked(self):
        runtime=self.runtime();actual=runtime.stat(self.host)
        self.assertEqual(actual.st_ino,NATIVE_STAT(self.delivered).st_ino)
        self.assertNotEqual(actual.st_ino,NATIVE_STAT(self.host).st_ino)
        self.assertEqual(runtime.realpath(self.host),str(self.host))

    def test_same_size_timestamp_tamper_still_fails(self):
        runtime=self.runtime();old=self.delivered.stat();data=self.delivered.read_bytes()
        self.delivered.write_bytes(bytes([data[0]^1])+data[1:]);os.utime(self.delivered,ns=(old.st_atime_ns,old.st_mtime_ns))
        with self.assertRaisesRegex(ValueError,'bytes changed'):runtime.open(self.host)

    def test_old_final_graph_hash_cannot_be_read_as_production_input(self):
        self.index['forbidden_historical_final_graph_hashes']=[self.digest]
        runtime=self.runtime()
        with self.assertRaisesRegex(ValueError,'Historical final graph'):runtime.open(self.host)
        with self.assertRaisesRegex(ValueError,'Historical final graph'):runtime.open(self.delivered)

    def test_source_writes_blocked_and_new_output_writes_allowed(self):
        runtime=self.runtime()
        with self.assertRaises(PermissionError):runtime.open(self.host,'w')
        with runtime.open(self.work/'new.txt','w')as f:f.write('ok')
        self.assertEqual((self.work/'new.txt').read_text(),'ok')

    def test_platform_null_device_supports_native_subprocess_redirection(self):
        runtime=self.runtime();fd=runtime.os_open(os.devnull,os.O_RDWR)
        try:self.assertEqual(os.write(fd,b'discarded'),9)
        finally:os.close(fd)
        self.assertEqual(runtime.misses,[])

    def test_native_temporary_verifier_cleanup_uses_complete_directory_entry_api(self):
        runtime=self.runtime();folder=self.work/'native-verifier';(folder/'nested').mkdir(parents=True)
        (folder/'nested/result.txt').write_text('fresh verification output')
        with patch('os.scandir',runtime.scandir):shutil.rmtree(folder)
        self.assertFalse(folder.exists())
        self.assertTrue(self.delivered.exists())

    def test_only_own_multiprocessing_pipe_stat_is_an_IPC_resource(self):
        runtime=self.runtime();name='\\\\.\\pipe\\pyc-'+str(os.getpid())+'-0-abc_123'
        self.assertEqual(runtime.translate(name,'stat'),name)
        self.assertEqual(len(runtime.runtime_probes),1)
        with self.assertRaises(MissingDeliveredInput):runtime.translate(name,'open')
        with self.assertRaises(MissingDeliveredInput):runtime.translate('\\\\.\\pipe\\pyc-'+str(os.getpid()+1)+'-0-abc_123','stat')

    def test_multiprocessing_spawn_preserves_same_checked_runtime(self):
        import multiprocessing.spawn as spawn
        runtime=self.runtime()
        with patch.object(spawn,'get_command_line',spawn.get_command_line):
            runtime.install_multiprocessing()
            command=spawn.get_command_line(pipe_handle=123,parent_pid=os.getpid())
            self.assertEqual(command[:5],[sys.executable,'-I','-X','utf8','-B'])
            self.assertEqual(command[5:9],[str(runtime.adapter_path),str(runtime.package),str(runtime.work),runtime.index_sha256])
            self.assertEqual(command[9],'--multiprocessing-spawn-child')
            self.assertEqual(json.loads(bytes.fromhex(command[10]).decode('utf8'))['spawn_token'],runtime.spawn_requests[0]['spawn_token'])

    def test_scandir_keeps_logical_paths_and_real_file_types(self):
        self.index['files'][os.path.normcase(str(self.root/'logical-dir/original.txt'))]=dict(relative='data/original.txt',sha256=self.digest)
        runtime=self.runtime()
        with runtime.scandir(self.root/'logical-dir')as stream:entries=list(stream)
        self.assertEqual(entries[0].name,'original.txt')
        self.assertEqual(entries[0].path,str(self.root/'logical-dir/original.txt'))
        self.assertTrue(entries[0].is_file())

    def test_changed_index_or_path_escape_cannot_select_new_inputs(self):
        p=self.package/'logical-input-index.json';p.write_text('{}')
        with self.assertRaisesRegex(ValueError,'index changed'):Runtime(self.package,self.work,'0'*64)
        self.index['files'][os.path.normcase(str(self.host))]['relative']='../historical-source.txt'
        with self.assertRaisesRegex(ValueError,'escaped'):self.runtime()


if __name__=='__main__':unittest.main()
