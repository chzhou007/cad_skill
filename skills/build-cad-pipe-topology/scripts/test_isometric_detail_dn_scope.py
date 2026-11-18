import unittest,ezdxf
from types import SimpleNamespace
from unittest.mock import patch
from isometric_detail_dn_scope import classify


class DetailScopeTest(unittest.TestCase):
 def fixture(self):
  d=ezdxf.new();m=d.modelspace();t=m.add_text('示意图',dxfattribs={'layer':'DIM_SYMB','insert':(0,0)});dn=m.add_text('DN80',dxfattribs={'layer':'空调编号','insert':(10,20)});screen={'source_sha256':'S','graph_sha256':'G','status':'native_dn_bulk_screen_candidates_only','graph_mutated':False,'hil_ready':False,'records':[{'text_handle':dn.dxf.handle,'text':'DN80','layer':'空调编号','position':[10,20],'status':'no_source_line_in_local_scope'}]};p={'source_sha256':'S','graph_sha256':'G','bulk_screen_sha256':'B','title':{'handle':t.dxf.handle,'text':'示意图','layer':'DIM_SYMB'},'text_handles':[dn.dxf.handle]};return d,screen,p
 def test_scope_is_not_mapping_or_diameter(self):
  d,s,p=self.fixture()
  with patch('isometric_detail_dn_scope.geometry.equipment_labels',return_value=[]),patch('isometric_detail_dn_scope.geometry.infer_drawing_layout',return_value='L'),patch('isometric_detail_dn_scope.geometry.is_excluded_detail_point',return_value=True),patch('isometric_detail_dn_scope.dataclasses.asdict',return_value={}):
   r=classify(d,s,p,'S','G','B');self.assertFalse(r['detail_mapping_ready']);self.assertFalse(r['hil_ready']);self.assertNotIn('nominal_mm',r['records'][0])
 def test_wrong_scope_or_source_fails_closed(self):
  d,s,p=self.fixture()
  with patch('isometric_detail_dn_scope.geometry.equipment_labels',return_value=[]),patch('isometric_detail_dn_scope.geometry.infer_drawing_layout',return_value='L'),patch('isometric_detail_dn_scope.geometry.is_excluded_detail_point',return_value=False):
   with self.assertRaisesRegex(ValueError,'not in excluded'):classify(d,s,p,'S','G','B')
  p['title']['text']='other'
  with patch('isometric_detail_dn_scope.geometry.equipment_labels',return_value=[]),patch('isometric_detail_dn_scope.geometry.infer_drawing_layout',return_value='L'):
   with self.assertRaisesRegex(ValueError,'title'):classify(d,s,p,'S','G','B')
 def test_right_detail_requires_right_scope_and_is_separate(self):
  d,s,p=self.fixture();p['scopes']=[{'scope_id':'right-unit','side':'right','title':p['title'],'text_handles':p['text_handles']}]
  with patch('isometric_detail_dn_scope.geometry.equipment_labels',return_value=[]),patch('isometric_detail_dn_scope.geometry.infer_drawing_layout',return_value=SimpleNamespace(right_detail_x_min=0,right_detail_y_max=30)),patch('isometric_detail_dn_scope.dataclasses.asdict',return_value={}):
   r=classify(d,s,p,'S','G','B');self.assertEqual(r['records'][0]['scope_id'],'right-unit');self.assertEqual(r['records'][0]['status'],'excluded_right_scope_detail_correspondence_pending')

if __name__=='__main__':unittest.main()
