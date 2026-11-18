import copy,math,unittest
import ezdxf
from inherited_marker_and_crossover_evidence import population,collect,path_coverage,BRIDGE
from inherited_exploded_ball_profiles import owner

def transform(p,angle,mirror):
    x,y=p;x=-x if mirror else x;t=math.radians(angle);return(x*math.cos(t)-y*math.sin(t)+1000,x*math.sin(t)+y*math.cos(t)+2000)

def marker_scene(angle=0,mirror=False,far=False):
    doc=ezdxf.new();ms=doc.modelspace();tf=lambda p:transform(p,angle,mirror)
    pts=[(-275.99564,-275.99564),(-79.54951,-79.54951),(-173.99511,122.98973),(175.35618,-121.62867),(79.54951,79.54951),(275.99564,275.99564)]
    marker=ms.add_lwpolyline([tf(p)for p in pts],dxfattribs={'layer':'DIM_SYMB'});xy=owner().equipment_graph.polyline_center([tf(p)for p in pts]);ports=[];edges=[];nodes=[]
    for system,prefix,port in [('supply','S',(-63.8636,-63.8636)),('return','R',(63.8636,63.8636))]:
        if far:port=(-500,-500)if system=='supply'else(500,-500)
        end=(port[0],500);p,q=tf(port),tf(end);line=ms.add_line(p,q,dxfattribs={'layer':'空调冷冻水供水'if system=='supply'else'空调冷冻水回水'})
        ports.append(dict(port_id='V-'+prefix,node_id='V',system=system,x=p[0],y=p[1],source_marker_handle=marker.dxf.handle));nodes.append(dict(node_id=prefix,node_type='physical_junction',x=q[0],y=q[1],floor=3))
        edges.append(dict(edge_id='E'+prefix,system=system,start_node_id=prefix,end_node_id='V',end_port_id='V-'+prefix,source_insert_handle=marker.dxf.handle,connection_mode='standalone_omission_to_first_tee',attribute_paths=[[list(q),list(p),list(xy)]]))
    nodes.append(dict(node_id='V',node_type='virtual_equipment',subtype='external_system_interface',placement_rule='unowned_standalone_DIM_SYMB_center',source_marker_handle=marker.dxf.handle,x=xy[0],y=xy[1],floor=3,ports=ports))
    return doc,dict(metadata=dict(source_sha256='S'),nodes=nodes,edges=edges),marker

class OriginalNativeMarker(unittest.TestCase):
    def test_original_thirty_unit_geometry_reused_after_rotation_mirror(self):
        for angle in(0,37,90):
            for mirror in(False,True):
                doc,g,_=marker_scene(angle,mirror);before=copy.deepcopy(g);p=population(doc,'S');result=collect(doc,g,'V','S','G',p)
                self.assertTrue(result['original_native_marker_and_crossover_kernels_reused']);self.assertEqual(g,before)
                self.assertTrue(all(0<r['source_endpoint_to_marker_distance']<=30 for r in result['records']));self.assertFalse(result['common_marker_creates_pipe_connection'])
    def test_beyond_calibration_duplicate_source_and_competing_marker_held(self):
        doc,g,_=marker_scene(far=True)
        with self.assertRaises(ValueError):collect(doc,g,'V','S','G',population(doc,'S'))
        doc,g,_=marker_scene();line=next(iter(doc.modelspace().query('LINE')));doc.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
        with self.assertRaises(ValueError):collect(doc,g,'V','S','G',population(doc,'S'))
        doc,g,marker=marker_scene();doc.modelspace().add_lwpolyline(list(marker.get_points('xy')),dxfattribs={'layer':'DIM_SYMB'})
        with self.assertRaises(ValueError):collect(doc,g,'V','S','G',population(doc,'S'))

def gap_scene(same=False,angle=0,mirror=False,host=True,gap=100,right_z=0):
    doc=ezdxf.new();ms=doc.modelspace();tf=lambda p:transform(p,angle,mirror);a,b=tf((-gap/2,0)),tf((gap/2,0));left,right=tf((-gap/2-100,0)),tf((gap/2+100,0))
    ms.add_line(left,a,dxfattribs={'layer':'空调冷冻水供水'});ms.add_line((*b,right_z),(*right,right_z),dxfattribs={'layer':'空调冷冻水供水'})
    if host:ms.add_line(tf((0,-200)),tf((0,200)),dxfattribs={'layer':'空调冷冻水供水'if same else'空调冷冻水回水'})
    center=tf((gap/2+110,0));edge=dict(edge_id='E',system='supply',start_node_id='T',end_node_id='V',attribute_paths=[[list(left),list(a),list(b),list(right),list(center)]])
    graph=dict(metadata={'source_sha256':'S'},nodes=[dict(node_id='T',node_type='physical_junction',x=left[0],y=left[1]),dict(node_id='V',node_type='virtual_equipment',subtype='external_system_interface',x=center[0],y=center[1])],edges=[edge])
    return doc,graph
class OriginalNativeCrossovers(unittest.TestCase):
    def test_original_same_and_opposite_system_crossings_keep_no_node_and_unknown_length(self):
        for same in(False,True):
            for angle,mirror in[(0,False),(37,True),(90,False)]:
                doc,g=gap_scene(same,angle,mirror);p=population(doc,'S');out=path_coverage(doc,g,'E','S','G',p);s=out['edges'][0]['segments'][1]
                self.assertEqual(s['status'],BRIDGE);self.assertEqual(s['previous_native_LINE_status'],'no_witness_in_scoped_search')
                self.assertIsNone(s['physical_gap_length_mm']);self.assertFalse(s['source_crossover_evidence']['crossed_pipe_connected']);self.assertTrue(p['proof']['native_T_population_before_after_equal'])
    def test_no_host_long_gap_and_different_native_endpoint_Z_do_not_get_bridged(self):
        for kw in(dict(host=False),dict(gap=302),dict(right_z=1)):
            doc,g=gap_scene(**kw)
            with self.assertRaises(ValueError):path_coverage(doc,g,'E','S','G',population(doc,'S'))
if __name__=='__main__':unittest.main()
