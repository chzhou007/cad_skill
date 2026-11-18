import copy
import unittest

from attach_block_equipment_attachments import attach
from test_verify_block_equipment_attachments import BlockAttachmentTest
from verify_block_equipment_attachments import verify


class AttachBlockEquipmentTest(unittest.TestCase):
 def fixture(self):
  doc, old, graph, joint = BlockAttachmentTest().fixture()
  for edge in graph['edges']:
   edge.update(physical_length='unknown', path_length_complete=False)
  report = verify(doc, old, graph, joint, 'S', 'OLD', 'NEW')
  return graph, report

 def test_adds_scoped_evidence_without_changing_connectivity(self):
  graph, report = self.fixture(); before = copy.deepcopy(graph)
  result = attach(graph, report, 'S', 'NEW', 'REPORT')
  self.assertEqual(graph, before)
  self.assertEqual(len(result['sourceBlockEquipmentAttachment']['mappings']), 2)
  self.assertFalse(result['metadata']['hil_ready'])
  for original, edge in zip(graph['edges'], result['edges']):
   evidence = edge.pop('source_block_equipment_attachment')
   self.assertEqual(edge, original)
   self.assertFalse(evidence['physical_port_verified'])
   self.assertFalse(evidence['human_accepted'])
   self.assertEqual(evidence['physical_length'], 'unknown')

 def test_rejects_stale_or_mismatched_source_and_lengths(self):
  graph, report = self.fixture()
  with self.assertRaises(ValueError): attach(graph, report, 'OTHER', 'NEW', 'REPORT')
  graph['edges'][0]['source_device_extension']['source_circle_chain'][1] = 'OTHER'
  with self.assertRaises(ValueError): attach(graph, report, 'S', 'NEW', 'REPORT')
  graph, report = self.fixture(); graph['edges'][0]['path_length_complete'] = True
  with self.assertRaises(ValueError): attach(graph, report, 'S', 'NEW', 'REPORT')


if __name__ == '__main__': unittest.main()
