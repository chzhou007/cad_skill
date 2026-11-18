import copy,math,unittest
import test_native_nested_joint_evidence as nested_fixture
from reconstruct_native_block_branches import reconstruct,projected_coverage,collect_offsets,collect_joints,value_sha


def fixture(omission=False,mirror=False):
    doc,graph,inventory,circle,old_policy,hashes=nested_fixture.fixture(mirror)
    edge=graph['edges'][0];root=doc.entitydb[edge['source_insert_handle']];matrix=root.matrix44();block=doc.blocks[root.dxf.name]
    def xy(x,y):p=matrix.transform((x,y,0));return [p.x,p.y]
    for e in block:
        if e.dxftype()=='CIRCLE':e.dxf.layer='空调平面'
    tee=xy(40 if omission else 20,0);anchor=xy(31,1) if omission else xy(-15,0)
    if omission:
        block.add_line((30,0),(40,0),dxfattribs={'layer':'空调冷冻水供水'})
        for center in (20,30):
            block.add_lwpolyline([(x+center,y) for x,y in [(-2,-1),(0,0),(-1,2),(3,0),(2,1),(4,3)]],dxfattribs={'layer':'DIM_SYMB'})
        paths=[[tee,xy(30,0),anchor],[xy(20,0),xy(10,0)]]
    else:paths=[[tee,xy(10,0),anchor]]
    edge.update(start_node_id='T',end_node_id='D',attribute_paths=paths,path_points=copy.deepcopy(paths[0]),
        connection_mode='omission_pair_stitched_at_main_marker' if omission else 'direct_existing_cad_branch',
        path_length=sum(math.dist(a,b) for p in paths for a,b in zip(p,p[1:])),equipment_inventory=[dict(equipment_type='金属软接',count=1,device_names=['J'])])
    graph['nodes']=[dict(node_id='T',node_type='physical_junction',floor=1,x=tee[0],y=tee[1]),dict(node_id='D',node_type='equipment',floor=1,x=anchor[0],y=anchor[1])]
    doc.modelspace().add_text('D',dxfattribs={'insert':anchor})
    local_x=40 if omission else 20
    points=[xy(local_x,-10),xy(local_x,10)]
    doc.modelspace().add_line(*points,dxfattribs={'layer':'空调冷冻水供水'})
    for eid,nid,point in [('L','LEFT',points[0]),('R','RIGHT',points[1])]:
        graph['nodes'].append(dict(node_id=nid,node_type='virtual_equipment',floor=1,x=point[0],y=point[1]))
        graph['edges'].append(dict(edge_id=eid,start_node_id='T',end_node_id=nid,system='supply',attribute_paths=[[tee,point]]))
    policy=dict(source_sha256='S',graph_sha256='G',inventory_sha256='I',joint_block='HOSE',joint_fingerprint_sha256=old_policy['block_fingerprint_sha256'],edge_ids=['E'],expected_reconstructed_edges=1,expected_pending_edges=[])
    return doc,graph,inventory,policy,dict(source_sha256='S',graph_sha256='G',inventory_sha256='I')


