import copy,math,unittest
from test_canonicalize_confirmed_sideviews import fixture
from canonicalize_confirmed_sideviews import canonical_detail_branch
from native_local_detail_T_evidence import collect
from source_main_DN_continuity import infer

def case(boundary=False,angle=0,mirror=1):
    doc,g,_,_=fixture();g['edges']=[e for e in g['edges']if e['edge_id']!='UP']
    g['nodes']=[n for n in g['nodes']if n['node_id']in ('A','B','D','T')]
    g['edges'][0]=canonical_detail_branch(doc,g,g['edges'][0])
    if boundary:
        leaf=next(n for n in g['nodes']if n['node_id']=='D');g['nodes'].remove(leaf)
        g['boundary_anchors']=[dict(boundary_id='BOUNDARY',system='supply',x=leaf['x'],y=leaf['y'])]
        g['edges'][0].update(end_node_id=None,end_boundary_id='BOUNDARY')
    if angle or mirror!=1:
        from ezdxf.math import Matrix44
        matrix=Matrix44.scale(mirror,1,1)@Matrix44.z_rotate(angle)
        def xy(p):return list(matrix.transform(p))[:2]
        for entity in list(doc.modelspace()):
            if entity.dxftype()in ('LINE','CIRCLE'):entity.transform(matrix)
        for n in g['nodes']+g.get('boundary_anchors',[]):n['x'],n['y']=xy([n['x'],n['y']])
        for edge in g['edges']:
            edge['path']=[xy(p)for p in edge['path']];edge['attribute_paths']=[[xy(p)for p in path]for path in edge['attribute_paths']]
            proof=edge.get('source_detail_circle_length_evidence')
            if proof:
                for key in ('circle_center','line_contact'):proof[key]=xy(proof[key])
    return doc,g

class Tests(unittest.TestCase):
    def test_complete_DN_entry_uses_unowned_detail_T_and_preserves_previous_plain_reader(self):
        from local_detail_plan_DN import collect as current
        from main_continuity_plan_DN import collect as previous
        from test_full_plan_DN_source import source_fixture
        doc,g=case();before=copy.deepcopy(g)
        result=current(doc,g,'S','G',[dict(edge_id='ML',nominal_mm=200,evidence_id='bounded-test-seed')])
        self.assertEqual(result['native_local_detail_T_nodes'],['T']);self.assertEqual(result['source_T_exceptions'],{})
        self.assertEqual({r['edge_id']:r['nominal_mm']for r in result['records']},{'BR':200,'ML':200,'MR':200});self.assertEqual(g,before)
        doc,g,_,_=source_fixture();old=previous(doc,g,'SRC','GRAPH');new=current(doc,g,'SRC','GRAPH')
        for key,value in old.items():self.assertEqual(new[key],value,key)
        self.assertEqual(new['native_local_detail_T_nodes'],[])

    def test_unowned_node_boundary_and_transforms_preserve_local_T_without_semantic_promotion(self):
        for boundary in(False,True):
            for angle in(0,math.pi/2):
                for mirror in(1,-1):
                    doc,g=case(boundary,angle,mirror);before=copy.deepcopy(g);proof=collect(doc,g,'T','S','G')
                    self.assertEqual(len(proof['junctions'][0]['source_rays']),3);self.assertFalse(proof['equipment_ownership_inferred']);self.assertFalse(proof['main_detail_correspondence_inferred'])
                    self.assertIsNone(proof['physical_length_mm']);self.assertFalse(proof['physical_ports_verified']);self.assertEqual(g,before)
                    result=infer(g,[dict(edge_id='ML',nominal_mm=200,evidence_id='LABEL')],['ML','MR','BR'],{'T':proof},'S','G')
                    self.assertTrue(all(r['nominal_mm']==200 for r in result['records']))

    def test_branch_label_does_not_backflow_and_native_Z_does_not_become_length(self):
        doc,g=case();line=doc.entitydb[g['edges'][0]['source_handles'][0]];line.dxf.start=(0,-300,400);line.dxf.end=(0,-100,400)
        proof=collect(doc,g,'T','S','G');result=infer(g,[dict(edge_id='BR',nominal_mm=80,evidence_id='BRANCH')],['ML','MR','BR'],{'T':proof},'S','G')
        self.assertIsNone(proof['physical_length_mm']);self.assertEqual({r['edge_id']:r['nominal_mm']for r in result['records']},{'BR':80,'ML':None,'MR':None})

    def test_stale_circle_rim_service_source_and_fourway_are_barriers(self):
        for mode in('rim','circle','duplicate','service','source','review','fourway','physical_path'):
            doc,g=case();branch=g['edges'][0]
            if mode=='rim':branch['source_detail_circle_length_evidence']['line_contact'][0]+=1
            elif mode=='circle':doc.modelspace().add_circle((0,0),100)
            elif mode=='duplicate':
                line=doc.entitydb[branch['source_handles'][0]];doc.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
            elif mode=='service':branch['system']='return'
            elif mode=='source':g['metadata']['source_sha256']='STALE'
            elif mode=='review':next(n for n in g['nodes']if n['node_id']=='T')['review_required']=True
            elif mode=='fourway':g['edges'].append(dict(branch,edge_id='EXTRA'))
            else:branch['attribute_paths'][0][0]=[0,0]
            with self.subTest(mode=mode),self.assertRaises(ValueError):collect(doc,g,'T','S','G')

if __name__=='__main__':unittest.main()
