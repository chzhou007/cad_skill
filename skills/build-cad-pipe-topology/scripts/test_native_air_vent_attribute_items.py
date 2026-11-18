import copy,unittest
import ezdxf
from native_air_vent_attribute_items import collect
from axis_unbranched_vertical_DN import chain_evidence,native_items
from native_line_path_evidence import LAYERS


def fixture(trim=True,mirror=False):
    doc=ezdxf.new();space=doc.modelspace();x,y=2250000,170000;sign=-1 if mirror else 1
    lower=[x,y-200*sign];corner=[x,y];port=[x,y+100*sign];right=[x+200,y];layer=LAYERS['supply']
    if trim:space.add_line(lower,port,dxfattribs={'layer':layer})
    else:
        space.add_line(lower,corner,dxfattribs={'layer':layer});space.add_line(corner,port,dxfattribs={'layer':layer})
    space.add_line(corner,right,dxfattribs={'layer':layer})
    space.add_text('CRAH-4#-1-1',dxfattribs={'insert':(2231944.029906254,130877.5098815536),'height':20})
    anchor=space.add_attdef('WHAT',insert=port,text='自动排气阀',dxfattribs={'height':2})
    graph=dict(metadata={},nodes=[dict(node_id='A',node_type='virtual_equipment',x=lower[0],y=lower[1],floor=3),dict(node_id='B',node_type='virtual_equipment',x=right[0],y=right[1],floor=3)],
        edges=[dict(edge_id='E',start_node_id='A',end_node_id='B',system='supply',attribute_paths=[[lower,corner,right]],equipment_inventory=[dict(equipment_type='自动放气阀',device_names=['AAV1'],count=1)])])
    inventory=[dict(device_name='AAV1',equipment_type='自动放气阀',source_kind='semantic_attdef_folded_'+('trim' if trim else 'remove'),system_hint='supply',edge_id='E',assignment_status='assigned',x=str(port[0]),y=str(port[1]),assignment_x=str(x),assignment_y=str(y))]
    scopes=[dict(path_index=0,segment_index=i,system='supply',scope_points=graph['edges'][0]['attribute_paths'][0][i:i+2],native_source_status='single_source_line_covers') for i in (0,1)]
    return doc,graph,inventory,anchor,scopes


class InheritedAirVentItemsTests(unittest.TestCase):
    def test_original_trim_remove_and_mirror_make_attribute_bend_without_source_or_component_edits(self):
        for trim,mirror in ((True,False),(False,False),(True,True),(False,True)):
            with self.subTest(trim=trim,mirror=mirror):
                doc,g,inv,anchor,scopes=fixture(trim,mirror);before=copy.deepcopy((g,inv));source=[(e.dxf.handle,str(e.dxf.all_existing_dxf_attribs())) for e in doc.modelspace()]
                with self.assertRaisesRegex(ValueError,'another source arm'):chain_evidence(scopes,None,native_items(doc,g))
                items,proof=collect(doc,g,inv);continuity=chain_evidence(scopes,None,items)
                self.assertEqual(proof['canonical_folded_vents'],1);self.assertEqual(continuity['bends'][0]['source_arms'],2)
                self.assertEqual(proof['records'][0]['native_anchor']['handle'],anchor.dxf.handle)
                self.assertEqual(proof['records'][0]['original_removal']['action'],'trim' if trim else 'remove')
                self.assertEqual((g,inv),before);self.assertEqual(source,[(e.dxf.handle,str(e.dxf.all_existing_dxf_attribs())) for e in doc.modelspace()])
                self.assertEqual(proof['physical_lengths_assigned'],0);self.assertEqual(proof['components_reassigned'],0)

    def test_missing_semantics_changed_owner_active_pipe_and_real_continuation_are_held(self):
        for variant in ('semantic','owner','active','real_pipe','duplicate'):
            with self.subTest(variant=variant):
                doc,g,inv,anchor,scopes=fixture();space=doc.modelspace();port=list(anchor.dxf.insert)[:2]
                if variant=='semantic':anchor.dxf.text='未知设备'
                elif variant=='owner':inv[0]['edge_id']='OTHER'
                elif variant=='active':g['edges'][0]['attribute_paths'].append([[2250000,170000],port])
                elif variant=='real_pipe':space.add_line(port,(port[0],port[1]+100),dxfattribs={'layer':LAYERS['supply']})
                else:space.add_line((2250000,169800),port,dxfattribs={'layer':LAYERS['supply']})
                with self.assertRaises(ValueError):collect(doc,g,inv)

if __name__=='__main__':unittest.main()
