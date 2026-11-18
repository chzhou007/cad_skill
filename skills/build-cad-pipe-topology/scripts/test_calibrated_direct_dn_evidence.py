import copy,unittest
import ezdxf
from calibrated_direct_dn_evidence import collect


class CalibratedDirectDNTests(unittest.TestCase):
    def fixture(self):
        d=ezdxf.new();m=d.modelspace();supply='空调冷冻水供水';ret='空调冷冻水回水';label='空调平面'
        for layer in (supply,ret,label):d.layers.new(layer)
        edges=[];controls=[];targets=[]
        cases=[('C1','supply',(0,0),(100,0),(50,.5),0,'DN80'),('C2','return',(0,200),(100,200),(50,200.5),0,'DN80'),('C3','supply',(300,0),(300,100),(299.5,50),90,'DN80'),('C4','return',(500,0),(500,100),(499.5,50),90,'DN80'),('PS','supply',(1000,0),(1000,100),(998.9,50),90,'DN150(3.200)'),('PR','return',(1001,0),(1001,100),(1000.45,50),90,'DN80')]
        for eid,service,a,b,p,rotation,text in cases:
            line=m.add_line(a,b,dxfattribs={'layer':supply if service=='supply' else ret});t=m.add_text(text,dxfattribs={'layer':label,'height':1,'insert':p,'rotation':rotation})
            edges.append(dict(edge_id=eid,system=service,attribute_paths=[[list(a),list(b)]],source_handles=[line.dxf.handle]))
            spec=dict(text_handle=t.dxf.handle,expected_text=text,edge_id=eid,source_line_handle=line.dxf.handle)
            (controls if eid.startswith('C') else targets).append(spec)
        graph=dict(nodes=[],edges=edges,metadata=dict(source_sha256='S'))
        return d,graph,dict(source_sha256='S',graph_sha256='G',text_layers=[label],controls=controls,selections=targets)

    def test_independent_controls_resolve_close_pipes_without_extending_DN_scope(self):
        d,g,p=self.fixture();before=copy.deepcopy(g);result=collect(d,g,p,'S','G')
        self.assertEqual([(r['edge_id'],r['nominal_mm']) for r in result['observations']],[('PS',150),('PR',80)])
        self.assertEqual(result['observations'][0]['parenthesized_source_value'],'3.200');self.assertFalse(result['observations'][0]['physical_length_from_parentheses'])
        self.assertEqual(result['observations'][1]['rejected_wrong_side_native_pipes'][0]['handle'],p['selections'][0]['source_line_handle'])
        self.assertFalse(result['human_accepted']);self.assertEqual(g,before)

    def test_target_cannot_be_its_own_control_and_profiles_must_match(self):
        for mode in ('overlap','profile','inconsistent','one_service','one_direction','mirror'):
            d,g,p=self.fixture()
            if mode=='overlap':p['controls'][0]=copy.deepcopy(p['selections'][0])
            elif mode=='profile':d.entitydb[p['selections'][0]['text_handle']].dxf.width=2
            elif mode=='inconsistent':d.entitydb[p['controls'][3]['text_handle']].dxf.insert=(500.5,50,0)
            elif mode=='one_service':g['edges'][1]['system']='supply'
            elif mode=='one_direction':d.entitydb[p['controls'][3]['text_handle']].dxf.rotation=0
            else:d.entitydb[p['selections'][0]['text_handle']].dxf.text_generation_flag=2
            with self.subTest(mode=mode),self.assertRaises(ValueError):collect(d,g,p,'S','G')

    def test_side_is_learned_from_controls_instead_of_assuming_above_or_left(self):
        d,g,p=self.fixture()
        points=[(50,-.5),(50,199.5),(300.5,50),(500.5,50),(1000.45,50),(1002.1,50)]
        for spec,point in zip(p['controls']+p['selections'],points):d.entitydb[spec['text_handle']].dxf.insert=point
        result=collect(d,g,p,'S','G')
        self.assertEqual({r['calibrated_text_normal_side'] for r in result['observations']},{-1})
        self.assertEqual([(r['edge_id'],r['nominal_mm']) for r in result['observations']],[('PS',150),('PR',80)])

    def test_duplicate_native_pipe_wrong_owner_and_compound_note_fail_closed(self):
        for mode in ('duplicate','owner','compound','source','changed_value'):
            d,g,p=self.fixture()
            if mode=='duplicate':line=d.entitydb[p['selections'][1]['source_line_handle']];d.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
            elif mode=='owner':p['selections'][1]['source_line_handle']=p['selections'][0]['source_line_handle']
            elif mode=='compound':d.modelspace().add_text('供DN100/回DN80',dxfattribs={'layer':'空调平面','height':1,'insert':(1000.5,55),'rotation':90})
            elif mode=='source':p['source_sha256']='BAD'
            else:d.entitydb[p['selections'][0]['text_handle']].dxf.text='DN200'
            with self.subTest(mode=mode),self.assertRaises(ValueError):collect(d,g,p,'S','G')


if __name__=='__main__':unittest.main()
