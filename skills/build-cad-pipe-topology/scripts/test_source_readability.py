import tempfile,unittest
from pathlib import Path
import ezdxf
from source_readability import read_source

class Readability(unittest.TestCase):
 def test_modern_utf8_overrides_retained_legacy_header(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td)/'source.dxf';d=ezdxf.new('R2018');d.modelspace().add_text('三层空调水管：管径DN250');d.saveas(p)
   p.write_bytes(p.read_bytes().replace(b'ANSI_1252',b'ANSI_936'))
   doc,audit=read_source(p)
   self.assertEqual(next(iter(doc.modelspace())).plain_text(),'三层空调水管：管径DN250')
   self.assertEqual(audit['actual_read_codec'],'utf-8');self.assertEqual(audit['native_chinese_entity_count'],1)
 def test_replacement_character_stops_before_geometry(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td)/'source.dxf';d=ezdxf.new('R2018');d.modelspace().add_text('中文\ufffd');d.saveas(p)
   with self.assertRaisesRegex(ValueError,'stop before geometry'):read_source(p)
 def test_invalid_utf8_stops_even_outside_modelspace(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td)/'source.dxf';d=ezdxf.new('R2018');d.blocks.new('NATIVE').add_text('中文');d.saveas(p)
   p.write_bytes(p.read_bytes().replace('中文'.encode('utf8'),b'\xff\xfe'))
   with self.assertRaises(UnicodeError):read_source(p)
if __name__=='__main__':unittest.main()
