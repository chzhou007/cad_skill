import copy,unittest
from source_dn_annotation_risks import scan

def t(id,text,x,y,layer='空调平面'):
 return {'id':id,'handle':id,'text':text,'position':[x,y],'height':5,'rotation':0,'layer':layer}
def edge(id,y):return {'edge_id':id,'attribute_paths':[[[0,y],[100,y]]]}
class DNAnnotationRiskTest(unittest.TestCase):
 def test_mixed_source_syntax_flags_edge_without_mutation(self):
  texts=[t('a','DN300(3.200)',10,2),t('b','DN300(3.200)/DN200(2.600)',60,2)];edges=[edge('E1',0)];before=copy.deepcopy((texts,edges));result=scan(texts,edges,{'空调平面'})
  self.assertEqual((texts,edges),before);self.assertEqual(result['mixed_syntax_edges'][0]['edge_id'],'E1');self.assertFalse(result['hil_ready']);self.assertIsNone(result['observations'][1]['parsed_single_dn'])
 def test_proximity_does_not_assign_or_cross_layers(self):
  result=scan([t('a','DN300',10,2),t('b','DN300/DN200',60,100),t('c','CHWS1 DN450',50,2,'其他')],[edge('E1',0)],{'空调平面'})
  self.assertEqual(len(result['observations']),2);self.assertEqual(result['mixed_syntax_edges'],[]);self.assertEqual(result['status'],'screening_only')
 def test_ambiguous_candidates_and_bad_input(self):
  result=scan([t('a','DN300',10,2),t('b','CHWS1 DN450',40,2)],[edge('E1',0),edge('E2',4)],{'空调平面'})
  self.assertEqual({x['edge_id'] for x in result['mixed_syntax_edges']},{'E1','E2'})
  with self.assertRaises(ValueError):scan([t('a','DN300',0,0),t('a','DN200',1,0)],[],{'空调平面'})
  with self.assertRaises(ValueError):scan([],[],set())
if __name__=='__main__':unittest.main()
