import copy,json,tempfile,unittest
from pathlib import Path
import test_native_projected_circle_main_role as original_fixtures
from received_projected_circle_authority import select_authority,collect,reader,replay_intake,sha,OLD_HOLD
from receive_current_review_answers import produce


class ReceivedAuthorityTests(unittest.TestCase):
    def fixture(self,root):
        doc,g,a=original_fixtures.ProjectedCircleTests().fixture();meta=g['nodes'][0]['expert_circle_evidence']
        (root/'pair.png').write_bytes(b'original-pair');(root/'overview.png').write_bytes(b'original-overview')
        source=dict(path='source.dxf',sha256='a'*64);graph=dict(path='graph.json',sha256='b'*64)
        evidence=dict(source=source,graph=graph,node_id='T',source_entities=[dict(handle=meta[k],type=kind)for k,kind in
            [('circle_handle','CIRCLE'),('main_handle','LINE'),('branch_handle','LINE')]])
        q=dict(id='Q',text='B支路是否接入A圆圈？',options=['是，接入该圆','不接入'],source_evidence=evidence)
        section=dict(title='原CAD大范围和Pair',questions=[q],image=dict(path='pair.png',sha256=sha(root/'pair.png')),
            contexts=[dict(title='原CAD大范围',path='overview.png',sha256=sha(root/'overview.png'),locators=[dict(label='A与B',bbox=[-1,11,-1,1])])])
        definitions=dict(schema='review',sections=[],followup_sections=[section])
        answer=dict(decision=q['options'][0],source_pair_sha256=section['image']['sha256'],updated_at='2026-11-13T03:13:26Z')
        record=dict(question_id='Q',question=q['text'],options=q['options'],source_evidence=evidence,explicit_answer=answer,pair_sha256=section['image']['sha256'])
        binding=dict(question_id='Q',node_id='T',expected_decision=q['options'][0],context_index=0,locator_index=0)
        return doc,g,definitions,record,binding,source,graph

    def select(self,root,fixture):
        doc,g,d,r,b,s,gs=fixture
        return select_authority(d,[r],b,s,gs,g,dict(path='intake.json',sha256='c'*64),root)

    def test_new_explicit_reply_uses_all_original_native_checks_without_extending_old_issue(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);f=self.fixture(root);doc,g,*_=f;before=copy.deepcopy(g)
            a=self.select(root,f);proof=collect(doc,g,'T','a'*64,'b'*64,{'T':a})
            self.assertEqual(proof['original_main_identity']['through'],['P','Q'])
            self.assertFalse(proof['branch_center_ray_fabricated']);self.assertIsNone(proof['physical_connector_length_mm'])
            self.assertFalse(proof['previous_issue_extent_expanded']);self.assertEqual(g,before)
            self.assertEqual(a['received_question_id'],'Q');self.assertFalse(a['original_expert_issue_rewritten'])

    def test_wrong_decision_graph_node_pair_and_locator_stay_blocked(self):
        for kind in('decision','graph','node','pair','extent','native-competitor'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory()as folder:
                root=Path(folder);f=list(self.fixture(root));doc,g,d,r,b,s,gs=f
                if kind=='decision':r['explicit_answer']['decision']='不接入'
                if kind=='graph':r=copy.deepcopy(r);r['source_evidence']['graph']['sha256']='x'*64;f[3]=r
                if kind=='node':b['node_id']='OTHER'
                if kind=='pair':(root/'pair.png').write_bytes(b'changed')
                if kind=='extent':d['followup_sections'][0]['contexts'][0]['locators'][0]['bbox']=[-1,11,5,7]
                if kind=='native-competitor':doc.modelspace().add_line((-5,0),(5,0),dxfattribs={'layer':doc.entitydb[g['nodes'][0]['expert_circle_evidence']['main_handle']].dxf.layer})
                with self.assertRaises(ValueError):
                    a=self.select(root,f);collect(doc,g,'T','a'*64,'b'*64,{'T':a})

    def test_reader_only_replaces_the_exact_old_extent_hold_for_the_named_node(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);f=self.fixture(root);doc,g,*_=f;a=self.select(root,f)
            def old(*args):raise ValueError(OLD_HOLD)
            self.assertEqual(reader(old,{'T':a})(doc,g,'T','a'*64,'b'*64)['received_source_authority']['received_question_id'],'Q')
            with self.assertRaisesRegex(ValueError,'outside'):reader(old,{'T':a})(doc,g,'OTHER','a'*64,'b'*64)
            def ambiguous(*args):raise ValueError('competing native LINE')
            with self.assertRaisesRegex(ValueError,'competing'):reader(ambiguous,{'T':a})(doc,g,'T','a'*64,'b'*64)

    def test_replay_actual_archived_browser_snapshot_and_detect_changed_reply(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);f=self.fixture(root);doc,g,definitions,record,*_=f
            reply=copy.deepcopy(definitions);reply['followup_sections'][0]['questions'][0]['answer']=record['explicit_answer']
            reply['browser_answer_snapshot']={'Q':record['explicit_answer']}
            a=root/'definitions.json';b=root/'reply.json';a.write_text(json.dumps(definitions),encoding='utf8');b.write_text(json.dumps(reply),encoding='utf8')
            output=root/'intake';produce(a,b,root,['Q'],output);spec=dict(path=str(output/'receipt.json'),sha256=sha(output/'receipt.json'))
            found,records=replay_intake(spec,root);self.assertEqual(found,definitions);self.assertEqual(records[0]['explicit_answer'],record['explicit_answer'])
            (output/'original-reply.json').write_text('{}',encoding='utf8')
            with self.assertRaises(ValueError):replay_intake(spec,root)


if __name__=='__main__':unittest.main()
