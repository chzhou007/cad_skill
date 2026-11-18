import unittest
from source_compound_dn_evidence import parse,extract

class CompoundDNTest(unittest.TestCase):
 def test_order_and_suffix_are_preserved(self):
  self.assertEqual(parse(' DN300(3.600) / DN200(3.000) '),[{'order_in_text':1,'nominal_mm':300.,'parenthesized_source_value':'3.600'},{'order_in_text':2,'nominal_mm':200.,'parenthesized_source_value':'3.000'}])
  self.assertEqual(parse('dn65/DN80')[1]['nominal_mm'],80.)
 def test_other_expressions_are_not_guessed(self):
  for text in ('DN0/DN20','DN50','DN50/DN60/DN70','CHWS DN50/DN60','DN50(楼层)/DN60','DN50/DN-10'):
   with self.subTest(text=text):self.assertIsNone(parse(text))
 def test_duplicates_and_rotation_are_preserved_without_binding(self):
  texts=[{'id':h,'handle':h,'layer':'空调平面','text':'DN300(3.6)/DN200(3.0)','position':[0,0],'height':10,'rotation':r} for h,r in [('A',0),('B',90)]]
  out=extract(texts,[],{'空调平面'});self.assertEqual(len(out['records']),2);self.assertEqual(out['records'][1]['source_text']['rotation'],90);self.assertFalse(out['records'][0]['edge_binding_confirmed']);self.assertFalse(out['human_accepted'])
if __name__=='__main__':unittest.main()
