import copy,unittest
from test_native_plan_projection_lengths import fixture
from native_plan_projection_lengths import unit_evidence,lengths

class SideviewMetricDomainTests(unittest.TestCase):
    def test_real_floor_plan_keeps_old_source_witnessed_projection(self):
        doc,g,policy,coverage,_=fixture();before=copy.deepcopy(g)
        self.assertEqual(lengths(g,coverage,dict(plan_edges=['P'],system='supply'),unit_evidence(doc,policy))['value_mm'],800)
        self.assertEqual(g,before)

    def test_detail_units_or_asserted_metric_flag_cannot_manufacture_physical_length(self):
        for role in [dict(kind='confirmed_detail_view',coordinate_domain='native_detail_drawing',metric_verified_by_this_stage=False),dict(kind='confirmed_detail_view',metric_verified_by_this_stage=True),{}]:
            doc,g,policy,coverage,_=fixture();g['edges'][0]['source_view_context']=role;before=copy.deepcopy(g)
            with self.subTest(role=role),self.assertRaisesRegex(ValueError,'separately verified'):lengths(g,coverage,dict(plan_edges=['P'],system='supply'),unit_evidence(doc,policy))
            self.assertEqual(g,before)

if __name__=='__main__':unittest.main()
