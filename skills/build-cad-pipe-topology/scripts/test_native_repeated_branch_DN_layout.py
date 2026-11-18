import copy,unittest
import ezdxf
from native_line_path_evidence import LAYERS
from native_repeated_branch_DN_layout import collect


def fixture():
    doc=ezdxf.new();b=doc.blocks.new('branch-template');m=doc.modelspace();g=dict(metadata=dict(source_sha256='S'),nodes=[],edges=[]);targets=[];roots=[]
    for system,x in [('supply',10),('return',30)]:b.add_line((x,0),(x,100),dxfattribs=dict(layer=LAYERS[system]))
    for i in range(5):
        root=m.add_blockref('branch-template',(200*i,0));roots.append(root.dxf.handle)
        for system,x in [('supply',10),('return',30)]:
            text=m.add_text('DN80',dxfattribs=dict(layer='AN',height=1,rotation=90,insert=(200*i+x-1,50)))
            eid=f'{system}{i}';ids=[eid+'A',eid+'B'];g['nodes'].extend(dict(node_id=nid,node_type='interface',x=200*i+x,y=y,floor=2) for nid,y in zip(ids,[0,100]))
            g['edges'].append(dict(edge_id=eid,start_node_id=ids[0],end_node_id=ids[1],system=system,source_insert_handle=root.dxf.handle,attribute_paths=[[[200*i+x,0],[200*i+x,100]]]))
            if i==4:
                targets.append(text.dxf.handle)
                m.add_line((200*i+x-1.1,0),(200*i+x-1.1,100),dxfattribs=dict(layer=LAYERS['return' if system=='supply' else 'supply']))
    return doc,g,targets,roots


class Tests(unittest.TestCase):
    def test_exact_native_layout_binds_two_services_despite_nearer_foreign_mains(self):
        doc,g,targets,_=fixture();before=copy.deepcopy(g);out=collect(doc,g,targets,'S','G');self.assertEqual(g,before)
        self.assertEqual(len(out['records']),2)
        for r in out['records']:
            self.assertEqual(len(r['independent_control_roots']),4);self.assertEqual(r['nominal_mm_candidate'],80)
            self.assertTrue(r['current_edge_id'].endswith('4'));self.assertTrue(r['rejected_competing_source_pipes'])
            self.assertFalse(r['whole_edge_DN_assigned']);self.assertFalse(set(targets)&set(r['independent_control_text_handles']))
    def test_insufficient_controls_shifted_text_wrong_profile_and_source_fail(self):
        for case in ['controls','offset','font','rotation','Z','source']:
            doc,g,targets,roots=fixture();source='S'
            if case=='controls':doc.modelspace().delete_entity(doc.entitydb[roots[0]])
            elif case=='offset':doc.entitydb[targets[0]].dxf.insert=(809.3,50,0)
            elif case=='font':doc.entitydb[targets[0]].dxf.height=1.1
            elif case=='rotation':doc.entitydb[targets[0]].dxf.rotation=0
            elif case=='Z':doc.entitydb[targets[0]].dxf.insert=(809,50,2)
            else:source='changed'
            with self.subTest(case=case),self.assertRaises(ValueError):collect(doc,g,targets,source,'G')
    def test_duplicate_current_pipe_owner_is_not_resolved_by_template(self):
        doc,g,targets,_=fixture();duplicate=copy.deepcopy(g['edges'][-2]);duplicate['edge_id']='other-current-owner';g['edges'].append(duplicate)
        with self.assertRaisesRegex(ValueError,'one source branch'):collect(doc,g,targets,'S','G')
    def test_targets_cannot_be_reused_as_controls_or_changed_into_F_leader_labels(self):
        doc,g,targets,_=fixture()
        with self.assertRaises(ValueError):collect(doc,g,targets+targets,'S','G')
        # Different nested root pose has no independent controls in that pose.
        target=doc.entitydb[g['edges'][-1]['source_insert_handle']];target.dxf.xscale=-1
        with self.assertRaises(ValueError):collect(doc,g,targets,'S','G')


if __name__=='__main__':unittest.main()
