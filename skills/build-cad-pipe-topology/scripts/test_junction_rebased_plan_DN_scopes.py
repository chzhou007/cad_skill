import copy
import unittest

from junction_rebased_plan_DN_scopes import check_scope


class CurrentDNTopologyScopeTests(unittest.TestCase):
    def fixture(self):
        scope = dict(floor=2, branches=[dict(edge_id='B', tee='T', equipment_id='D', system='supply')], main_edges=['M'])
        group = dict(group_id='G', equipment_scope=['D'], floor=2, records=[
            dict(kind='equipment_branch', plan_edges=['B'], plan_start='T', equipment_id='D', system='supply'),
            dict(kind='main_between_equipment_branches', plan_edges=['M'], system='supply')])
        return dict(groups=[group]), scope

    def test_current_mapping_matches_exact_old_local_DN_roles(self):
        mapping, scope = self.fixture()
        self.assertEqual(check_scope(mapping, scope), 'G')

    def test_changed_owner_service_main_or_floor_blocks_scope_reuse(self):
        for field in ('equipment', 'system', 'main', 'floor'):
            mapping, scope = self.fixture()
            if field == 'equipment': scope['branches'][0]['equipment_id'] = 'OTHER'
            elif field == 'system': scope['branches'][0]['system'] = 'return'
            elif field == 'main': scope['main_edges'] = ['OTHER']
            else: scope['floor'] = 3
            with self.subTest(field=field), self.assertRaises(ValueError): check_scope(mapping, scope)

    def test_ambiguous_group_or_multiedge_scope_needs_explicit_reconciliation(self):
        mapping, scope = self.fixture()
        mapping['groups'].append(copy.deepcopy(mapping['groups'][0]))
        with self.assertRaises(ValueError): check_scope(mapping, scope)
        mapping, scope = self.fixture()
        mapping['groups'][0]['records'][0]['plan_edges'].append('EXTRA')
        with self.assertRaises(ValueError): check_scope(mapping, scope)


if __name__ == '__main__': unittest.main()
