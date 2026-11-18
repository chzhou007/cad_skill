import copy,unittest
from unittest.mock import patch
import ezdxf
import equivalent_member_source_support as rule

class Tests(unittest.TestCase):
    def fixture(self):
        docs={v:ezdxf.new()for v in('plan','iso')};graphs={};handles=[]
        for v in docs:
            d=docs[v];ms=d.modelspace();off=0 if v=='plan'else 10000;layer=rule.LAYERS['supply'];main=ms.add_line((off-500,0),(off+2500,0),dxfattribs=dict(layer=layer))
            if v=='plan':handles=[main.dxf.handle,ms.add_line((off-500,0),(off+2500,0),dxfattribs=dict(layer=layer)).dxf.handle]
            nodes=[];edges=[]
            for i,x in enumerate((0,1000,2000)):
                nid=v+str(i);eq='EQ'+str(i);nodes.extend([dict(node_id=nid,node_type='tee',system='supply',floor=3,x=off+x,y=0),dict(node_id=eq,node_type='equipment',floor=3,x=off+x,y=100)])
                ms.add_text(eq,dxfattribs=dict(insert=(off+x,120),height=20));ms.add_line((off+x,0),(off+x,100),dxfattribs=dict(layer=layer))
                edges.append(dict(edge_id=v+'b'+str(i),system='supply',start_node_id=nid,end_node_id=eq,attribute_paths=[[[off+x,0],[off+x,100]]]))
                if v=='plan':ms.add_circle((x,0),10,dxfattribs=dict(layer=layer))
            for i in range(2):edges.append(dict(edge_id=v+'m'+str(i),system='supply',source_handles=[main.dxf.handle],start_node_id=v+str(i),end_node_id=v+str(i+1),attribute_paths=[[[off+1000*i,0],[off+1000*(i+1),0]]]))
            for side,x,tee in [('left',-500,0),('right',2500,2)]:
                nid=v+side;nodes.append(dict(node_id=nid,node_type='terminal',floor=3,x=off+x,y=0));edges.append(dict(edge_id=nid,system='supply',start_node_id=nid,end_node_id=v+str(tee),attribute_paths=[[[off+x,0],[off+tee*1000,0]]]))
            graphs[v]=dict(nodes=nodes,edges=edges)
        provider=dict(records=[dict(edge_id='isom'+str(i),classification='horizontal_only',has_existing_correspondence=True,correspondence_observations=[dict(domain='ordinary_local_graph',plan_edges=['planm'+str(i)])])for i in range(2)])
        hashes={v:dict(source_sha256=v+'source',graph_sha256=v+'graph')for v in docs}
        return docs,graphs,{f'plan{i}':f'iso{i}'for i in range(3)},provider,handles,hashes
    def qualify(self,fixture=None):
        d,g,m,p,h,hs=fixture or self.fixture()
        # The integration test replays the real historical circle owner. This
        # isolated kernel test records that its original document is supplied.
        calls=[]
        def reader(doc,graph,nid,sh,gh):
            self.assertIs(doc,d['plan']);calls.append(nid)
            branch=next(e for e in graph['edges']if e['edge_id']=='planb'+nid[-1])
            rays=[dict(edge_id=e['edge_id'],source_line_handle=h[0],coincident_native_main_handles=h)for e in graph['edges']if nid in(e['start_node_id'],e['end_node_id'])and e is not branch]
            return dict(source_sha256=sh,graph_sha256=gh,junctions=[dict(node_id=nid,system='supply',source_rays=rays)])
        r=rule.qualify_cohort(d,g,m,p,3,'supply',h,hs,reader)
        self.assertEqual(len(calls),3);return r,(d,g,m,p,h,hs)
    def test_complete_cohort_requires_independent_labels_native_circle_population_and_existing_chain(self):
        r,f=self.qualify();self.assertEqual(len(r['branches']),3);self.assertEqual(len(r['links']),2);self.assertFalse(r['source_entity_physical_identity_resolved']);self.assertFalse(r['physical_pipe_count_inferred'])
        d,g,m,p,h,hs=f;before=copy.deepcopy(g);cov=rule.member_coverage(d['plan'],g['plan'],['planm0'],hs['plan']['source_sha256'],hs['plan']['graph_sha256'],[r],set())
        self.assertEqual(cov['original_source_audit']['edges'][0]['segments'][0]['status'],'ambiguous_multiple_witnesses');self.assertEqual(cov['edges'][0]['segments'][0]['status'],'single_source_line_covers');self.assertEqual(g,before);self.assertEqual(len(d['plan'].modelspace().query('LINE')),5)
    def test_unmapped_native_circle_and_missing_raw_equipment_label_block(self):
        for mode in('mapping','label','extra_circle','prior'):
            f=self.fixture();d,g,m,p,h,hs=f
            if mode=='mapping':m.pop('plan1')
            elif mode=='label':d['iso'].modelspace().delete_entity(next(t for t in d['iso'].modelspace().query('TEXT')if t.plain_text()=='EQ1'))
            elif mode=='extra_circle':d['plan'].modelspace().add_circle((1500,0),10,dxfattribs=dict(layer=rule.LAYERS['supply']))
            else:p['records'][0]['correspondence_observations'][0]['plan_edges']=['wrong']
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.qualify(f)
    def test_same_xy_different_z_or_style_is_not_equivalent(self):
        for mode in('z','style'):
            f=self.fixture();d,g,m,p,h,hs=f;e=d['plan'].entitydb[h[1]]
            if mode=='z':e.dxf.start=(e.dxf.start.x,0,2);e.dxf.end=(e.dxf.end.x,0,2)
            else:e.dxf.color=4
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.qualify(f)
    def test_selected_cap_common_interval_preserves_unequal_native_tails(self):
        cohort,f=self.qualify();d=f[0]['plan'];ms=d.modelspace();layer=rule.LAYERS['supply'];a=ms.add_line((2500,0),(2500,1000),dxfattribs=dict(layer=layer));b=ms.add_line((2500,0),(2500,1080),dxfattribs=dict(layer=layer));original=rule._xyz(a),rule._xyz(b)
        s=dict(start=[2500,20],end=[2500,900],witnesses=[dict(scope='modelspace',source_handle=l.dxf.handle)for l in(a,b)])
        p=rule.equivalent_support(d,s,'supply',[cohort],set());self.assertEqual(p['representative_observation_handle'],b.dxf.handle);self.assertEqual(original,(rule._xyz(a),rule._xyz(b)));self.assertTrue(p['original_tails_unchanged'])
        with self.assertRaises(ValueError):rule.equivalent_support(d,s,'supply',[cohort],{a.dxf.handle})
        with self.assertRaises(ValueError):rule.equivalent_support(d,s,'supply',[cohort,copy.deepcopy(cohort)],set())
    def test_unrelated_missing_or_other_scope_source_is_never_filled(self):
        cohort,f=self.qualify();d,g,m,p,h,hs=f
        g['plan']['edges'][3]['attribute_paths']=[[[0,0],[1000,80]]]
        with self.assertRaises(ValueError):rule.member_coverage(d['plan'],g['plan'],[g['plan']['edges'][3]['edge_id']],hs['plan']['source_sha256'],hs['plan']['graph_sha256'],[cohort],set())
        with self.assertRaises(ValueError):rule.member_coverage(d['plan'],g['plan'],['planm0'],'other',hs['plan']['graph_sha256'],[cohort],set())
    def test_compound_carrier_stops_whole_bounded_group_even_with_unique_observation(self):
        cohort,f=self.qualify();d,g,m,p,h,hs=f
        with self.assertRaisesRegex(ValueError,'compound carrier path'):
            rule.member_coverage(d['plan'],g['plan'],['planm0'],hs['plan']['source_sha256'],hs['plan']['graph_sha256'],[cohort],{h[0]})
    def test_original_algorithm_globals_and_code_are_preserved(self):
        before=dict(rule.original.prove.__globals__);cohort,f=self.qualify();d,g,m,p,h,hs=f
        r=rule.bounded_apply(d,g,dict(junction_mapping=m,records=[]),3,dict(plan=[],iso=[]),hs,[],{},[cohort],set())
        self.assertEqual(r['counts']['unique_new_axis_edges'],0);self.assertTrue(r['native_junctions_read_original_document'])
        self.assertEqual(before,rule.original.prove.__globals__)
if __name__=='__main__':unittest.main()
