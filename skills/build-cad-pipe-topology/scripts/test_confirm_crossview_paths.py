import copy,unittest
from confirm_crossview_paths import route,snapshot,reviewed_answer,DECISION

class ConfirmCrossviewPathTests(unittest.TestCase):
    def fixture(self):
        return dict(nodes=[dict(node_id='T',node_type='tee',floor=2,x=0,y=0),dict(node_id='J',node_type='tee',floor=2,x=0,y=500),dict(node_id='EQ',node_type='equipment',floor=2,x=300,y=500)],
            edges=[dict(edge_id='A',start_node_id='T',end_node_id='J',system='supply',path_points=[[0,0],[0,500]],attribute_paths=[[[0,0],[0,500]]]),
                dict(edge_id='B',start_node_id='J',end_node_id='EQ',system='supply',path_points=[[0,500],[300,500]],attribute_paths=[[[0,500],[300,500]]])])
    def test_one_to_many_paths_need_no_equal_edge_or_vertex_counts(self):
        iso=self.fixture();plan=copy.deepcopy(iso)
        plan['edges']=[dict(edge_id='P',start_node_id='T',end_node_id='EQ',system='supply',path_points=[[0,0],[300,500]],attribute_paths=[[[0,0],[300,500]]])]
        self.assertEqual(route(plan,['P'],'T','EQ','supply'),['T','EQ'])
        self.assertEqual(route(iso,['A','B'],'T','EQ','supply'),['T','J','EQ'])
    def test_vertical_drawing_stroke_does_not_make_same_floor_path_a_riser(self):
        g=self.fixture();before=copy.deepcopy(g)
        route(g,['A','B'],'T','EQ','supply');self.assertEqual(g,before)
        g['nodes'][1]['floor']=3
        with self.assertRaisesRegex(ValueError,'inter-floor'):route(g,['A','B'],'T','EQ','supply')
    def test_disconnected_order_cross_system_and_intermediate_equipment_fail(self):
        for kind in ('order','system','equipment','disconnected'):
            g=self.fixture();ids=['A','B']
            if kind=='order':ids.reverse()
            elif kind=='system':g['edges'][1]['system']='return'
            elif kind=='equipment':g['nodes'][1]['node_type']='equipment'
            else:g['edges'][1]['start_node_id']='T'
            with self.assertRaises(ValueError):route(g,ids,'T','EQ','supply')
    def test_local_edge_split_or_floor_change_invalidates_snapshot(self):
        g=self.fixture();old=snapshot(g,['A','B'])
        g['edges'][0]['end_node_id']='EQ'
        self.assertNotEqual(snapshot(g,['A','B']),old)
        g=self.fixture();g['nodes'][0]['floor']=3
        self.assertNotEqual(snapshot(g,['A','B']),old)
    def test_only_explicit_scoped_original_pair_reply_is_accepted(self):
        reply=dict(sections=[dict(title='EQ',image={'sha256':'PAIR'},questions=[dict(id='Q',text='路径对应？',answer={'decision':DECISION,'comment':'同楼层两路分别对应；竖管另验。'})])])
        self.assertEqual(reviewed_answer(reply,'PAIR','Q','EQ')['id'],'Q')
        for field in ('pair','scope','answer','comment'):
            value=copy.deepcopy(reply)
            if field=='pair':value['sections'][0]['image']['sha256']='OTHER'
            elif field=='scope':value['sections'][0]['title']='OTHER'
            elif field=='answer':value['sections'][0]['questions'][0]['answer']['decision']='不能对应'
            else:value['sections'][0]['questions'][0]['answer']['comment']=''
            with self.assertRaises(ValueError):reviewed_answer(value,'PAIR','Q','EQ')

if __name__=='__main__':unittest.main()
