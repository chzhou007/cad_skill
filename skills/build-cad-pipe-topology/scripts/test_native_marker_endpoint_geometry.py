import copy,unittest
from confirm_crossview_paths import encode
from test_inherited_marker_and_crossover_evidence import marker_scene
from inherited_marker_and_crossover_evidence import population,collect as old_owner
from native_marker_endpoint_geometry import collect,MODE

def held_companion(angle=0,mirror=False):
    doc,graph,marker=marker_scene(angle,mirror)
    bad=next(e for e in graph['edges']if e['system']=='supply');path=bad['attribute_paths'][0];root=next(n for n in graph['nodes']if n['node_id']==bad['start_node_id'])
    root['x']+=70;root['y']+=20
    # Preserve the real terminal LINE slice. The invented remote detour is
    # intentionally not source-covered and must never become full-path proof.
    mid=[(path[0][0]+path[1][0])/2,(path[0][1]+path[1][1])/2]
    bad['attribute_paths']=[[[root['x'],root['y']],mid,path[1],path[2]]]
    return doc,graph,marker

class MarkerEndpointGeometryTests(unittest.TestCase):
    def test_previous_complete_geometry_success_is_byte_exact(self):
        doc,g,_=marker_scene();pop=population(doc,'S')
        self.assertEqual(encode(collect(doc,g,'V','S','G',pop)),encode(old_owner(doc,g,'V','S','G',pop)))

    def test_bad_companion_path_does_not_hide_valid_independent_endpoint_geometry(self):
        for angle,mirror in[(0,False),(37,True),(90,False)]:
            doc,g,_=held_companion(angle,mirror);before=copy.deepcopy(g);pop=population(doc,'S')
            with self.assertRaises(ValueError):old_owner(doc,g,'V','S','G',pop)
            r=collect(doc,g,'V','S','G',pop)
            self.assertEqual(r['mode'],MODE);self.assertEqual(g,before);self.assertEqual(len(r['records']),2)
            self.assertFalse(r['full_original_branch_paths_qualified']);self.assertFalse(r['root_T_or_remote_equipment_qualified'])
            self.assertFalse(r['common_marker_creates_pipe_connection']);self.assertEqual(r['physical_nodes_created'],0)
            for row in r['records']:
                original=next(e for e in g['edges']if e['edge_id']==row['edge_id'])
                self.assertEqual(row['display_segment_index'],len(original['attribute_paths'][0])-2)
                self.assertNotIn('physical_segments',row);self.assertFalse(row['full_original_branch_path_qualified'])

    def test_complete_source_contact_census_and_native_tail_owners_still_block(self):
        for kind in('extra_marker','duplicate_tail','wrong_system','wrong_display','extra_port','source'):
            doc,g,marker=held_companion();node=next(n for n in g['nodes']if n['node_id']=='V')
            if kind=='extra_marker':doc.modelspace().add_lwpolyline(list(marker.get_points('xy')),dxfattribs={'layer':'DIM_SYMB'})
            elif kind=='duplicate_tail':
                line=list(doc.modelspace().query('LINE'))[0];doc.modelspace().add_entity(line.copy())
            elif kind=='wrong_system':node['ports'][0]['system']='return'
            elif kind=='wrong_display':g['edges'][0]['attribute_paths'][0][-1]=[0,0]
            elif kind=='extra_port':node['ports'].append(copy.deepcopy(node['ports'][0]))
            else:g['metadata']['source_sha256']='OTHER'
            with self.subTest(kind=kind),self.assertRaises(ValueError):collect(doc,g,'V','S','G',population(doc,'S'))

if __name__=='__main__':unittest.main()
