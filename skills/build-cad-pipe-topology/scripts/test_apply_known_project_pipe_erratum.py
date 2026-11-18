import copy,unittest
import ezdxf
from apply_known_project_pipe_erratum import repair,csv_bytes


class KnownProjectErratumTests(unittest.TestCase):
    def fixture(self):
        doc=ezdxf.new();nodes=[];edges=[];pairs=[]
        for system,layer,y in [('supply','空调冷冻水供水',0),('return','空调冷冻水回水',500)]:
            for nid,x in [('A',-500),('U',0),('V',100),('B',600)]:nodes.append(dict(node_id=system+nid,node_type='virtual_equipment',subtype='unresolved_source_terminal',system=system,x=x,y=y,source_handles=[]))
            lines=[]
            for suffix,a,b in [('L',-500,0),('R',100,600)]:
                line=doc.modelspace().add_line((a,y),(b,y),dxfattribs={'layer':layer});lines.append(line.dxf.handle)
                edges.append(dict(edge_id=system+suffix,start_node_id=system+('A' if suffix=='L' else 'V'),end_node_id=system+('U' if suffix=='L' else 'B'),system=system,path=[[a,y],[b,y]],path_points=[[a,y],[b,y]],attribute_paths=[[[a,y],[b,y]]],source_handles=[line.dxf.handle],path_length=b-a,equipment_names=[],equipment_counts={}))
            circle=doc.modelspace().add_circle((100,y),100,dxfattribs={'layer':layer});pairs.append(dict(system=system,nodes=[system+'U',system+'V'],edges=[system+'L',system+'R'],lines=lines,circle=circle.dxf.handle))
        graph=dict(metadata={'source_sha256':'S'},nodes=nodes,edges=edges)
        issue=dict(sourceHashes={'main_dxf':'S'},issue=dict(id='ISSUE',note='explicit reviewed drawing erratum',nodes=[n for p in pairs for n in p['nodes']],edges=[e for p in pairs for e in p['edges']]))
        return doc,graph,[],issue,copy.deepcopy(graph),dict(source_sha256='S',project_scope='TEST',issue_id='ISSUE',pairs=pairs),'I'

    def test_only_explicit_disconnected_pairs_merge_without_measured_gap_or_cross_system_link(self):
        args=self.fixture();before=copy.deepcopy(args[1]);out,rows,audit=repair(*args)
        self.assertEqual(args[1],before);self.assertEqual(len(out['nodes']),4);self.assertEqual(len(out['edges']),2);self.assertFalse(out['metadata']['hil_ready'])
        self.assertEqual({e['system'] for e in out['edges']},{'supply','return'});self.assertEqual(rows,[])
        for e in out['edges']:
            self.assertEqual(e['path_length'],1000);self.assertFalse(e['path_length_complete']);self.assertEqual(e['physical_length'],'unknown');self.assertEqual(len(e['attribute_paths']),2)
        self.assertFalse(audit['general_circle_rule_added'])

    def test_changed_context_source_system_or_circle_cannot_be_repaired(self):
        for mode in ('context','source','system','circle','newDN'):
            a=list(self.fixture());g=a[1]
            if mode=='context':a[4]['edges'][0]['path'][0][0]-=1
            elif mode=='source':g['metadata']['source_sha256']='OTHER'
            elif mode=='system':g['edges'][0]['system']='return'
            elif mode=='circle':a[0].entitydb[a[5]['pairs'][0]['circle']].dxf.radius=90
            else:g['edges'][0]['pipe_diameter']={'nominal_mm':80}
            with self.assertRaises(ValueError):repair(*a)

    def test_component_csv_is_lossless_utf8_with_explicit_order(self):
        data=csv_bytes([{'id':'I','label':'球阀'}],['id','label']);self.assertTrue(data.startswith(b'\xef\xbb\xbf'));self.assertIn('球阀',data.decode('utf-8-sig'))


if __name__=='__main__':unittest.main()
