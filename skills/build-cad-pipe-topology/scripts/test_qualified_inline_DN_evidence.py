import copy,math,unittest
import ezdxf
from qualified_inline_DN_evidence import collect
from repair_native_flexible_joints import fingerprint


def fixture(angle=0,mirror=False):
    doc=ezdxf.new('R2018');block=doc.blocks.new('FLEX');block.add_point((0,0));block.add_point((300,0));block.add_line((0,-40),(0,40));block.add_line((300,-40),(300,40));block.add_spline(fit_points=[(0,0),(100,50),(200,-50),(300,0)])
    m=doc.modelspace();r=math.radians(angle)
    def rotate(p):return (p[0]*math.cos(r)-p[1]*math.sin(r),p[0]*math.sin(r)+p[1]*math.cos(r),0)
    graph=dict(metadata={'source_sha256':'S'},edges=[]);leaves=[];joints=[]
    for service,y in [('supply',0),('return',-400)]:
        edge=dict(edge_id=service,system=service,equipment_names=[],equipment_counts={'flexible_joint':2},source_flexible_joints=[])
        for x in (0,500):
            ins=m.add_blockref('FLEX',rotate((x,y)),dxfattribs={'rotation':angle,'xscale':-1 if mirror else 1});pts=[list(e.dxf.location) for e in ins.virtual_entities() if e.dxftype()=='POINT'];h=ins.dxf.handle
            edge['equipment_names'].append('CASE-FLEX-'+h);edge['source_flexible_joints'].append(dict(source_handle=h,source_block='FLEX',source_contact_points=[p[:2] for p in pts],physical_length='unknown',parameter_status='unknown_not_zero'))
            leaves.append(pts[-1]);joints.append(ins)
        graph['edges'].append(edge)
    qualifier=m.add_text('金属软管',dxfattribs={'insert':rotate((1050,1600)),'height':350,'rotation':angle,'layer':'NOTE'})
    dn=m.add_text('DN300',dxfattribs={'insert':rotate((1100,1150)),'height':350,'rotation':angle,'layer':'NOTE'})
    hub=rotate((1000,1500));leaders=[m.add_line(hub,rotate((2200,1500)),dxfattribs={'layer':'NOTE'})]
    leaders += [m.add_line(hub,p,dxfattribs={'layer':'NOTE'}) for p in leaves]
    spec=dict(qualifier_handle=qualifier.dxf.handle,dn_handle=dn.dxf.handle,expected_text='DN300',leader_handles=[e.dxf.handle for e in leaders],expected_component_handles=[x.dxf.handle for x in joints])
    policy=dict(source_sha256='S',graph_sha256='G',block_name='FLEX',block_fingerprint_sha256=fingerprint(block),labels=[spec])
    return doc,graph,policy,qualifier,dn,leaders,joints


class QualifiedInlineDNTests(unittest.TestCase):
    def test_component_DN_never_overrides_main_DN_or_adds_hydraulic_parameters(self):
        for angle in (0,90,180,270):
            for mirror in (False,True):
                doc,g,p,*_=fixture(angle,mirror);before=copy.deepcopy(g);out=collect(doc,g,p,'S','G');r=out['records'][0]
                self.assertEqual(g,before);self.assertEqual(r['nominal_mm'],300);self.assertEqual(len(r['bindings']),4)
                self.assertEqual({x['system'] for x in r['bindings']},{'supply','return'});self.assertFalse(out['pipe_DN_inferred']);self.assertFalse(r['physical_parameter_verified']);self.assertIsNone(r['resistance_parameter'])
                self.assertEqual(out['consumed_DN_text_handles'],[p['labels'][0]['dn_handle']])

    def test_unknown_qualifier_unbound_or_ambiguous_leaves_and_changed_native_geometry_fail(self):
        for mode in ('qualifier','text','label-position','free-leaf','duplicate-instance','source-z','graph-owner','contacts','physical-claim','source','fingerprint','subset'):
            doc,g,p,q,dn,lines,joints=fixture()
            if mode=='qualifier':q.dxf.text='管道'
            elif mode=='text':dn.dxf.text='DN200'
            elif mode=='label-position':q.dxf.insert=(5000,5000,0)
            elif mode=='free-leaf':lines[-1].dxf.end=(9000,9000,0)
            elif mode=='duplicate-instance':doc.modelspace().add_blockref('FLEX',joints[-1].dxf.insert)
            elif mode=='source-z':lines[-1].dxf.end=(lines[-1].dxf.end.x,lines[-1].dxf.end.y,5)
            elif mode=='graph-owner':g['edges'][0]['equipment_names']=[]
            elif mode=='contacts':g['edges'][0]['source_flexible_joints'][0]['source_contact_points'][0][0]+=1
            elif mode=='physical-claim':g['edges'][0]['source_flexible_joints'][0]['physical_length']=0
            elif mode=='source':p['source_sha256']='OTHER'
            elif mode=='fingerprint':p['block_fingerprint_sha256']='OTHER'
            else:p['labels'][0]['expected_component_handles'].pop()
            with self.subTest(mode=mode),self.assertRaises(ValueError):collect(doc,g,p,'S','G')


if __name__=='__main__':unittest.main()
