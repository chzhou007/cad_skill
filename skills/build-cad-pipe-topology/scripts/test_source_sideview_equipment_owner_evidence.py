import copy,math,unittest
from test_calibrated_equipment_interface_ownership import fixture as layout_fixture
from canonicalize_confirmed_sideviews import apply as canonicalize,DECISION
from source_sideview_equipment_owner_evidence import collect

def fixture(angle=0,mirror=False,second=False,boundary=False):
    d,g,model,add=layout_fixture(angle,mirror);model.update(status='source_calibrated_supported_projection_pattern',physical_ports_verified=False,human_accepted=False)
    prefixes=['I-']
    if second:add('J-',250);prefixes.append('J-')
    archive_edges=list(g['edges']);m=d.modelspace();d.blocks.new('WAVE');rows=[];questions=[]
    g['boundary_anchors']=[]
    for index,prefix in enumerate(prefixes):
        upper=[];detail=[];label='case'+str(index);qid='Q'+str(index)
        for service,y in [('supply',index*5000),('return',index*5000+2000)]:
            old=next(e for e in archive_edges if e['edge_id']=='E-'+prefix+service);end=old['path'][-1]
            wave=m.add_blockref('WAVE',end);old['source_wave_terminal']=dict(source_wave_handle=wave.dxf.handle,endpoint_node_id=old['end_node_id'],source_sha256='S')
            did='D-'+prefix+service;tee='T-'+prefix+service;left='A-'+prefix+service;right='B-'+prefix+service;bid='BR-'+prefix+service
            line=m.add_line((10000,y),(12000,y),dxfattribs={'layer':('空调冷冻水供水' if service=='supply' else '空调冷冻水回水')})
            pipe=m.add_line((11000,y),(11000,y-500),dxfattribs={'layer':line.dxf.layer})
            for nid,x,yy,kind in [(tee,11000,y,'tee'),(left,10000,y,'virtual_equipment'),(right,12000,y,'virtual_equipment')]:
                g['nodes'].append(dict(node_id=nid,node_type=kind,subtype='physical_tee' if kind=='tee' else 'main_boundary',system=service,floor=1,x=x,y=yy))
            if boundary:g['boundary_anchors'].append(dict(boundary_id=did,system=service,floor=1,x=11000,y=y-500,boundary_type='source_non_node'))
            else:g['nodes'].append(dict(node_id=did,node_type='virtual_equipment',subtype='unresolved_source_terminal',system=service,floor=1,x=11000,y=y-500))
            for eid,a,b,pa,pb,h in [(bid,tee,None if boundary else did,[11000,y],[11000,y-500],pipe.dxf.handle),('ML-'+prefix+service,left,tee,[10000,y],[11000,y],line.dxf.handle),('MR-'+prefix+service,tee,right,[11000,y],[12000,y],line.dxf.handle)]:
                edge=dict(edge_id=eid,start_node_id=a,end_node_id=b,system=service,path=[pa,pb],attribute_paths=[[pa,pb]],path_length=math.dist(pa,pb),source_handles=[h],equipment_names=[],equipment_counts={})
                if b is None:edge['end_boundary_id']=did
                g['edges'].append(edge)
            upper.append([old['start_node_id'],old['edge_id']]);detail.append([did,bid])
        rows.append(dict(label=label,upper=upper,detail=detail));questions.append(dict(id=qid,text=label+' '+str(upper)+' '+str(detail),answer=dict(decision=DECISION)))
    manifest=dict(source_sha256='S',graph_sha256='G',images=[dict(sha256='b'*64,rows=rows)])
    reply=dict(sections=[dict(image=dict(sha256='b'*64),questions=questions)])
    graph,_=canonicalize(d,g,[],manifest,reply,[q['id'] for q in questions],'S','G')
    return d,graph,model

class SideviewOwnerEvidenceTests(unittest.TestCase):
    def test_reuses_confirmed_alias_and_existing_rotated_mirrored_native_calibration(self):
        for angle in (0,90,180,270):
            for mirror in (False,True):
                d,g,m=fixture(angle,mirror);before=copy.deepcopy(g);e=collect(d,g,m,'S','CURRENT')
                self.assertEqual(len(e['selected']),1);self.assertEqual(e['selected'][0]['candidate_owner'],'EQ')
                self.assertEqual({x['system'] for x in e['selected'][0]['canonical_endpoints']},{'supply','return'})
                self.assertFalse(e['context_promoted_to_physical_graph']);self.assertFalse(e['whole_physical_lengths_selected']);self.assertEqual(g,before)

    def test_non_node_boundaries_stay_non_node_in_read_only_evidence(self):
        d,g,m=fixture(boundary=True);before=copy.deepcopy(g);e=collect(d,g,m,'S','CURRENT')
        row=e['selected'][0]
        self.assertTrue(all(x['canonical_interface_kind']=='non_node_boundary' for x in row['canonical_endpoints']))
        self.assertTrue(all(x['unshown_plan_connector_length_mm'] is None for x in row['canonical_endpoints']))
        self.assertTrue(all(x['canonical_path_coordinate_kind']=='confirmed_detail_view_not_plan_metric_proof' for x in row['canonical_endpoints']))
        self.assertEqual(g,before)

    def test_all_groups_are_screened_before_selecting_to_protect_competing_owner(self):
        d,g,m=fixture(second=True);e=collect(d,g,m,'S','CURRENT')
        self.assertEqual(len(e['records']),2);self.assertEqual(e['selected'],[])
        self.assertTrue(all(r['status']=='multiple_pairs_claim_equipment_pending' for r in e['records']))

    def test_unlearned_spacing_is_preserved_pending(self):
        d,g,m=fixture();m['spacings']=[200];e=collect(d,g,m,'S','CURRENT')
        self.assertEqual(len(e['records']),1);self.assertEqual(e['selected'],[])
        self.assertEqual(e['records'][0]['status'],'archived_native_pair_not_unique_or_supported')

    def test_changed_answer_alias_roles_mixed_service_and_duplicate_pipe_rejected(self):
        for mode in ('answer','pair','alias','equipment','service','duplicate','source','archive-body'):
            d,g,m=fixture();root=g['confirmedSideviewCanonicalization'];row=root['records'][0]
            if mode=='answer':row['answer']['decision']='不是同一组'
            if mode=='pair':row['pair_sha256']='not-pinned'
            if mode=='alias':root['edge_aliases'][row['abbreviated_edge']]='OTHER'
            if mode=='equipment':next(n for n in g['nodes'] if n['node_id']==row['canonical_interface'])['node_type']='equipment'
            if mode=='service':next(x for x in g['edges'] if x['edge_id']==row['canonical_edge'])['system']='return'
            if mode=='duplicate':root['records'].append(copy.deepcopy(row))
            if mode=='source':root['source_sha256']='OTHER'
            if mode=='archive-body':root['representation_only_nodes'][0]['node_type']='equipment'
            with self.subTest(mode=mode),self.assertRaises((ValueError,KeyError)):collect(d,g,m,'S','CURRENT')

    def test_false_detail_T_and_body_proximity_cannot_create_ownership(self):
        d,g,m=fixture();row=g['confirmedSideviewCanonicalization']['records'][0]
        g['edges']=[e for e in g['edges'] if e['edge_id']!='MR-I-'+row['system']]
        with self.assertRaisesRegex(ValueError,'three incident'):collect(d,g,m,'S','CURRENT')

if __name__=='__main__':unittest.main()