class NativeBlockBranchTests(unittest.TestCase):
    def test_direct_and_omission_rebuild_with_mirror_and_native_conservation(self):
        for omission in (False,True):
            for mirror in (False,True):
                with self.subTest(omission=omission,mirror=mirror):
                    doc,g,inventory,policy,hashes=fixture(omission,mirror);before=copy.deepcopy(g);rows=copy.deepcopy(inventory)
                    result=reconstruct(doc,g,inventory,policy,hashes);edge=result['edges'][0]
                    self.assertEqual(g,before);self.assertEqual(inventory,rows);self.assertEqual(result['nodes'],before['nodes'])
                    self.assertEqual(edge['equipment_inventory'],before['edges'][0]['equipment_inventory']);self.assertEqual(edge['system'],'supply')
                    self.assertEqual(len(edge['attribute_paths']),3 if omission else 2)
                    self.assertAlmostEqual(edge['path_length'],30 if omission else 20)
                    self.assertFalse(edge['path_length_complete']);self.assertEqual(edge['physical_length'],'unknown')
                    proof=result['sourceNativeBlockBranchReconstruction']['records'][0]
                    self.assertFalse(proof['physical_port_verified']);self.assertFalse(proof['human_accepted']);self.assertEqual(bool(proof['omission']),omission)
                    self.assertTrue(all(s['status']=='single_source_line_covers' for p in proof['reconstructed_path_coverage'] for s in p['coverage']['segments']))

    def test_non_native_anchor_extra_marker_and_duplicate_source_do_not_pass(self):
        for variant in ('anchor','marker','duplicate','caption'):
            doc,g,inventory,policy,hashes=fixture(True);root=doc.entitydb[g['edges'][0]['source_insert_handle']]
            if variant=='anchor':g['nodes'][1]['x']+=2
            elif variant=='marker':doc.blocks[root.dxf.name].add_lwpolyline([(i,i%2) for i in range(6)],dxfattribs={'layer':'DIM_SYMB'})
            elif variant=='duplicate':doc.blocks[root.dxf.name].add_line((10,0),(20,0),dxfattribs={'layer':'空调冷冻水供水'})
            else:doc.modelspace().add_text('D')
            with self.assertRaisesRegex(ValueError,'scope differs'):reconstruct(doc,g,inventory,policy,hashes)

    def test_stale_policy_and_source_component_attribution_fail(self):
        doc,g,inventory,policy,hashes=fixture();policy['inventory_sha256']='other'
        with self.assertRaisesRegex(ValueError,'stale'):reconstruct(doc,g,inventory,policy,hashes)
        doc,g,inventory,policy,hashes=fixture();inventory[0]['edge_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'inventory mismatch'):reconstruct(doc,g,inventory,policy,hashes)

    def test_projection_hashes_and_original_path_indices_are_explicit(self):
        doc,g,inventory,policy,hashes=fixture(True);rows=projected_coverage(doc,g,'E','S')
        self.assertEqual([r['original_path_index'] for r in rows],[0,1])
        self.assertNotEqual(rows[0]['projection_graph_sha256'],rows[1]['projection_graph_sha256'])
        self.assertEqual(rows[1]['coverage']['unverified_drawing_length'],0)

    def test_old_attachment_migrates_to_history_only_for_affected_edges(self):
        doc,g,inventory,policy,hashes=fixture()
        g['sourceBlockEquipmentAttachment']=dict(status='old',mappings=[dict(edge_id='E'),dict(edge_id='L')]);g['edges'][0]['source_block_equipment_attachment']={'old':'snapshot'}
        result=reconstruct(doc,g,inventory,policy,hashes)
        self.assertEqual(result['sourceBlockEquipmentAttachmentHistory'],g['sourceBlockEquipmentAttachment'])
        self.assertEqual(result['sourceBlockEquipmentAttachment']['mappings'],[dict(edge_id='L')])
        self.assertNotIn('source_block_equipment_attachment',result['edges'][0])
        self.assertEqual(result['sourceNativeBlockBranchReconstruction']['records'][0]['original_edge']['source_block_equipment_attachment'],{'old':'snapshot'})

    def test_rebuilt_branch_inventory_requires_current_native_geometry(self):
        from crossview_equipment_branch_inventory import inspect_branch
        doc,g,inventory,policy,hashes=fixture(True);result=reconstruct(doc,g,inventory,policy,hashes)
        branch=inspect_branch(doc,result,'D','supply',hashes,'iso',inventory)
        self.assertTrue(branch['ready_for_mapping_comparison']);self.assertFalse(branch['physical_ports_verified'])
        self.assertIsNotNone(branch['omission_evidence'])
        result['edges'][0]['attribute_paths'][0][0][0]+=2
        branch=inspect_branch(doc,result,'D','supply',hashes,'iso',inventory)
        self.assertFalse(branch['ready_for_mapping_comparison'])

    def offset_fixture(self,mirror=False):
        doc,g,inventory,policy,hashes=fixture(True,mirror);root=doc.entitydb[g['edges'][0]['source_insert_handle']]
        circle=next(e for e in doc.blocks[root.dxf.name] if e.dxftype()=='CIRCLE');circle.dxf.center=(-10.1,0,0)
        screen=collect_offsets(doc,g,dict(hashes,edges=['E'],max_radius_ratio=.2),'S','G');c=screen['edges'][0]['candidates'][0]
        evidence=dict(status='source_geometry_candidates_only',source_sha256='S',graph_sha256='G',edges=[dict(edge_id='E',system='supply',source_insert_handle=root.dxf.handle,candidates=[dict(source_chain=c['source_line_chain'],circles=[dict(source_chain=c['source_circle_chain'],z_coincident=True,line_endpoint_index=c['endpoint_index'])])])])
        hh=dict(hashes,circle_sha256=value_sha(evidence))
        joint=collect_joints(doc,g,inventory,evidence,dict(hh,edges=['E'],joint_block='HOSE',block_fingerprint_sha256=policy['joint_fingerprint_sha256']),hh)
        policy['_verified_offset_controls']={'E':dict(offset_evidence=c,historical_joint_evidence=joint['edges'][0]['matches'][0],component_name='J',max_radius_ratio=.2,control_policy_sha256='P',control_audit_sha256='A')}
        return doc,g,inventory,policy,hashes,circle

    def test_inherited_offset_keeps_native_endpoint_and_does_not_measure_the_offset(self):
        for mirror in (False,True):
            doc,g,inventory,policy,hashes,circle=self.offset_fixture(mirror)
            original=copy.deepcopy(g);result=reconstruct(doc,g,inventory,policy,hashes)
            record=result['sourceNativeBlockBranchReconstruction']['records'][0]
            self.assertEqual(g,original);self.assertAlmostEqual(result['edges'][0]['path_length'],30)
            endpoint=record['offset_contact']['contact']['line_endpoint'][:2]
            self.assertEqual(result['edges'][0]['attribute_paths'][-1][-1],endpoint)
            self.assertGreater(math.dist(endpoint,record['offset_contact']['contact']['circle_center'][:2]),.05)
            self.assertIsNone(record['offset_contact']['physical_length_mm']);self.assertFalse(record['physical_port_verified'])

    def test_offset_needs_the_original_unique_chain_and_assignment(self):
        for variant in ('no_control','different_history','extra_circle','z_mismatch'):
            doc,g,inventory,policy,hashes,circle=self.offset_fixture()
            if variant=='no_control':policy.pop('_verified_offset_controls')
            elif variant=='different_history':policy['_verified_offset_controls']['E']['component_name']='OTHER'
            elif variant=='extra_circle':doc.blocks[doc.entitydb[g['edges'][0]['source_insert_handle']].dxf.name].add_circle((-10.15,0),1)
            else:circle.dxf.center=(-10.1,0,.1)
            with self.assertRaises(ValueError):reconstruct(doc,g,inventory,policy,hashes)


if __name__=='__main__':unittest.main()
