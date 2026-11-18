import hashlib,json,tempfile,unittest
from pathlib import Path
from reconstruct_plan_member_contact_context import validate_manifest,MODE

class Tests(unittest.TestCase):
    def fixture(self,folder):
        roles=['provider','member_bridges','member_interfaces','plan_source','plan_graph','plan_inventory','axis_source','axis_graph','axis_inventory','current_T_source_config','junction_transition','template_origin','orientation_policy'];inputs={}
        for name in roles:
            p=Path(folder)/(name+'.dxf'if name.endswith('source')else name+'.json');p.write_text('{}',encoding='utf8');inputs[name]=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        return dict(schema=MODE,view_role='floor_plan_orthographic_XY',floor=2,inputs=inputs)
    def test_fixed_roles_accept_then_reject_changed_source(self):
        with tempfile.TemporaryDirectory()as folder:
            m=self.fixture(folder);self.assertEqual(validate_manifest(m),m['inputs']);Path(m['inputs']['plan_source']['path']).write_text('changed')
            with self.assertRaises(ValueError):validate_manifest(m)
    def test_axis_view_T3_or_incomplete_context_not_accepted(self):
        for kind in ['view','T3','missing','extra']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory()as folder:
                m=self.fixture(folder)
                if kind=='view':m['view_role']='axis'
                elif kind=='T3':p=Path(folder)/'source_T3.dxf';p.write_text('{}');m['inputs']['plan_source']['path']=str(p)
                elif kind=='missing':m['inputs'].pop('junction_transition')
                else:m['inputs']['unproved_auto_Z_tolerance']=m['inputs']['provider']
                with self.assertRaises(ValueError):validate_manifest(m)

if __name__=='__main__':unittest.main()
