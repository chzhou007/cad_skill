import copy,unittest
from test_screen_applied_near_tees import AppliedNearTeesTest
from screen_applied_near_tees import screen
from attach_applied_near_tee_state import attach
from confirm_normalized_near_tees import confirm,DECISION


class ConfirmNearTeeTest(unittest.TestCase):
    def fixture(self):
        f=AppliedNearTeesTest();f.setUp();g=attach(f.g,screen(f.d,f.g,f.a,f.p,f.h),'S','G')
        policy=copy.deepcopy(f.p);policy.update(reply_sha256='REPLY',pair_sha256='PAIR')
        spec=policy['selections'][0];spec['question_id']='Q'
        q=dict(id='Q',text=spec['branch_handle']+' 接入 '+spec['main_handle']+' ?',answer={'decision':DECISION})
        reply=dict(sections=[dict(image={'sha256':'PAIR'},questions=[q])])
        return f,g,policy,reply
    def test_only_selected_pending_semantics_change_geometry_and_other_issues_survive(self):
        f,g,p,r=self.fixture();g['preHilComparison']['families'].append(dict(id='other-family',status='algorithm_pending'))
        old=copy.deepcopy(g);out,records=confirm(f.d,g,f.a,p,r,f.h)
        self.assertEqual(g,old);self.assertEqual(g['edges'],out['edges'])
        self.assertEqual(out['nodes'][0]['resolution_state'],'source_contact_reconstructed_user_confirmed')
        self.assertFalse(out['nodes'][0]['review_required']);self.assertFalse(out['metadata']['hil_ready'])
        states={x['id']:x['status'] for x in out['preHilComparison']['families']}
        self.assertEqual(states['normalized-near-tee'],'resolved');self.assertEqual(states['other-family'],'algorithm_pending')
        self.assertEqual(records[0]['branch_handle'],f.branch.dxf.handle)
    def test_partial_answer_other_image_or_rebound_source_cannot_close(self):
        for field in ('answer','image','source'):
            f,g,p,r=self.fixture()
            if field=='answer':r['sections'][0]['questions'][0]['answer']['decision']='部分连接，见说明'
            elif field=='image':r['sections'][0]['image']['sha256']='OTHER'
            else:g['nodes'][0]['source_near_tee_evidence']['branch_handle']='OTHER'
            with self.assertRaises(ValueError):confirm(f.d,g,f.a,p,r,f.h)
    def test_changed_incidence_requires_new_reconstruction_not_status_edit(self):
        f,g,p,r=self.fixture();g['edges'][0]['system']='return'
        with self.assertRaises(ValueError):confirm(f.d,g,f.a,p,r,f.h)


if __name__=='__main__':unittest.main()
