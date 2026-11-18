import copy,unittest
from two_arm_affected_junctions import same_roles
class Tests(unittest.TestCase):
    def fixture(self):return dict(junctions=[dict(node_id='T',system='return',position=[0,0],source_rays=[dict(edge_id=e,source_line_handle=h,direction=v)for e,h,v in[('OLD','L1',[1,0]),('B','L2',[0,1]),('C','L3',[0,-1])]])])
    def test_explicit_merge_alias_preserves_existing_three_native_rays(self):
        old=self.fixture();new=copy.deepcopy(old);new['junctions'][0]['source_rays'][0]['edge_id']='MERGED';new['junctions'][0]['source_rays'][0]['direction']=[1000,0];self.assertEqual(same_roles(old,new,{'OLD':'MERGED'})['physical_Ts_added'],0)
    def test_a_changed_source_system_direction_or_fourth_arm_cannot_inherit_old_T(self):
        old=self.fixture()
        for kind in('system','LINE','direction','fourth_arm'):
            new=copy.deepcopy(old);j=new['junctions'][0]
            if kind=='system':j['system']='supply'
            elif kind=='LINE':j['source_rays'][0]['source_line_handle']='OTHER'
            elif kind=='direction':j['source_rays'][0]['direction']=[-1,0]
            else:j['source_rays'].append(dict(j['source_rays'][0],edge_id='FOURTH'))
            with self.subTest(kind=kind),self.assertRaises(ValueError):same_roles(old,new,{})
if __name__=='__main__':unittest.main()
