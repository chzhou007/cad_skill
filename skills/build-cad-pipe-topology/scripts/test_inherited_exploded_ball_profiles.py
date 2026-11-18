import copy,unittest,ezdxf
from inherited_exploded_ball_profiles import collect,footprint,recover,FAMILY

def fixture(scale=1,rotation=0,z=0):
    doc=ezdxf.new();doc.layers.new('空调冷冻水供水');block=doc.blocks.new('df')
    for a,b in[((-80,-100,0),(-80,100,0)),((80,-100,0),(80,100,0)),((-45,-90,0),(45,90,0))]:block.add_line(a,b,dxfattribs={'color':2})
    for start,end in[(0,3.141592653589793),(3.141592653589793,6.283185307179586)]:block.add_ellipse((0,0,0),(20,0,0),ratio=1,start_param=start,end_param=end,dxfattribs={'color':2})
    hatch=block.add_hatch(color=2);bulge=0.41421356237309503
    hatch.paths.add_polyline_path([(20,0,bulge),(0,20,bulge),(-20,0,bulge),(0,-20,bulge)],is_closed=True)
    top=doc.modelspace().add_blockref('df',(0,0,z),dxfattribs={'xscale':scale,'yscale':1,'rotation':rotation,'layer':'空调冷冻水供水'})
    import math
    direction=[math.cos(math.radians(rotation)),math.sin(math.radians(rotation))]
    p=[-300*direction[0],-300*direction[1],z];q=[300*direction[0],300*direction[1],z]
    line=doc.modelspace().add_line(p,q,dxfattribs={'layer':'空调冷冻水供水'})
    g=dict(nodes=[],edges=[dict(edge_id='E',start_node_id='A',end_node_id='B',system='supply',source_handles=[line.dxf.handle],attribute_paths=[[p[:2],q[:2]]],connection_mode='continuous_original_cad_pipe')])
    rows=[dict(device_name='球阀-BV',equipment_type='球阀',edge_id='E',source_block_name=FAMILY,source_top_handle=top.dxf.handle)]
    return doc,g,rows,top,block,line

class Exploded(unittest.TestCase):
    def test_plan_mode_cannot_silently_report_zero_for_unclaimed_source_bodies(self):
        d,g,rows,top,block,line=fixture();g['edges'][0]['connection_mode']='source_plan_pipe'
        with self.assertRaisesRegex(ValueError,'not unique'):collect(d,g,[],['E'],'plan')
        reading,proof=recover(d,g,[],'plan')
        self.assertEqual(proof['recovered_physical_source_instances'],1)
        self.assertEqual(reading[0]['source_top_handle'],top.dxf.handle)
        self.assertEqual(collect(d,g,reading,['E'],'plan')['profiles'],{'E':{'ball_valve':1}})

    def test_recovery_preserves_old_rows_and_never_duplicates_recognized_instances(self):
        d,g,rows,top,block,line=fixture();before=copy.deepcopy(rows)
        reading,proof=recover(d,g,rows,'iso');self.assertEqual(reading,before);self.assertFalse(proof['records'])
        reading,proof=recover(d,g,[],'iso');again,p=recover(d,g,reading,'iso')
        self.assertEqual(again,reading);self.assertFalse(p['records'])

    def test_original_kernel_rotation_mirror_and_exact_native_contacts(self):
        for scale,angle in[(1,0),(-1,0),(1,90),(-1,135)]:
            d,g,rows,top,block,line=fixture(scale,angle);before=copy.deepcopy(rows)
            out=collect(d,g,rows,['E'],'iso');self.assertEqual(out['profiles'],{'E':{'ball_valve':1}})
            self.assertEqual(len(out['records'][0]['native_contact']['flange_contacts']),2);self.assertEqual(rows,before)

    def test_missing_native_stroke_is_not_a_ball_valve(self):
        d,g,rows,top,block,line=fixture();block.delete_entity(next(iter(block)))
        with self.assertRaisesRegex(ValueError,'not independently requalified'):collect(d,g,rows,['E'],'iso')

    def test_wrong_Z_and_duplicate_source_pipe_are_not_snapped(self):
        for mutation in('Z','duplicate'):
            d,g,rows,top,block,line=fixture()
            if mutation=='Z':line.dxf.start=(line.dxf.start.x,line.dxf.start.y,1);line.dxf.end=(line.dxf.end.x,line.dxf.end.y,1)
            else:d.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
            with self.assertRaisesRegex(ValueError,'not unique'):collect(d,g,rows,['E'],'iso')

    def test_wrong_prior_owner_is_rejected(self):
        d,g,rows,top,block,line=fixture();rows[0]['edge_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'owner or family differs'):collect(d,g,rows,['E'],'iso')

if __name__=='__main__':unittest.main()
