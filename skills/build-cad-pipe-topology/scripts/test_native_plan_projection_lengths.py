import copy,unittest
import ezdxf
from native_plan_projection_lengths import unit_evidence,lengths
from native_path_coverage_audit import audit

def fixture():
    doc=ezdxf.new('R2018');doc.header['$INSUNITS']=4;m=doc.modelspace();title=m.add_text('二层顶部水管平面图',dxfattribs={'insert':(0,0)})
    specs=[];dims=[]
    for end,angle in [((600,0),0),((0,750),90)]:
        drawing=m.add_linear_dim(base=(1000,1000),p1=(0,0),p2=end,angle=angle);drawing.render();dim=drawing.dimension
        text=next(t for t in doc.blocks[dim.dxf.geometry] if t.dxftype() in ('TEXT','MTEXT'))
        specs.append(dict(handle=dim.dxf.handle,text_handle=text.dxf.handle,text=text.plain_text()));dims.append(dim)
    m.add_line((100,100),(900,100),dxfattribs={'layer':'空调冷冻水供水'})
    graph=dict(edges=[dict(edge_id='P',system='supply',attribute_paths=[[[100,100],[900,100]]])])
    policy=dict(view_kind='floor_plan',plan_window=[-100,1500,-100,1500],floor_title_handle=title.dxf.handle,floor_title=title.plain_text(),unit_dimensions=specs)
    coverage=audit(doc,graph,dict(source_sha256='S',graph_sha256='G',edges=['P']),'S','G')
    return doc,graph,policy,coverage,dims

class PlanProjectionMetricTests(unittest.TestCase):
    def test_native_mm_and_two_directions_produce_only_known_plan_projection(self):
        d,g,p,c,_=fixture();before=copy.deepcopy(g);u=unit_evidence(d,p);result=lengths(g,c,dict(plan_edges=['P'],system='supply'),u)
        self.assertEqual(result['value_mm'],800);self.assertIsNone(result['installed_whole_edge_length_mm']);self.assertEqual(g,before)
    def test_units_manual_dimension_text_and_factor_are_not_silently_accepted(self):
        for kind in ('units','override','factor','scope'):
            d,g,p,c,dims=fixture()
            if kind=='units':d.header['$INSUNITS']=0
            elif kind=='override':dims[0].dxf.text='600'
            elif kind=='factor':override=dims[0].override();override.update({'dimlfac':.5});override.commit()
            else:p['plan_window']=[0,10,0,10]
            with self.assertRaises(ValueError):unit_evidence(d,p)
    def test_same_direction_dimensions_do_not_corroborate_two_axes(self):
        d,g,p,c,dims=fixture();drawing=d.modelspace().add_linear_dim(base=(0,1000),p1=(0,0),p2=(750,0),angle=0);drawing.render();dim=drawing.dimension
        text=next(t for t in d.blocks[dim.dxf.geometry] if t.dxftype() in ('TEXT','MTEXT'))
        p['unit_dimensions'][1]=dict(handle=dim.dxf.handle,text_handle=text.dxf.handle,text=text.plain_text())
        with self.assertRaisesRegex(ValueError,'independent'):unit_evidence(d,p)
    def test_missing_ambiguous_or_stale_source_piece_cannot_be_measured(self):
        for kind in ('missing','ambiguous','changed','nested'):
            d,g,p,c,_=fixture();s=c['edges'][0]['segments'][0]
            if kind=='missing':s['status']='no_witness_in_scoped_search';s['witnesses']=[]
            elif kind=='ambiguous':s['witnesses'].append(copy.deepcopy(s['witnesses'][0]))
            elif kind=='changed':g['edges'][0]['attribute_paths'][0][1][0]+=10
            else:s['witnesses'][0]['scope']='decomposed_selected_insert'
            with self.assertRaises(ValueError):lengths(g,c,dict(plan_edges=['P'],system='supply'),unit_evidence(d,p))

if __name__=='__main__':unittest.main()
