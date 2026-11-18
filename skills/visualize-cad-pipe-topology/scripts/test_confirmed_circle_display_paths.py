import copy,unittest
import ezdxf
from coverage_display_paths import partition

def fixture(paired=False):
    doc=ezdxf.new();m=doc.modelspace();center=[0,-1] if paired else [0,0];rim=[0,99] if paired else [0,100]
    circle=m.add_circle(center,100,dxfattribs={'layer':'空调冷冻水回水'})
    line=m.add_line(rim,(0,300),dxfattribs={'layer':'空调冷冻水供水'})
    main=m.add_line((-200,0),(200,0),dxfattribs={'layer':'空调冷冻水供水'})
    edge=dict(system='supply',attribute_paths=[[[0,300],rim]],path_points=[[0,300],rim,[0,0]],path_length=300-rim[1],path_length_complete=False,physical_length='unknown',source_handles=[line.dxf.handle])
    proof=dict(circle_handle=circle.dxf.handle,source_rim=rim,physical_length='unknown')
    if paired:
        proof.update(source_sha256='S',confirmation_basis='explicit_equipment_pair_reply',source_circle_center=center,point=[0,0],system='supply',maximum_circle_main_offset_drawing_units=1.01,main_handle=main.dxf.handle)
        edge['source_confirmed_equipment_pair_circle']=proof
    else:
        proof.update(center=center,line_system='supply',confirmation=dict(confirmed_by='user',question='连接？',answer='是'))
        edge['source_user_circle_connection']=proof
    return doc,edge

class ConfirmedCircleDisplayTests(unittest.TestCase):
    def test_exact_and_offset_connectors_are_dotted_not_measured(self):
        for paired in (False,True):
            doc,e=fixture(paired);before=copy.deepcopy(e);known,unknown=partition(e,doc,'S')
            self.assertEqual(known,e['attribute_paths']);self.assertEqual(unknown,[[e['attribute_paths'][0][-1],[0,0]]])
            self.assertEqual(e,before)
    def test_later_circle_repair_must_not_hide_an_earlier_crossover_gap(self):
        doc,e=fixture();m=doc.modelspace();a=m.add_line((0,300),(0,250),dxfattribs={'layer':'空调冷冻水供水'});b=m.add_line((0,200),(0,100),dxfattribs={'layer':'空调冷冻水供水'})
        e.update(attribute_paths=[[[0,300],[0,250]],[[0,200],[0,100]]],path_length=150,source_handles=[a.dxf.handle,b.dxf.handle],path_length_scope='source_drawn_pipe_only_user_confirmed_circle_and_equipment_length_unknown',source_normalized_crossovers=[dict(a=[0,250],b=[0,200],crossing_connectivity='independent_pipes_no_junction',physical_length='unknown')])
        known,unknown=partition(e,doc,'S')
        self.assertEqual(known,e['attribute_paths']);self.assertEqual(unknown,[[[0,250],[0,200]],[[0,100],[0,0]]])
    def test_native_source_and_current_endpoint_are_required(self):
        doc,e=fixture(True)
        with self.assertRaises(ValueError):partition(e)
        with self.assertRaises(ValueError):partition(e,doc,'OTHER')
        e['path_points'][-1]=[10,0]
        with self.assertRaises(ValueError):partition(e,doc,'S')
    def test_wrong_branch_service_and_false_measured_length_reject(self):
        for kind in ('service','length'):
            doc,e=fixture()
            if kind=='service':doc.entitydb[e['source_handles'][0]].dxf.layer='空调冷冻水回水'
            else:e['path_length']+=100
            with self.assertRaises(ValueError):partition(e,doc,'S')
    def test_plain_circle_never_creates_a_display_connection(self):
        doc,e=fixture();e.pop('source_user_circle_connection')
        self.assertEqual(partition(e,doc,'S'),(e['attribute_paths'],[]))

if __name__=='__main__':unittest.main()
