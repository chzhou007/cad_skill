import unittest,ast,hashlib
from pathlib import Path
import ezdxf
from ezdxf import bbox
import pipe_geometry as pg
from profiled_single_tap_instruments import single_tap_measurements,INHERITED_RECOGNIZER_AST_SHA256
from rebuild_profiled_schematic import measurement_reader

class InheritedSingleTapTests(unittest.TestCase):
    def setUp(self):self.before=pg.TOL;pg.set_tolerance(.25)
    def tearDown(self):pg.set_tolerance(self.before)
    def instrument(self,main=True,header=True,wrong_letter=False):
            d=ezdxf.new();m=d.modelspace();b=d.blocks.new('BODY');b.add_lwpolyline([(-2,0),(2,0),(2,4),(-2,4)],close=True);b.add_text('X'if wrong_letter else'P',dxfattribs={'insert':(-1,1),'height':1})
            en=m.add_blockref('BODY',(0,0),dxfattribs={'layer':'I'});m.add_line((0,0),(0,-8),dxfattribs={'layer':'I'})
            if header:
                m.add_line((0,4),(0,8),dxfattribs={'layer':'I'});m.add_circle((0,11),3,dxfattribs={'layer':'I'});m.add_text('PIT-A1',dxfattribs={'layer':'I','insert':(-1.8,9.5),'height':1})
            s=[{'a':(-20,-8),'b':(20,-8),'system':'physical','source_system':'supply','source_layer':'MAIN','handle':'MAIN-1'}]if main else[]
            bb=bbox.extents([en]);symbols=[{'handle':en.dxf.handle,'block':'BODY','entity':en,'bounds':[bb.extmin.x,bb.extmin.y,bb.extmax.x,bb.extmax.y]}]
            cfg=[{'source_block':'BODY','body_text':'P','tag_regex':'PIT-[A-Za-z0-9]+','label':'Pressure Transmitter','maximum_leader_body_diagonals':4,'main_layers':['MAIN']}]
            return d,s,symbols,cfg

    def test_complete_native_main_body_and_head_is_measurement_only(self):
        d,segments,symbols,rules=self.instrument();groups,consumed=single_tap_measurements(d,segments,symbols,rules)
        self.assertEqual(len(groups),1);self.assertEqual(consumed,{symbols[0]['handle']});self.assertFalse(groups[0]['hydraulic_connection']);self.assertEqual(groups[0]['source_tag'],'PIT-A1')

    def test_missing_main_missing_head_or_wrong_body_class_remains_unassigned(self):
        for kwargs in [dict(main=False),dict(header=False),dict(wrong_letter=True)]:
            with self.subTest(kwargs=kwargs):self.assertEqual(single_tap_measurements(*self.instrument(**kwargs)),([],set()))

    def test_nearby_head_without_exact_native_leader_stays_unassigned(self):
        d,segments,symbols,rules=self.instrument()
        for e in list(d.modelspace().query('LINE')):
            if abs(e.dxf.start.y-4)<.001:d.modelspace().delete_entity(e)
        self.assertEqual(single_tap_measurements(d,segments,symbols,rules),([],set()))

    def test_unconfigured_profile_does_not_recognize_or_consume(self):
        d,segments,symbols,rules=self.instrument();self.assertEqual(single_tap_measurements(d,segments,symbols,[]),([],set()))

    def test_private_adapter_preserves_original_outputs_and_consumed_ownership(self):
        d,segments,symbols,rules=self.instrument();handle=symbols[0]['handle'];existing=dict(id='existing',hydraulic_connection=False);stats=[]
        def base(*args):return segments,[existing],{handle}
        reader=measurement_reader(base,stats);actual=reader(d,segments,symbols,dict(single_tap_rules=rules));self.assertIs(actual[0],segments);self.assertEqual(actual[1],[existing]);self.assertEqual(actual[2],{handle});self.assertEqual(stats[0]['profiled_groups'],0)

    def test_inherited_recognition_body_is_exact_not_replaced_by_a_new_heuristic(self):
        p=Path(__file__).with_name('profiled_single_tap_instruments.py');n=next(x for x in ast.parse(p.read_text('utf8')).body if isinstance(x,ast.FunctionDef)and x.name=='single_tap_measurements');self.assertEqual(hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest(),INHERITED_RECOGNIZER_AST_SHA256)

if __name__=='__main__':unittest.main()
