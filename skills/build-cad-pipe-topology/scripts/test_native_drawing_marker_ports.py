import copy,unittest
from native_drawing_marker_ports import collect
from test_native_external_port_destination import fixture as original_fixture

def fixture(angle=0):
    result=original_fixture(angle)
    for edge in result[1]['edges']:edge['connection_mode']='standalone_omission_to_first_tee'
    return result

class Tests(unittest.TestCase):
    def test_separate_native_geometry_through_rotations_without_remote_identity_or_centre_length(self):
        for angle in(0,90,180,270):
            doc,graph,policy,sh,gh=fixture(angle);graph['metadata']=dict(source_sha256=sh);before=copy.deepcopy(graph)
            result=collect(doc,graph,policy['node_id'],sh,gh)
            self.assertEqual(len(result['records']),4);self.assertFalse(result['common_marker_creates_pipe_connection']);self.assertFalse(result['remote_destination_or_cap_role_assigned']);self.assertEqual(graph,before)
            self.assertTrue(all(not row['physical_port_verified']and row['physical_length_mm']is None for row in result['records']))
    def test_changed_geometry_system_extra_pipe_and_wrong_source_fail(self):
        for defect in('path','source','port','extra'):
            doc,graph,p,sh,gh=fixture();graph['metadata']=dict(source_sha256=sh)
            if defect=='path':graph['edges'][0]['attribute_paths'][0][-1]=[999,999]
            elif defect=='source':graph['metadata']['source_sha256']='changed'
            elif defect=='port':next(n for n in graph['nodes']if n['node_id']==p['node_id'])['ports'][0]['system']='wrong'
            else:doc.modelspace().add_line((80,40),(80,0),dxfattribs=dict(layer='空调冷冻水供水'))
            with self.subTest(defect=defect),self.assertRaises(ValueError):collect(doc,graph,p['node_id'],sh,gh)
if __name__=='__main__':unittest.main()
