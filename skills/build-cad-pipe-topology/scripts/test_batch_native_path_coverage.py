import copy
import unittest
import ezdxf
from batch_native_path_coverage import collect


class Tests(unittest.TestCase):
    def test_multiple_path_fragments_are_read_without_certifying_the_gap(self):
        doc=ezdxf.new();layer='空调冷冻水供水';doc.layers.new(layer)
        for a,b in [((0,0),(10,0)),((20,0),(30,0))]:doc.modelspace().add_line(a,b,dxfattribs=dict(layer=layer))
        edge=dict(edge_id='E',system='supply',attribute_paths=[[[0,0],[10,0]],[[20,0],[30,0]]])
        graph=dict(edges=[edge]);before=copy.deepcopy(graph)
        out=collect(doc,graph,['E'],'S','G')
        self.assertEqual(graph,before);self.assertEqual(out['graph_sha256'],'G')
        self.assertEqual([s['path_index'] for s in out['edges'][0]['segments']],[0,1])
        self.assertTrue(all(s['status']=='single_source_line_covers' for s in out['edges'][0]['segments']))
        self.assertFalse(out['multi_path_continuity_or_whole_length_proved'])
        self.assertTrue(all(p['reading_projection_sha256']!='G' for p in out['edges'][0]['path_projections']))


if __name__=='__main__':unittest.main()
