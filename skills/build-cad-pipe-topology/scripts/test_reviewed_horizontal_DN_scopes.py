import copy,unittest,tempfile
from pathlib import Path
from confirm_crossview_paths import encode,sha
from reviewed_horizontal_DN_scopes import migrate_scopes,prepare


def fixture():
    graph=dict(edges=[dict(edge_id=s,start_node_id='D',end_node_id='T'+s,system=s,attribute_paths=[[[0,0],[1,0]]],source_handles=[s])for s in ('supply','return')])
    attrs=dict(equipment_scope=['D'],records=[dict(kind='equipment_branch',system=s,plan_edges=[s],diameter=dict(nominal_mm=150,scope_paths=[[[0,0],[1,0]]]))for s in ('supply','return')])
    return graph,attrs


class Tests(unittest.TestCase):
    def test_original_archive_string_hash_schema_is_checked_before_any_native_parent(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);paths={k:root/(k+'.json')for k in ['source','reviewed_graph','attributes','pair','overview','reply','definitions','receipt']}
            graph,attrs=fixture();paths['source'].write_bytes(b'native-source');paths['pair'].write_bytes(b'pair');paths['overview'].write_bytes(b'wide')
            graph['metadata']=dict(source_sha256=sha(paths['source']));paths['reviewed_graph'].write_bytes(encode(graph))
            attrs.update(source_sha256=sha(paths['source']),graph_sha256=sha(paths['reviewed_graph']));paths['attributes'].write_bytes(encode(attrs))
            evidence=dict(source_sha256=dict(plan=sha(paths['source'])),graph_sha256=dict(plan=sha(paths['reviewed_graph'])),
                plan_attribute_sha256=sha(paths['attributes']),pair_sha256=sha(paths['pair']),overview_sha256=sha(paths['overview']),equipment_ids=['D'])
            decision='平面已绘支路DN150，设备前另变DN80，区段见说明'
            q=dict(id='q',text='reviewed drawn plan and axis drop',options=[decision],source_evidence=evidence,
                answer=dict(decision=decision,source_pair_sha256=sha(paths['pair'])))
            image=dict(sha256=sha(paths['pair']));raw=dict(sections=[],followup_sections=[dict(image=image,questions=[q])])
            paths['reply'].write_bytes(encode(raw));paths['definitions'].write_bytes(encode(raw))
            paths['receipt'].write_bytes(encode(dict(input=dict(sha256=sha(paths['reply'])),records=[dict(question_id='q',explicit_answer=q['answer'],
                question=q['text'],options=q['options'],source_evidence=evidence,pair_sha256=image['sha256'])])))
            _,rows=prepare(graph,paths,'q',sha(paths['source']));self.assertEqual(len(rows),2)
            graph['metadata']['source_sha256']='changed'
            with self.assertRaises(ValueError):prepare(graph,paths,'q',sha(paths['source']))
    def test_review_follows_unchanged_paths_and_explicit_owner_but_is_not_a_seed_or_a_reducer(self):
        old,attrs=fixture();current=copy.deepcopy(old);current['edges'][0]['edge_id']='new-id';before=copy.deepcopy(current)
        r=migrate_scopes(old,current,attrs,['D'],150,80,'q')
        self.assertEqual(current,before);self.assertEqual(len(r),2)
        self.assertEqual(r[0]['edge_id'],'new-id');self.assertEqual(r[0]['historical_edge_id'],'supply')
        for row in r:
            self.assertTrue(row['scope_only']);self.assertEqual(row['nominal_mm'],150)
            self.assertEqual(row['separate_axis_equipment_drop_DN_mm'],80)
            self.assertIsNone(row['reducer_position']);self.assertFalse(row['whole_axis_value_selected'])
    def test_changed_owner_geometry_service_or_source_cannot_inherit_review(self):
        for key,value in [('end_node_id','other'),('system','other'),('source_handles',['other']),('attribute_paths',[[[0,0],[2,0]]])]:
            old,attrs=fixture();current=copy.deepcopy(old);current['edges'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):migrate_scopes(old,current,attrs,['D'],150,80,'q')
    def test_multiple_branches_or_changed_historical_DN_remain_unresolved(self):
        old,attrs=fixture();current=copy.deepcopy(old);current['edges'].append(dict(current['edges'][0],edge_id='copy'))
        with self.assertRaises(ValueError):migrate_scopes(old,current,attrs,['D'],150,80,'q')
        attrs['records'][0]['diameter']['nominal_mm']=80
        with self.assertRaises(ValueError):migrate_scopes(old,old,attrs,['D'],150,80,'q')


if __name__=='__main__':unittest.main()
