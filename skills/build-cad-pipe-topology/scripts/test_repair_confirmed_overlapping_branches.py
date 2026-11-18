import copy
import unittest
import ezdxf
from repair_confirmed_overlapping_branches import apply


class OverlappingBranchesTests(unittest.TestCase):
    def setUp(self):
        self.doc=ezdxf.new();m=self.doc.modelspace()
        main=m.add_line((0,0),(1000,0),dxfattribs={'layer':'supply'})
        a=m.add_line((300,80),(300,300),dxfattribs={'layer':'supply'})
        c=m.add_line((300,-300),(300,-80),dxfattribs={'layer':'supply'})
        ca=m.add_circle((300,0),80);cb=m.add_circle((700,0),80)
        def n(i,x,y,sub=None):return {'node_id':i,'node_type':'virtual_equipment' if sub else 'tee','subtype':sub,'system':'supply','x':x,'y':y,'floor':1}
        def e(i,a,b,path,h):return {'edge_id':i,'start_node_id':a,'end_node_id':b,'system':'supply','start_floor':1,'end_floor':1,'path':path,'path_points':copy.deepcopy(path),'attribute_paths':[copy.deepcopy(path)],'path_length':sum(((q[0]-p[0])**2+(q[1]-p[1])**2)**.5 for p,q in zip(path,path[1:])),'source_handles':[h],'equipment_names':[],'equipment_counts':{}}
        self.graph={'metadata':{'source_sha256':'s'},'nodes':[n('L',0,0),n('R',1000,0),n('UA',300,80,'unresolved_source_terminal'),n('UC',300,-80,'unresolved_source_terminal'),n('VA',300,300,'out_of_plane_interface'),n('VC',300,-300,'out_of_plane_interface')], 'edges':[e('M','L','R',[[0,0],[1000,0]],main.dxf.handle),e('A','VA','UA',[[300,300],[300,80]],a.dxf.handle),e('C','VC','UC',[[300,-300],[300,-80]],c.dxf.handle)], 'virtual_equipment_ports':[], 'sourceCircleCrossoverConflicts':[{'status':'pending'}]}
        def conn(h,branch,terminal,line,center,mode,route):return {'main_edge':'M','branch_edge':branch,'terminal':terminal,'circle_handle':h,'main_handle':main.dxf.handle,'branch_handle':line,'system':'supply','pipe_layer':'supply','circle_center':center,'circle_radius':80,'connection_mode':mode,'display_route':route}
        self.policy={'source_sha256':'s','graph_sha256':'g','evidence_manifest_sha256':'ev','confirmed_by':'user','connections':[conn(ca.dxf.handle,'A','UA',a.dxf.handle,[300,0],'native_circle_rim',[[300,80],[300,0]]),conn(cb.dxf.handle,'C','UC',c.dxf.handle,[700,0],'user_confirmed_hidden_overlap',[[300,-80],[300,0],[700,0]])]}

    def test_separate_tees_without_fabricated_intermediate_pipe(self):
        out,audit=apply(self.doc,self.graph,[],self.policy,'s','g','ev')
        self.assertEqual(len(audit['records']),2)
        for r in audit['records']:
            self.assertEqual(len([e for e in out['edges'] if r['tee'] in (e['start_node_id'],e['end_node_id'])]),3)
        branch=next(e for e in out['edges'] if e['edge_id']=='C')
        self.assertEqual(branch['attribute_paths'],[[[300,-300],[300,-80]]]);self.assertEqual(branch['path_length'],220)
        self.assertEqual(branch['physical_length'],'unknown');self.assertFalse(branch['path_length_complete'])
        self.assertIn('source_coverage_unverified',branch['path_length_scope'])
        self.assertNotEqual(branch['end_node_id'],audit['records'][0]['tee'])
        self.assertEqual(out['sourceCircleCrossoverConflicts'],self.graph['sourceCircleCrossoverConflicts'])
        self.assertFalse(out['metadata']['hil_ready'])

    def test_reject_wrong_system_layer_and_wrong_branch_source(self):
        for key,value in [('system','return'),('pipe_layer','return'),('branch_handle','bad')]:
            p=copy.deepcopy(self.policy);p['connections'][1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):apply(self.doc,self.graph,[],p,'s','g','ev')

    def test_reject_stale_confirmation_duplicates_and_invalid_route(self):
        for p in (dict(self.policy,confirmed_by='algorithm'),dict(self.policy,graph_sha256='stale')):
            with self.assertRaises(ValueError):apply(self.doc,self.graph,[],p,'s','g','ev')
        p=copy.deepcopy(self.policy);p['connections'][1]['circle_handle']=p['connections'][0]['circle_handle']
        with self.assertRaises(ValueError):apply(self.doc,self.graph,[],p,'s','g','ev')
        p=copy.deepcopy(self.policy);p['connections'][1]['display_route']=[[0,0],[700,0]]
        with self.assertRaises(ValueError):apply(self.doc,self.graph,[],p,'s','g','ev')

    def test_reject_unsafely_split_main_with_components_or_diameter(self):
        with self.assertRaises(ValueError):apply(self.doc,self.graph,[{'edge_id':'M'}],self.policy,'s','g','ev')
        g=copy.deepcopy(self.graph);g['edges'][0]['diameter_nominal_mm']=250
        with self.assertRaises(ValueError):apply(self.doc,g,[],self.policy,'s','g','ev')

    def test_prior_confirmed_repair_is_retained(self):
        g=copy.deepcopy(self.graph);g['userConfirmedOverlappingBranches']={'records':[{'circle_handle':'OLD'}]}
        out,_=apply(self.doc,g,[],self.policy,'s','g','ev')
        self.assertEqual(out['userConfirmedOverlappingBranches']['previous_repair'],g['userConfirmedOverlappingBranches'])


if __name__=='__main__':unittest.main()
