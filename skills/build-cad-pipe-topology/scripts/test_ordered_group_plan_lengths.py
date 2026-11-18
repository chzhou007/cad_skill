import copy,unittest
from unittest.mock import patch
import ezdxf
import ordered_group_plan_lengths as owner
from test_batch_native_main_chains import graph
from batch_native_path_coverage import collect
from match_source_checked_crossview_paths import selected_snapshot

def fixture():
    sh='a'*64;gh='b'*64;graphs=dict(plan=graph('P'),iso=graph('A'));docs={}
    for view,g in graphs.items():
        g['metadata']=dict(source_sha256=sh)
        for e in g['edges']:e.update(start_floor=1,end_floor=1)
        if view=='iso':
            for n in g['nodes']:n['x']*=100;n['y']*=100
            for e in g['edges']:e['attribute_paths']=[[[x*100,y*100]for x,y in p]for p in e['attribute_paths']]
        d=ezdxf.new();d.layers.new('空调冷冻水供水');d.modelspace().add_line((0,0),(30 if view=='plan'else 3000,0),dxfattribs=dict(layer='空调冷冻水供水'));docs[view]=d
    row=dict(mapping_id='GROUP',kind='native_main_chain_between_independent_junctions',floor=1,system='supply',plan_start='P0',plan_end='P3',iso_start='A0',iso_end='A3',
        plan_nodes=['P0','P1','P2','P3'],iso_nodes=['A0','A1','A2','A3'],plan_edges=['PE0','PE1','PE2'],iso_edges=['AE0','AE1','AE2'])
    for view in graphs:row[view+'_snapshot']=selected_snapshot(graphs[view],row[view+'_edges'])
    hashes={v:dict(source_sha256=sh,graph_sha256=gh,inventory_sha256='c'*64)for v in graphs};units=dict(plan_window=[-1,40,-1,20])
    anchors={('supply','P0'):'A0',('supply','P3'):'A3'}
    return docs,graphs,row,anchors,units,hashes

class Tests(unittest.TestCase):
    def allocate(self,args):
        docs,graphs,row,anchors,units,hashes=args
        def native(d,g,r,h):return dict(plan=dict(path_coverage=collect(d['plan'],g['plan'],r['plan_edges'],h['plan']['source_sha256'],h['plan']['graph_sha256'])))
        with patch.object(owner,'source_check',side_effect=native):return owner.allocate_group(docs,graphs,row,anchors,units,[],{},hashes,[0,45,135])
    def test_source_children_are_allocated_by_order_without_axis_ratios_or_group_total_copying(self):
        args=fixture();before=copy.deepcopy(args[1]);r=self.allocate(args)
        self.assertEqual([v['known_plan_pipe_XY_mm']for v in r['records']],[10,10,10]);self.assertEqual(r['known_plan_pipe_XY_total_mm'],30)
        self.assertEqual(r['complete_run_children'],3);self.assertEqual(r['partial_pipe_XY_children'],0);self.assertEqual(args[1],before)
        for row in r['records']:self.assertFalse(row['axis_drawn_lengths_or_ratios_used']);self.assertIsNone(row['physical_installed_length_mm'])
    def test_coherent_reversal_cannot_replace_independent_anchor_identities(self):
        a=list(fixture());r=a[2];r['iso_nodes'].reverse();r['iso_edges'].reverse();r['iso_start'],r['iso_end']=r['iso_end'],r['iso_start'];r['iso_snapshot']=selected_snapshot(a[1]['iso'],r['iso_edges'])
        with self.assertRaisesRegex(ValueError,'independent fixed anchors'):self.allocate(a)
    def test_branch_count_change_duplicate_native_line_and_floor_change_fail(self):
        for defect in('count','duplicate','floor'):
            a=list(fixture())
            if defect=='count':a[2]['iso_nodes'].pop(1)
            elif defect=='duplicate':a[0]['plan'].modelspace().add_line((0,0),(30,0),dxfattribs=dict(layer='空调冷冻水供水'))
            else:a[1]['iso']['edges'][0]['end_floor']=2
            with self.subTest(defect=defect),self.assertRaises(ValueError):self.allocate(a)
    def test_selected_group_cannot_supply_its_own_outer_anchor_proof(self):
        rows=[dict(mapping_id='SELF',system='supply',plan_start='P',plan_end='Q',iso_start='A',iso_end='B')]
        self.assertEqual(owner.independent_anchors(rows,{'SELF'}),({},{}))
        rows+=[dict(rows[0],mapping_id='OTHER'),dict(rows[0],mapping_id='CONFLICT',iso_start='BAD')]
        with self.assertRaisesRegex(ValueError,'anchors conflict'):owner.independent_anchors(rows,{'SELF'})
if __name__=='__main__':unittest.main()
