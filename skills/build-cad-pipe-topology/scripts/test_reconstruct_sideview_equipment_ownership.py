import copy,unittest,subprocess,sys,os
from test_source_sideview_equipment_owner_evidence import fixture
from source_sideview_equipment_owner_evidence import collect
from reconstruct_sideview_equipment_ownership import apply

def case(boundary=False,second=False):
    doc,graph,model=fixture(boundary=boundary,second=second)
    for edge in graph['edges']:edge.update(start_floor=1,end_floor=1,path_length_scope='historical_native_paths_only',physical_length_status='unknown_omitted_length',physical_length='unknown',path_length_complete=False)
    return doc,graph,collect(doc,graph,model,'S','CURRENT')

POLICY=dict(expected_equipment_bindings=1,equipment_ids=['EQ'])

class SideviewOwnerReconstructionTests(unittest.TestCase):
    def test_source_alias_node_endpoints_bind_to_real_equipment_and_preserve_paths(self):
        doc,g,e=case();before=copy.deepcopy(g);out,audit=apply(g,e,POLICY,'S','CURRENT')
        self.assertEqual(g,before);self.assertEqual(len(out['edges']),len(g['edges']));self.assertEqual(len(audit['records']),2)
        oldedges={x['edge_id']:x for x in g['edges']};owners=[]
        for edge in out['edges']:
            for key in ('path','attribute_paths','path_length','source_handles','equipment_names','equipment_counts','path_length_scope','physical_length_status'):self.assertEqual(edge.get(key),oldedges[edge['edge_id']].get(key))
            if 'source_sideview_equipment_interface' in edge:
                owners.append(edge['end_node_id']);self.assertIsNone(edge['equipment_connector_length_mm']);self.assertFalse(edge['path_length_complete'])
                self.assertEqual(edge['source_view_context']['coordinate_domain'],'native_detail_drawing')
        self.assertEqual(owners,['EQ','EQ']);self.assertEqual({n['node_id'] for n in out['nodes'] if n['node_type']=='equipment'},{'EQ'})
        self.assertEqual(len(out['sourceSideviewEquipmentOwnership']['retired_interface_nodes']),2);self.assertFalse(out['metadata']['hil_ready'])
        self.assertEqual(out['confirmedSideviewCanonicalization'],g['confirmedSideviewCanonicalization'])

    def test_non_node_boundaries_are_archived_as_symbols_not_created_as_physical_ports(self):
        doc,g,e=case(boundary=True);out,a=apply(g,e,POLICY,'S','CURRENT');root=out['sourceSideviewEquipmentOwnership']
        self.assertEqual(out['boundary_anchors'],[]);self.assertEqual(len(root['retired_boundary_anchors']),2);self.assertEqual(root['retired_interface_nodes'],[])
        self.assertEqual(len(out['nodes']),len(g['nodes']));self.assertEqual(len(out['virtual_equipment_ports']),len(g['virtual_equipment_ports']))
        self.assertTrue(all(r['original_canonical_interface_kind']=='non_node_boundary' and r['physical_port_verified'] is False for r in a['records']))
        for edge in out['edges']:
            if 'source_sideview_equipment_interface' in edge:self.assertNotIn('end_boundary_id',edge);self.assertEqual(edge['end_node_id'],'EQ')

    def test_competing_groups_cannot_be_cherry_picked_by_policy(self):
        doc,g,e=case(second=True)
        self.assertEqual(e['selected'],[])
        with self.assertRaisesRegex(ValueError,'complete supported'):apply(g,e,POLICY,'S','CURRENT')

    def test_legacy_boundary_floor_is_an_explicit_source_not_an_assumed_floor(self):
        doc,g,e=case(boundary=True)
        for a in g['boundary_anchors']:
            a['legacy_node']=dict(node_id='retired-'+a['boundary_id'],floor=a.pop('floor'))
        out,audit=apply(g,e,POLICY,'S','CURRENT')
        self.assertTrue(all(r['endpoint_floor_evidence']['source']=='preserved_boundary_legacy_node' for r in audit['records']))
        g['boundary_anchors'][0]['legacy_node'].pop('floor')
        with self.assertRaisesRegex(ValueError,'floor differs'):apply(g,e,POLICY,'S','CURRENT')
        g['boundary_anchors'][0]['floor']=2;g['boundary_anchors'][0]['legacy_node']['floor']=1
        with self.assertRaisesRegex(ValueError,'floor evidence conflicts'):apply(g,e,POLICY,'S','CURRENT')

    def test_measured_length_existing_owner_stale_alias_and_wrong_scope_reject(self):
        for mode in ('length','connected','alias','source','count','moved-body','missing-floor'):
            doc,g,e=case();p=copy.deepcopy(POLICY);branch=next(x for x in g['edges'] if x['edge_id']==e['selected'][0]['canonical_endpoints'][0]['canonical_edge'])
            if mode=='length':branch['physical_length']=0
            if mode=='connected':branch['confirmed_equipment_interface']={'prior':True}
            if mode=='alias':g['confirmedSideviewCanonicalization']['node_aliases']['another']='D'
            if mode=='source':e['source_sha256']='OTHER'
            if mode=='count':p['equipment_ids']=['another']
            if mode=='moved-body':next(n for n in g['nodes'] if n['node_id']=='EQ')['x']+=20
            if mode=='missing-floor':next(n for n in g['nodes'] if n['node_id']=='EQ').pop('floor')
            with self.subTest(mode=mode),self.assertRaises(ValueError):apply(g,e,p,'S','CURRENT')

    def test_second_application_and_physical_equipment_retirement_are_rejected(self):
        doc,g,e=case();out,_=apply(g,e,POLICY,'S','CURRENT')
        with self.assertRaises(ValueError):apply(out,e,POLICY,'S','CURRENT')
        node=next(n for n in g['nodes'] if n['node_id']==e['selected'][0]['canonical_endpoints'][0]['canonical_interface']);node['node_type']='equipment'
        with self.assertRaises(ValueError):apply(g,e,POLICY,'S','CURRENT')

    def test_deterministic_root_and_aliases_across_hash_seeds(self):
        command="from test_reconstruct_sideview_equipment_ownership import case,POLICY; from reconstruct_sideview_equipment_ownership import apply; from confirm_crossview_paths import encode; import hashlib; d,g,e=case(boundary=True); print(hashlib.sha256(encode(apply(g,e,POLICY,'S','CURRENT')[0])).hexdigest())"
        results=[subprocess.check_output([sys.executable,'-X','utf8','-c',command],text=True,env=dict(os.environ,PYTHONHASHSEED=str(seed))).strip() for seed in (1,2,3)]
        self.assertEqual(len(set(results)),1)

if __name__=='__main__':unittest.main()
