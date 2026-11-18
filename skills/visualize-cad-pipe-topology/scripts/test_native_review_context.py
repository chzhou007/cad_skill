import tempfile
import unittest
from pathlib import Path
import ezdxf
from native_review_context import record_source, expanded_window, render_context


class NativeReviewContextTests(unittest.TestCase):
    def test_native_colours_chinese_and_matching_crop_without_source_edit(self):
        doc=ezdxf.new();m=doc.modelspace()
        a=m.add_line((-1000,0),(1000,0),dxfattribs={'color':6})
        b=m.add_line((0,-1000),(0,1000),dxfattribs={'color':4})
        text=m.add_text('空调井与主管',dxfattribs={'height':200,'insert':(-800,500),'color':3})
        boxes=[{'label':'A','bbox':[-500,500,-300,300]}]
        crop=expanded_window(boxes,min_width=4000,min_height=2500)
        before=[(x.dxf.handle,x.dxftype(),x.dxf.get('layer')) for x in m]
        recorder=record_source(doc)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'context'
            proof=render_context(recorder,crop,boxes,root,'原 CAD：问题位置')
            svg=root.with_suffix('.svg').read_text(encoding='utf8')
            self.assertTrue(root.with_suffix('.png').stat().st_size>1000)
            self.assertIn('#ff00ff',svg)
            self.assertIn('#00ffff',svg)
            self.assertIn('#ff643b',svg)
            self.assertEqual(proof['window_wcs'],crop)
            self.assertFalse(proof['physical_or_topology_changes'])
        self.assertEqual(text.dxf.text,'空调井与主管')
        self.assertEqual(before,[(x.dxf.handle,x.dxftype(),x.dxf.get('layer')) for x in m])
        self.assertEqual(tuple(a.dxf.start),(-1000,0,0))

    def test_locator_outside_context_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'outside context'):
                render_context(None,[0,10,0,10],[{'label':'X','bbox':[-1,1,2,3]}],Path(folder)/'bad','bad')


if __name__=='__main__':unittest.main()
