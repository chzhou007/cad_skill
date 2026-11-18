import copy,unittest
import test_native_paired_junction_correspondence as fixtures
from native_paired_junction_correspondence import collect
from paired_plan_DN_scopes import topology_contract
from refine_paired_service_path_correspondence import MODE as MAPPING_MODE
from refined_paired_plan_DN_scopes import extension_contracts,recompute_groups,implementation_hashes
from checked_plan_DN_scope_attributes import attribute_checked_scope
from pipe_annotation_attributes import source_texts
from source_direct_dn_evidence import collect as direct_collect
from native_line_path_evidence import _on,LAYERS


def fixture():
    docs,graphs,mapping,hashes=fixtures.fixture();doc=docs['plan'];g=graphs['plan'];g['metadata']=dict(source_sha256='S');m=doc.modelspace();settings={}
    for edge in g['edges']:
        edge['source_handles']=[line.dxf.handle for line in m.query('LINE') if line.dxf.layer==LAYERS[edge['system']]
            and any(_on(a,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05) and _on(b,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)
                for path in edge['attribute_paths'] for a,b in zip(path,path[1:]))]
    for pid in ('P01','P02'):settings[pid]=dict(seeds=[])
    for system,y in [('supply',0),('return',-30)]:
        for pid,eid,point,pos,angle,value in [
                ('P01',system+'M0',(-5,y),(-5,y+.4),0,300),
                ('P02',system+'C1',(10,y-25),(10.4,y-25),90,200)]:
            text=m.add_text('DN'+str(value),dxfattribs=dict(layer='AN',height=.3,rotation=angle,insert=pos))
            line=next(e for e in m.query('LINE') if e.dxf.layer==('空调冷冻水供水' if system=='supply' else '空调冷冻水回水')
                and min(e.dxf.start.x,e.dxf.end.x)-.01<=point[0]<=max(e.dxf.start.x,e.dxf.end.x)+.01
                and min(e.dxf.start.y,e.dxf.end.y)-.01<=point[1]<=max(e.dxf.start.y,e.dxf.end.y)+.01)
            settings[pid]['seeds'].append(dict(edge_id=eid,text_handle=text.dxf.handle,source_line_handle=line.dxf.handle,expected_text=text.plain_text()))
    texts=source_texts(doc,'source','S');groups=[]
    for pair in mapping['evidence']['paired_services']:
        contract=topology_contract(doc,g,pair,'S','G',2);pid=pair['pair_id']
        spec=dict(group_id=pid,floor=2,main_edges=contract['main_edges'],branches=contract['branches'],seeds=settings[pid]['seeds'],line_F_frames=[])
        out=attribute_checked_scope(doc,g,spec,texts,'S','G',set(),junctions=contract['junctions'],verified_taps=contract['verified_taps'],branch_frontier_edges=contract['branch_frontier_edges'])
        out['paired_topology_contract']=contract;groups.append(out)
    base=dict(source_sha256='S',graph_sha256='G',groups=groups,records=[r for gr in groups for r in gr['records']])
    proof=collect(docs,graphs,mapping,hashes);records=[]
    for row in proof['records']:
        for match in row['matches']:
            view=match['views']['plan'];records.append(dict(kind='main_between_matched_junctions',system=row['system'],
                parent_pair_id=row['parent_pair_id'],target_pair_id=match['target_pair_id'],target_equipment_id=match['target_equipment_id'],
                plan_edges=view['route']['edges'],plan_start=view['route']['start'],plan_end=view['route']['end'],
                junction_correspondence_ids=[match['junction_mapping_id']],decision_basis='native_offcorridor_branch_to_first_independently_checked_equipment_T'))
    refined=dict(mode=MAPPING_MODE,floor=2,local_graphs_mutated=False,physical_values_fused=False,human_accepted=False,
        records=records,evidence=dict(native_junction_correspondence=proof))
    return doc,g,base,refined,settings,texts


class RefinedPairedDNTests(unittest.TestCase):
    def test_through_target_200_extends_link_without_backflow_into_parent_300(self):
        doc,g,base,mapping,settings,texts=fixture();before=copy.deepcopy((g,base,mapping));groups,promotions=recompute_groups(doc,g,base,mapping,settings,texts,set(),direct_collect)
        self.assertEqual((g,base,mapping),before);self.assertEqual(len(promotions),2)
        rows={r['edge_id']:r for gr in groups for r in gr['records']}
        for system in ('supply','return'):
            self.assertEqual(rows[system+'X']['nominal_mm'],200)
            self.assertEqual(rows[system+'M1']['nominal_mm'],300);self.assertEqual(rows[system+'M2']['nominal_mm'],300)
            self.assertTrue(all(system in ev['edge_path'][0] for c in rows[system+'X']['lineage'] for ev in c['evidence']))
        for old in base['records']:self.assertEqual(rows[old['edge_id']],old)
        self.assertTrue(all(p['parent_non_through_frontier_retained'] and not p['physical_length_assigned'] for p in promotions))
    def test_whole_source_link_requires_both_existing_roles_and_complete_frontier(self):
        for case in ('parent_branch','target_through','partial','floor','coverage','witness','review','duplicate'):
            doc,g,base,mapping,settings,texts=fixture()
            if case=='parent_branch':base['groups'][0]['paired_topology_contract']['branch_frontier_edges']=[]
            elif case=='target_through':base['groups'][1]['paired_topology_contract']['junctions']['supplyX']['junctions'][0]['source_rays'][0]['source_line_handle']='WRONG'
            elif case=='partial':next(f for f in base['groups'][1]['frontier_fragments'] if f['edge_id']=='supplyX')['projected_source_path'][-1]=[10,-1]
            elif case=='floor':next(n for n in g['nodes'] if n['node_id']=='supplyI')['floor']=3
            elif case=='review':next(n for n in g['nodes'] if n['node_id']=='supplyI')['review_required']=True
            elif case=='coverage':mapping['evidence']['native_junction_correspondence']['records'][0]['matches'][0]['views']['plan']['coverage']['edges'][0]['segments'][0]['status']='unverified'
            elif case=='witness':mapping['records'][0]['target_equipment_id']='D3'
            else:mapping['records'].append(copy.deepcopy(mapping['records'][0]))
            with self.subTest(case=case),self.assertRaises(ValueError):extension_contracts(g,base,mapping)
    def test_new_direct_change_label_conflicting_with_prior_scope_requires_rebuild(self):
        doc,g,base,mapping,settings,texts=fixture();doc.modelspace().add_text('DN125',dxfattribs=dict(layer='AN',height=.3,rotation=90,insert=(10.4,-5)))
        before=copy.deepcopy(g)
        with self.assertRaisesRegex(ValueError,'previously checked'):recompute_groups(doc,g,base,mapping,settings,source_texts(doc,'source','S'),set(),direct_collect)
        self.assertEqual(g,before)
    def test_compound_annotation_on_new_link_blocks_instead_of_inventing_DN(self):
        doc,g,base,mapping,settings,texts=fixture();doc.modelspace().add_text('DN125/DN100',dxfattribs=dict(layer='AN',height=.3,rotation=90,insert=(10.4,-5)))
        with self.assertRaises(ValueError):recompute_groups(doc,g,base,mapping,settings,source_texts(doc,'source','S'),set(),direct_collect)
    def test_implementation_hash_closure_includes_new_and_inherited_kernels(self):
        hashes=implementation_hashes();self.assertIn('checked_plan_DN_scope_attributes.py',hashes);self.assertIn('refine_paired_service_path_correspondence.py',hashes)


if __name__=='__main__':unittest.main()
