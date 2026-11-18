import copy, unittest
from reapply_reviewed_ring_crossview_DN import select_scopes


class Tests(unittest.TestCase):
    def fixture(self):
        rows=[];edges=[]
        for eid,floor in [('F1',1),('F2',2),('F3',3)]:
            edges.append(dict(edge_id=eid,system='supply',floor_start=floor,floor_end=floor))
            rows.append(dict(edge_id=eid,classification='horizontal_only',correspondence_observations=[dict(
                mapping_id='M'+eid,plan_edges=['E0054'],grouped_axis_edges=[eid])]))
        return dict(records=rows),dict(edges=edges),{'E0054':dict(system='supply')}

    def test_repeated_local_plan_IDs_do_not_cross_drawing_namespaces(self):
        provider,axis,source=self.fixture();before=copy.deepcopy((provider,axis,source))
        selected,excluded=select_scopes(provider,axis,source,2)
        self.assertEqual([r['axis_edge_id']for r in selected],['F2'])
        self.assertEqual({r['axis_edge_id']for r in excluded},{'F1','F3'})
        self.assertEqual((provider,axis,source),before)

    def test_wrong_system_group_scope_or_competing_writer_is_not_adopted(self):
        for kind in ('system','group','competing'):
            provider,axis,source=self.fixture()
            if kind=='system':source['E0054']['system']='return'
            elif kind=='group':provider['records'][1]['correspondence_observations'][0]['grouped_axis_edges']=['F2','OTHER']
            else:provider['records'][1]['correspondence_observations']*=2
            with self.subTest(kind=kind),self.assertRaises(ValueError):select_scopes(provider,axis,source,2)


if __name__=='__main__':unittest.main()
