import copy,unittest
from match_network_named_lower_approaches import select_structure,check_through_neighbours,MAIN_MODE,COLUMN_MODE

def fixture(mirror=False):
    graphs={v:dict(nodes=[],edges=[]) for v in ('plan','iso')};names=[];columns=[];contracts=[];node_map={};mains=[]
    for system,identifier,suffix in [('supply','CHWS1','S'),('return','CHWR1','R')]:
        pn='P'+suffix;rif='RIF'+suffix;an='A'+suffix;middle='M'+suffix;pe='PAPP'+suffix;ae='IAPP'+suffix
        x=-10 if mirror else 10;points=[[0,0],[x,0],[x,100]]
        graphs['plan']['nodes'] += [dict(node_id=pn,floor=1),dict(node_id=rif,floor=1)]
        graphs['plan']['edges'].append(dict(edge_id=pe,start_node_id=pn,end_node_id=rif,system=system,attribute_paths=[[[0,0],[-30,0]]]))
        graphs['iso']['nodes'] += [dict(node_id=an,floor=1),dict(node_id=middle,floor=2)]
        graphs['iso']['edges'].append(dict(edge_id=ae,start_node_id=an,end_node_id=middle,system=system,attribute_paths=[points]))
        names.append(dict(identifier=identifier,system=system,target_kind='plan_riser_circle',target=dict(node_id=rif,floor=1)))
        columns.append(dict(identifier=identifier,system=system,floor=2,iso_riser_junction=middle));node_map[pn]=an
        segment=dict(side='lower',edge_id=ae,segment_index=1,floor_pair=[1,2],source_line_handle='LINE'+suffix,scope_points=points[1:])
        contracts.append(dict(corridor_id=identifier,system=system,middle_T=middle,through_source_LINE='LINE'+suffix,segments=[segment]))
        mains.append(dict(mapping_id='MAIN'+suffix,plan_edges=['PMAIN'+suffix],iso_edges=['IMAIN'+suffix],system=system))
    main=dict(mode=MAIN_MODE,floor=1,iso_graph_sha256='G',source_sha256=dict(iso='S'),evidence=dict(structure=dict(node_mapping=node_map)),records=mains)
    named=dict(mode=COLUMN_MODE,graph_sha256=dict(iso='G'),source_sha256=dict(iso='S'),records=columns)
    riser=dict(graph_sha256='G',source_sha256='S',through_contracts=contracts)
    return graphs,main,named,riser,dict(records=names),['CHWS1','CHWR1']

class Tests(unittest.TestCase):
    def test_two_named_prefixes_retain_exact_vertical_boundary_and_no_values(self):
        for mirrored in (False,True):
            args=fixture(mirrored);before=copy.deepcopy(args);rows=select_structure(*args)
            self.assertEqual(args,before);self.assertEqual(len(rows),2)
            for r in rows:
                scope=r['iso_segment_scopes'][0];self.assertEqual(scope['segment_indices'],[0]);self.assertFalse(scope['whole_local_edge'])
                self.assertEqual(scope['scope_paths'][0][-1],r['retained_vertical_scope']['scope_points'][0]);self.assertIsNone(r['physical_length_mm']);self.assertFalse(r['whole_axis_DN_assigned']);self.assertFalse(r['human_accepted'])
    def test_unknown_network_T_duplicate_names_wrong_column_floor_and_vertical_guard(self):
        for case in ('unknown_T','duplicate','floor','service','column','segment','plumb','source'):
            graphs,main,named,riser,names,ids=fixture()
            if case=='unknown_T':main['evidence']['structure']['node_mapping'].pop('PS')
            elif case=='duplicate':names['records'].append(copy.deepcopy(names['records'][0]))
            elif case=='floor':named['records'][0]['floor']=3
            elif case=='service':named['records'][0]['system']='return'
            elif case=='column':riser['through_contracts'][0]['middle_T']='other'
            elif case=='segment':riser['through_contracts'][0]['segments'][0]['segment_index']=0
            elif case=='plumb':graphs['iso']['edges'][0]['attribute_paths'][0][1][0]=0
            else:named['source_sha256']['iso']='old'
            with self.subTest(case=case),self.assertRaises(ValueError):select_structure(graphs,main,named,riser,names,ids)
    def test_adjoining_main_is_an_independent_anchor_and_off_branch_mode_is_not_relaxed(self):
        args=fixture();row=select_structure(*args)[0]
        roles=dict(plan=dict(through_edges=['PAPPS','PMAINS'],off_edge='PFEED'),iso=dict(through_edges=['IAPPS','IMAINS'],off_edge='IFEED'))
        self.assertEqual(check_through_neighbours(row,roles,args[1]),'MAINS')
        wrong=copy.deepcopy(roles);wrong['plan']['off_edge']='PAPPS'
        with self.assertRaisesRegex(ValueError,'through approach'):check_through_neighbours(row,wrong,args[1])
        wrong=copy.deepcopy(roles);wrong['iso']['through_edges'][1]='OTHER'
        with self.assertRaisesRegex(ValueError,'adjoining main'):check_through_neighbours(row,wrong,args[1])
if __name__=='__main__':unittest.main()
