import copy,gc,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import ezdxf
from source_readability import read_source
from native_source_snapshot_runtime import source_snapshot_runtime,native_allocation_window

class Tests(unittest.TestCase):
    def test_native_allocation_window_restores_collector_state_and_thresholds(self):
        prior=gc.isenabled();thresholds=gc.get_threshold()
        try:
            gc.enable()
            with self.assertRaisesRegex(ValueError,'native failure'):
                with native_allocation_window():
                    self.assertFalse(gc.isenabled());raise ValueError('native failure')
            self.assertTrue(gc.isenabled());self.assertEqual(gc.get_threshold(),thresholds)
            gc.disable()
            with native_allocation_window():self.assertFalse(gc.isenabled())
            self.assertFalse(gc.isenabled())
            gc.enable()
            with patch.dict(os.environ,{'CAD_NATIVE_ALLOCATION_GC':'0'}):
                with native_allocation_window():self.assertTrue(gc.isenabled())
            self.assertTrue(gc.isenabled())
        finally:
            if prior:gc.enable()
            else:gc.disable()

    def test_native_allocation_restores_gc_after_parse_and_clone_errors(self):
        import native_source_snapshot_runtime as runtime
        with tempfile.TemporaryDirectory()as folder:
            p,_=self.source(folder);prior=gc.isenabled()
            try:
                gc.enable()
                with source_snapshot_runtime():
                    read_source(p)
                    with patch.object(runtime.pickle,'loads',side_effect=ValueError('clone failed')):
                        with self.assertRaisesRegex(ValueError,'clone failed'):read_source(p)
                    self.assertTrue(gc.isenabled())
                with patch.object(ezdxf,'readfile',side_effect=ValueError('parse failed')):
                    with source_snapshot_runtime():
                        with self.assertRaisesRegex(ValueError,'parse failed'):read_source(p)
                self.assertTrue(gc.isenabled())
            finally:
                if prior:gc.enable()
                else:gc.disable()

    def source(self,folder):
        p=Path(folder)/'中文原图.dxf';doc=ezdxf.new('R2013');m=doc.modelspace()
        line=m.add_line((0,0,7),(100,0,7),dxfattribs={'layer':'空调冷冻水供水'})
        m.add_text('三层 空调井 DN200');block=doc.blocks.new('嵌套设备');block.add_line((0,0),(1,1));m.add_blockref('嵌套设备',(10,20))
        doc.saveas(p);return p,line.dxf.handle

    def test_fresh_mutable_copies_strict_Chinese_and_nested_references(self):
        with tempfile.TemporaryDirectory()as folder:
            p,h=self.source(folder);control,proof=read_source(p)
            with source_snapshot_runtime()as stats:
                first,a=read_source(p);first.entitydb[h].dxf.start=(999,999,999);first.modelspace().add_text('消费方修改')
                second,b=read_source(p);third,c=read_source(p)
                self.assertEqual(a,proof);self.assertEqual(b,proof);self.assertEqual(c,proof)
                self.assertEqual(tuple(second.entitydb[h].dxf.start),tuple(control.entitydb[h].dxf.start))
                self.assertIs(second.entitydb[h].doc,second);self.assertIsNot(second.entitydb[h],third.entitydb[h])
                self.assertEqual([e.dxf.handle for e in second.modelspace()],[e.dxf.handle for e in control.modelspace()])
                self.assertEqual(len(list(second.blocks['嵌套设备'])),1)
                second.entitydb[h].dxf.start=(88,88,88)
                self.assertNotEqual(tuple(second.entitydb[h].dxf.start),tuple(third.entitydb[h].dxf.start))
                self.assertEqual(stats['original_parses'],1);self.assertEqual(stats['fresh_snapshot_clones'],2)

    def test_changed_source_bytes_reparse_and_still_reject_bad_Chinese(self):
        with tempfile.TemporaryDirectory()as folder:
            p,_=self.source(folder)
            with source_snapshot_runtime()as stats:
                _,a=read_source(p)
                doc=ezdxf.readfile(p);doc.modelspace().add_text('新增中文');doc.saveas(p)
                _,b=read_source(p)
                self.assertNotEqual(a['source_sha256'],b['source_sha256']);self.assertEqual(stats['invalidations'],1)
                doc=ezdxf.readfile(p);doc.modelspace().add_text('损坏\ufffd');doc.saveas(p)
                with self.assertRaisesRegex(ValueError,'Unreadable source text'):read_source(p)
                with self.assertRaisesRegex(ValueError,'Unreadable source text'):read_source(p)

    def test_disabled_direct_calls_memory_limit_and_exception_restore(self):
        with tempfile.TemporaryDirectory()as folder:
            p,_=self.source(folder);original=ezdxf.readfile
            with patch.dict(os.environ,{'CAD_NATIVE_SOURCE_SNAPSHOTS':'0'}):
                with source_snapshot_runtime()as stats:
                    read_source(p);read_source(p);self.assertEqual(stats['original_parses'],0)
            with source_snapshot_runtime(max_bytes=1)as stats:
                read_source(p);read_source(p);ezdxf.readfile(p)
                self.assertEqual(stats['original_parses'],2);self.assertEqual(stats['fresh_snapshot_clones'],0)
                self.assertEqual(stats['unsupported_fallbacks'],1)
            with self.assertRaises(RuntimeError):
                with source_snapshot_runtime():raise RuntimeError('stop')
            self.assertIs(ezdxf.readfile,original)

if __name__=='__main__':unittest.main()
