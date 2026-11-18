import copy,unittest,ezdxf,json,hashlib,subprocess,sys,tempfile
from pathlib import Path
from repair_source_floor_labels import repair,verify_output
from native_line_path_evidence import LAYERS


def fixture():
    d=ezdxf.new();m=d.modelspace();p=ezdxf.new();pm=p.modelspace();layer=LAYERS['supply']
    main=m.add_line((-10,0),(10,0),dxfattribs={'layer':layer})
    vertical=m.add_line((-10,0),(-10,100),dxfattribs={'layer':layer})
    title=pm.add_text('二层顶部水管平面图',dxfattribs={'layer':'TITLE'})
    anchors=[]
    for label in ('A','B'):
        a=m.add_text(label);b=pm.add_text(label)
        anchors.append(dict(equipment_id=label,axis_text_handle=a.dxf.handle,plan_text_handle=b.dxf.handle))
    nodes=[dict(node_id=n,node_type=t,x=x,y=y,floor=f) for n,t,x,y,f in [
        ('T','tee',0,0,3),('L','tee',-10,0,2),('R','tee',10,0,2),
        ('A','equipment',-20,0,2),('B','equipment',20,0,2),('V','virtual_equipment',0,-5,2),('UP','tee',-10,100,3)]]
    by={n['node_id']:n for n in nodes};edges=[]
    for ident,a,b in [('ML','L','T'),('MR','T','R'),('BR','T','V'),('EA','L','A'),('EB','R','B'),('CUT','L','UP')]:
        n,q=by[a],by[b];edges.append(dict(edge_id=ident,start_node_id=a,end_node_id=b,system='supply',floor_start=n['floor'],floor_end=q['floor'],attribute_paths=[[[n['x'],n['y']],[q['x'],q['y']]]],equipment_inventory=[]))
    g=dict(nodes=nodes,edges=edges)
    h=dict(source_sha256='S',plan_source_sha256='P',graph_sha256='G')
    policy=dict(h,target_floor=2,plan_title=dict(handle=title.dxf.handle,text=title.dxf.text,layer='TITLE',floor=2),caption_anchors=anchors,
        coverage_policy=dict(source_sha256='S',graph_sha256='G',edges=['ML','MR','CUT']),
        riser_barrier_edges={'CUT':vertical.dxf.handle},minimum_barrier_drawing_span=80,
        nodes=[dict(node_id='T',expected_floor=3,main_edge_ids=['ML','MR'],source_line_sequences={'ML':[main.dxf.handle],'MR':[main.dxf.handle]})])
    return d,p,g,policy,h


class SourceFloorLabelRepairTests(unittest.TestCase):
    def test_corrects_only_floor_metadata_with_source_caption_corrobation(self):
        d,p,g,policy,h=fixture();before=copy.deepcopy(g)
        out,proof=repair(d,p,g,policy,h)
        self.assertEqual(g,before)
        self.assertEqual(next(n for n in out['nodes'] if n['node_id']=='T')['floor'],2)
        self.assertEqual(next(e for e in out['edges'] if e['edge_id']=='BR')['floor_start'],2)
        for a,b in zip(g['edges'],out['edges']):
            self.assertEqual({k:v for k,v in a.items() if k not in ('floor_start','floor_end')},
                             {k:v for k,v in b.items() if k not in ('floor_start','floor_end')})
        self.assertFalse(proof['graph_connectivity_changed'])
        self.assertFalse(proof['crossview_path_mapping_ready'])
        self.assertFalse(out['sourceFloorLabelRepair']['physical_floor_verified'])

    def test_matching_title_text_cannot_be_used_for_other_floor(self):
        d,p,g,q,h=fixture();q['target_floor']=3;q['plan_title']['floor']=3
        with self.assertRaisesRegex(ValueError,'does not state'):repair(d,p,g,q,h)

    def test_caption_change_and_stale_graph_rejected(self):
        d,p,g,q,h=fixture();p.entitydb[q['caption_anchors'][0]['plan_text_handle']].dxf.text='OTHER'
        with self.assertRaisesRegex(ValueError,'caption changed'):repair(d,p,g,q,h)
        d,p,g,q,h=fixture();h['graph_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'mismatch'):repair(d,p,g,q,h)

    def test_competing_equipment_floor_is_not_overwritten(self):
        d,p,g,q,h=fixture();g['nodes'].append(dict(node_id='C',node_type='equipment',x=15,y=-5,floor=3))
        g['edges'].append(dict(edge_id='EC',start_node_id='R',end_node_id='C',system='supply'))
        with self.assertRaisesRegex(ValueError,'competing equipment floor'):repair(d,p,g,q,h)

    def test_duplicate_source_main_and_nonvertical_barrier_fail(self):
        d,p,g,q,h=fixture();d.modelspace().add_line((-10,0),(10,0),dxfattribs={'layer':LAYERS['supply']})
        with self.assertRaisesRegex(ValueError,'fully native'):repair(d,p,g,q,h)
        d,p,g,q,h=fixture();q['riser_barrier_edges']['CUT']=q['nodes'][0]['source_line_sequences']['ML'][0]
        with self.assertRaisesRegex(ValueError,'long vertical'):repair(d,p,g,q,h)

    def test_cli_evidence_reproduces_and_detects_audit_changes(self):
        d,p,g,q,h=fixture()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);axis=root/'axis.dxf';plan=root/'plan.dxf';gp=root/'graph.json';pp=root/'policy.json'
            d.saveas(axis);p.saveas(plan);gp.write_text(json.dumps(g),encoding='utf8')
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            h.update(source_sha256=sha(axis),plan_source_sha256=sha(plan),graph_sha256=sha(gp));q.update(h)
            q['coverage_policy'].update(source_sha256=h['source_sha256'],graph_sha256=h['graph_sha256'])
            pp.write_text(json.dumps(q),encoding='utf8');out=root/'out'
            subprocess.run([sys.executable,str(Path(__file__).with_name('repair_source_floor_labels.py')),
                '--source',str(axis),'--plan-source',str(plan),'--graph',str(gp),'--policy',str(pp),
                '--output',str(out)],check=True,capture_output=True)
            self.assertEqual(verify_output(out/'graph_with_edges.json')['nodes'],1)
            audit=out/'floor-label-repair-audit.json';data=json.loads(audit.read_text(encoding='utf8'))
            data['coverage']['edges']=[];audit.write_text(json.dumps(data),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'not reproducible'):verify_output(out/'graph_with_edges.json')


if __name__=='__main__':unittest.main()
