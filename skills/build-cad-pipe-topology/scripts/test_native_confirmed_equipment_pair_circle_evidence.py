import copy,math,unittest
from ezdxf.math import Matrix44
from test_reconstruct_confirmed_equipment_pairs import fixture
from reconstruct_confirmed_equipment_pairs import prepare,rebuild
from native_confirmed_equipment_pair_circle_evidence import collect

def case(angle=0,z=False):
    d,g,old,rows,m,r,p=fixture();m['images'][0]['sha256']='b'*64;r['sections'][0]['image']['sha256']='b'*64;p['reply_sha256']='a'*64
    if z:
        h=p['equipment'][0]['connections'][0]['branch_handle'];line=d.entitydb[h]
        line.dxf.start=(line.dxf.start.x,line.dxf.start.y,21.05);line.dxf.end=(line.dxf.end.x,line.dxf.end.y,1.576)
    if angle:
        matrix=Matrix44.z_rotate(math.radians(angle))
        for e in d.modelspace():e.transform(matrix)
        def xy(point):
            q=matrix.transform((point[0],point[1],0));return [q.x,q.y]
        for n in g['nodes']:n['x'],n['y']=xy([n['x'],n['y']])
        for edge in g['edges']:
            for key in ('path','path_points'):
                if key in edge:edge[key]=[xy(p) for p in edge[key]]
            edge['attribute_paths']=[[xy(p) for p in path] for path in edge['attribute_paths']]
        for row in rows:row['x'],row['y']=map(str,xy([float(row['x']),float(row['y'])]))
        # The reviewed synthetic picture must encompass the rotated source.
        m['images'][0]['window']=[-2000,2000,-2000,2000]
        old=copy.deepcopy(g)
    connections,questions=prepare(d,g,old,m,r,p,'S','G');result,_,_=rebuild(d,g,rows,connections,questions,p,'S','G')
    return d,result

class ConfirmedPairCircleEvidenceTests(unittest.TestCase):
    def test_reuses_original_reconstruction_in_all_four_native_rotations(self):
        for angle in (0,90,180,270):
            d,g=case(angle);before=copy.deepcopy(g)
            for row in g['confirmedEquipmentPairReconstruction']['records']:
                evidence=collect(d,g,row['tee'],'S','CURRENT')
                self.assertEqual(len(evidence['junctions'][0]['source_rays']),3)
                self.assertFalse(evidence['graph_mutated']);self.assertFalse(evidence['physical_ports_verified']);self.assertFalse(evidence['human_accepted'])
                self.assertIsNone(evidence['physical_connector_length'])
            self.assertEqual(before,g)

    def test_wrong_circle_colours_and_recorded_Z_are_preserved_only_under_confirmation(self):
        d,g=case(z=True)
        for row in g['confirmedEquipmentPairReconstruction']['records']:
            e=collect(d,g,row['tee'],'S','CURRENT')
            if row['system']=='return':
                self.assertAlmostEqual(e['circle_main_offset'],1)
                self.assertEqual(e['native_XYZ']['branch'][0][2],21.05)
        row=g['confirmedEquipmentPairReconstruction']['records'][0];meta=next(n for n in g['nodes'] if n['node_id']==row['tee'])['source_confirmed_equipment_pair_circle']
        line=d.entitydb[meta['branch_handle']];line.dxf.end=(line.dxf.end.x,line.dxf.end.y,2)
        with self.assertRaisesRegex(ValueError,'XYZ'):collect(d,g,row['tee'],'S','CURRENT')

    def test_unrecorded_four_way_mixed_service_or_later_main_split_rejected(self):
        for kind in ('fourway','mixed','split','missingroot','pending','boundary'):
            d,g=case();row=g['confirmedEquipmentPairReconstruction']['records'][0];node=next(n for n in g['nodes'] if n['node_id']==row['tee']);incident=[e for e in g['edges'] if node['node_id'] in (e['start_node_id'],e['end_node_id'])]
            if kind=='fourway':g['edges'].append(dict(incident[0],edge_id='EXTRA'))
            if kind=='mixed':incident[1]['system']='supply' if node['system']=='return' else 'return'
            if kind=='split':incident[1]['split_source_edge']['source_graph_sha256']='OTHER'
            if kind=='missingroot':g.pop('confirmedEquipmentPairReconstruction')
            if kind=='pending':node['review_required']=True
            if kind=='boundary':g['boundary_anchors']=[dict(source_marker_handles=[row['circle_handle']])]
            with self.subTest(kind=kind),self.assertRaises((ValueError,KeyError)):collect(d,g,node['node_id'],'S','CURRENT')

    def test_confirmation_scope_and_physical_unknowns_cannot_be_promoted(self):
        for kind in ('answer','pair','source','owner','port','length','offset','rim','caption'):
            d,g=case();row=g['confirmedEquipmentPairReconstruction']['records'][0];node=next(n for n in g['nodes'] if n['node_id']==row['tee']);edge=next(e for e in g['edges'] if e['edge_id']==row['branch_edge'])
            meta=copy.deepcopy(node['source_confirmed_equipment_pair_circle']);node['source_confirmed_equipment_pair_circle']=meta;edge['source_confirmed_equipment_pair_circle']=meta
            if kind=='answer':meta['answer']['decision']='未确认'
            if kind=='pair':meta['pair_sha256']='unbound'
            if kind=='source':meta['source_sha256']='OTHER'
            if kind=='owner':edge['start_node_id']='returnA'
            if kind=='port':meta['physical_port_verified']=True
            if kind=='length':meta['physical_length']=0
            if kind=='offset':meta['maximum_circle_main_offset_drawing_units']=5
            if kind=='rim':meta['source_rim'][0]+=.2
            if kind=='caption':d.entitydb[meta['native_caption_handle']].dxf.text='another device'
            with self.subTest(kind=kind),self.assertRaises((ValueError,KeyError)):collect(d,g,node['node_id'],'S','CURRENT')

    def test_duplicate_native_source_ray_is_not_hidden(self):
        d,g=case();row=g['confirmedEquipmentPairReconstruction']['records'][0];node=next(n for n in g['nodes'] if n['node_id']==row['tee']);meta=node['source_confirmed_equipment_pair_circle'];line=d.entitydb[meta['main_handle']]
        d.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
        with self.assertRaisesRegex(ValueError,'ambiguous'):collect(d,g,node['node_id'],'S','CURRENT')

if __name__=='__main__':unittest.main()
