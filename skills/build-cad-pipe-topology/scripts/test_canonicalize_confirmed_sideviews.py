import copy
import math
import unittest
import ezdxf
from canonicalize_confirmed_sideviews import apply,DECISION,source_expression_context

def fixture():
    doc=ezdxf.new();m=doc.modelspace();layer='空调冷冻水供水'
    main=m.add_line((-300,0),(300,0),dxfattribs={'layer':layer})
    branch=m.add_line((0,-300),(0,-100),dxfattribs={'layer':layer})
    m.add_circle((0,0),100,dxfattribs={'layer':layer})
    upper=m.add_line((1000,-1000),(1000,-800),dxfattribs={'layer':layer})
    doc.blocks.new('wave');wave=m.add_blockref('wave',(1000,-800))
    def node(n,x,y,kind='virtual_equipment',subtype='out_of_plane_interface'):
        return dict(node_id=n,x=x,y=y,node_type=kind,subtype=subtype,system='supply')
    def edge(n,a,b,path,h):
        return dict(edge_id=n,start_node_id=a,end_node_id=b,system='supply',path=path,
            attribute_paths=[copy.deepcopy(path)],path_length=sum(math.dist(p,q) for p,q in zip(path,path[1:])),
            source_handles=[h],equipment_names=[],equipment_counts={})
    nodes=[node('I',1000,-1000),node('U',1000,-800,subtype='unresolved_source_terminal'),node('D',0,-300),
           node('T',0,0,'tee','physical_tee'),node('A',-300,0),node('B',300,0),node('EQ',50,50,'equipment','real_equipment')]
    edges=[edge('UP','I','U',[[1000,-1000],[1000,-800]],upper.dxf.handle),
        edge('BR','T','D',[[0,0],[0,-300]],branch.dxf.handle),
        edge('ML','A','T',[[-300,0],[0,0]],main.dxf.handle),edge('MR','T','B',[[0,0],[300,0]],main.dxf.handle)]
    edges[0]['source_wave_terminal']=dict(source_wave_handle=wave.dxf.handle,endpoint_node_id='U',source_sha256='S')
    graph=dict(metadata=dict(source_sha256='S',hil_ready=True),nodes=nodes,edges=edges,virtual_equipment_ports=[])
    row=dict(label='左侧第1组',upper=[['I','UP']],detail=[['D','BR']])
    manifest=dict(source_sha256='S',graph_sha256='G',images=[dict(sha256='IMAGE',rows=[row])])
    reply=dict(sections=[dict(image=dict(sha256='IMAGE'),questions=[dict(id='Q',text='左侧第1组 I 与 D',answer=dict(decision=DECISION))])])
    return doc,graph,manifest,reply

class CanonicalSideviewTests(unittest.TestCase):
    def test_archived_expression_context_never_reinstates_physical_nodes(self):
        d,g,m,r=fixture();out,_=apply(d,g,[],m,r,['Q'],'S','G');original=copy.deepcopy(out)
        context=source_expression_context(out)
        self.assertEqual({n['node_id'] for n in context['nodes']},{n['node_id'] for n in g['nodes']})
        self.assertTrue(context['source_expression_context_only']);self.assertEqual(out,original)
        out['confirmedSideviewCanonicalization']['representation_only_nodes'][0]['node_type']='equipment'
        with self.assertRaises(ValueError):source_expression_context(out)
    def test_reuse_three_edge_detail_and_preserve_abbreviated_source(self):
        d,g,m,r=fixture();before=copy.deepcopy(g)
        out,audit=apply(d,g,[],m,r,['Q'],'S','G')
        self.assertEqual(len(out['edges']),3)
        self.assertEqual({n['node_id'] for n in out['nodes']},{'D','T','A','B','EQ'})
        br=next(e for e in out['edges'] if e['edge_id']=='BR')
        self.assertEqual(br['path_length'],200);self.assertEqual(br['attribute_paths'],[[[0.,-100.],[0,-300]]])
        self.assertEqual(audit['corrected_circle_display_lengths'][0]['old_drawing_length'],300)
        state=out['confirmedSideviewCanonicalization']
        self.assertEqual(state['edge_aliases'],{'UP':'BR'});self.assertEqual(state['node_aliases'],{'I':'D'})
        self.assertEqual(state['representation_only_edges'],[g['edges'][0]])
        self.assertFalse(out['metadata']['hil_ready']);self.assertEqual(g,before)
    def test_projected_other_main_is_not_split_or_attached(self):
        d,g,m,r=fixture();other=copy.deepcopy(g['edges'][2]);other.update(edge_id='OTHER',start_node_id='P',end_node_id='Q',path=[[-300,0],[300,0]],attribute_paths=[[[-300,0],[300,0]]],path_length=600)
        for name,x in [('P',-300),('Q',300)]:g['nodes'].append(dict(node_id=name,x=x,y=0,node_type='virtual_equipment',system='supply'))
        g['edges'].append(other)
        out,_=apply(d,g,[],m,r,['Q'],'S','G')
        self.assertEqual(next(e for e in out['edges'] if e['edge_id']=='OTHER'),other)
        self.assertEqual(sum('T' in (e['start_node_id'],e['end_node_id']) for e in out['edges']),3)
    def test_unconfirmed_changed_pair_and_stale_graph_reject(self):
        for field in ('answer','image','graph'):
            d,g,m,r=fixture()
            if field=='answer':r['sections'][0]['questions'][0]['answer']['decision']='不是同一组'
            elif field=='image':r['sections'][0]['image']['sha256']='OTHER'
            else:m['graph_sha256']='OLD'
            with self.assertRaises(ValueError):apply(d,g,[],m,r,['Q'],'S','G')
    def test_missing_main_split_is_not_accepted_as_a_T(self):
        d,g,m,r=fixture();g['edges']=[e for e in g['edges'] if e['edge_id']!='MR']
        with self.assertRaisesRegex(ValueError,'three incident'):apply(d,g,[],m,r,['Q'],'S','G')
    def test_upper_components_require_instance_mapping(self):
        d,g,m,r=fixture()
        with self.assertRaisesRegex(ValueError,'components require'):apply(d,g,[dict(edge_id='UP')],m,r,['Q'],'S','G')
    def test_equipment_and_mixed_service_are_protected(self):
        for field in ('equipment','service'):
            d,g,m,r=fixture()
            if field=='equipment':g['nodes'][0].update(node_type='equipment',subtype='real_equipment')
            else:g['edges'][1]['system']='return'
            with self.assertRaises(ValueError):apply(d,g,[],m,r,['Q'],'S','G')
    def test_circle_ambiguity_and_moved_native_branch_reject(self):
        for field in ('circle','line'):
            d,g,m,r=fixture()
            if field=='circle':d.modelspace().add_circle((0,0),100)
            else:d.entitydb[g['edges'][1]['source_handles'][0]].dxf.start=(10,-300)
            with self.assertRaises(ValueError):apply(d,g,[],m,r,['Q'],'S','G')

if __name__=='__main__':unittest.main()
