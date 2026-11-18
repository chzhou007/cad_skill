import copy,math,unittest
from reviewed_ring_partition_candidates import declared_candidates,add_candidate_partition_seeds
from test_reviewed_ring_main_partition import fixture
from projected_circle_plan_DN import infer
from current_junction_plan_DN import preserve_known


def policy_from(old):
    return dict(scope_id=old['scope_id'],upper_direction_WCS=old['upper_direction_WCS'],
        boundaries=[dict(system=system,**spec) for system,spec in old['systems'].items()])


class CandidateRingTests(unittest.TestCase):
    def test_alternatives_are_not_silently_reduced_to_the_last_number(self):
        for upper in ['200/250DN','DN200/250','200／250DN','DN200或DN250']:
            self.assertEqual(declared_candidates('上面承担1间，'+upper+'，下面承担2间，300DN'),
                dict(upper=[200,250],lower=[300]))
        self.assertEqual(declared_candidates('上面九个房间200DN，下面八个房间DN300'),dict(upper=[200],lower=[300]))
        with self.assertRaises(ValueError):declared_candidates('上面一个房间，下面两个房间')

    def test_native_evidence_selects_candidate_and_original_kernel_inherits(self):
        for angle in (0,.7,math.pi/2):
            for mirror in (1,-1):
                g,b,p,eligible,proofs=fixture(angle,mirror,branch_override=True)
                original=copy.deepcopy((g,b,p));policy=policy_from(p)
                seeds,selected,known=add_candidate_partition_seeds(g,b,policy,dict(upper=[200,250],lower=[300]),eligible)
                after=infer(g,seeds,eligible,proofs,'s','g');preserve_known(b,after['records']);rows={r['edge_id']:r for r in after['records']}
                self.assertEqual(rows['supply:UP']['nominal_mm'],200)
                self.assertEqual(rows['supply:BRANCH_U']['nominal_mm'],80)
                self.assertEqual(rows['return:LOW']['nominal_mm'],300)
                self.assertEqual(len(selected),4);self.assertFalse(known);self.assertEqual((g,b,p),original)

    def test_already_direct_lower_arm_is_preserved_and_not_reseeded(self):
        g,b,p,eligible,proofs=fixture()
        native_seeds=copy.deepcopy(b['direct_seed_evidence'])
        for system in ('supply','return'):
            native_seeds.append(dict(edge_id=system+':LOW',nominal_mm=300,evidence_id='native-lower-'+system))
        fresh=infer(g,native_seeds,eligible,proofs,'s','g');fresh.update(direct_seed_evidence=native_seeds,native_current_T_evidence=proofs)
        policy=policy_from(p)
        for boundary in policy['boundaries']:boundary['lower_edges']=[]
        seeds,selected,known=add_candidate_partition_seeds(g,fresh,policy,dict(upper=[200,250],lower=[300]),eligible)
        self.assertEqual(len(selected),2);self.assertEqual(len(known),2)
        self.assertTrue(all(r['direct'] for r in known))
        self.assertEqual(sum(s['edge_id']=='supply:LOW' for s in seeds),1)
        preserve_known(fresh,infer(g,seeds,eligible,proofs,'s','g')['records'])

    def test_ambiguous_local_choice_is_held_even_when_both_values_are_allowed(self):
        g,b,p,eligible,_=fixture();b['records'][next(i for i,r in enumerate(b['records']) if r['edge_id']=='supply:UP')]['lineage'].append(dict(nominal_mm=250,evidence=[]))
        with self.assertRaisesRegex(ValueError,'uniquely choose'):
            add_candidate_partition_seeds(g,b,policy_from(p),dict(upper=[200,250],lower=[300]),eligible)

    def test_wrong_side_third_arm_unreviewed_scope_and_extra_boundary_rejected(self):
        for kind in ('side','third_arm','unreviewed','duplicate','known_conflict'):
            g,b,p,eligible,_=fixture();policy=policy_from(p);allowed=set(eligible)
            if kind=='side':policy['upper_direction_WCS']=[0,-1]
            elif kind=='third_arm':policy['boundaries'][0]['upper_entry']='supply:FEED'
            elif kind=='unreviewed':allowed.remove('supply:UP')
            elif kind=='duplicate':policy['boundaries'].append(copy.deepcopy(policy['boundaries'][0]))
            else:
                row=next(r for r in b['records'] if r['edge_id']=='supply:LOW');row['nominal_mm']=450
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                add_candidate_partition_seeds(g,b,policy,dict(upper=[200,250],lower=[300]),allowed)


if __name__=='__main__':unittest.main()
