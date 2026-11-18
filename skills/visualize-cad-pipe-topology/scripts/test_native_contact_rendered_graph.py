import copy,unittest
from native_contact_rendered_graph import apply,restore,ROOT
from native_flange_contact_ownership import recover
from test_native_flange_contact_ownership import offset_fixture

class Tests(unittest.TestCase):
    def fixture(self):
        doc,native,insert,pipe=offset_fixture();base=native['edges'][0]
        old=dict(base,edge_id='OLD',system='supply');new=dict(base,edge_id='NEW',system='supply')
        edges=[dict(base,equipment_inventory=[]),dict(old,equipment_inventory=[dict(type='BALL',label='Ball',count=1,device_names=['Ball-1'])]),dict(new,equipment_inventory=[])]
        instance=dict(id='I1',name='Ball-1',type='BALL',label='Ball',source_top_handle='OLD-SOURCE',source_device_name='D/VALVE',edge_id='OLD',owner_equipment='D',x=1.,y=2.,assignment_x=1.,assignment_y=2.,sourceGeometry=[dict(points=[[1,2],[3,4]],fill=False)])
        parent=dict(edges=edges,nodes=[dict(node_id='D',label='中文设备')],instances=[instance],transform=dict(originX=0,originY=0,scale=1),symbols=dict(DBALANCE={}),types=[dict(code='DBALANCE',label='Balancing Valve')],old_attributes=dict(unknown_length=None))
        native['edges']=[base,old,new]
        before=dict(device_name='D/VALVE',owner_equipment='D',edge_id='OLD');after=dict(before,edge_id='NEW',assignment_x='10',assignment_y='20',edge_distance='3',assignment_status='assigned',assignment_basis='source_contact',original_edge_id='OLD')
        inventory=dict(all_component_ids_and_counts_conserved=True,source_graph_and_symbol_geometry_unchanged=True,human_accepted=False,changes=[dict(source_handle='OLD-SOURCE',before=before,after=after)])
        added=recover(doc,native,[],[insert.dxf.handle]);policy=dict(code='DBALANCE',label='Balancing Valve',symbol=dict(block='平衡阀'))
        return parent,native,inventory,added,doc,policy,'a'*64,'b'*64
    def test_conserved_index_changes_restore_exact_parent_and_keep_symbols_attributes(self):
        args=self.fixture();before=copy.deepcopy(args[0]);graph,audit=apply(*args)
        self.assertEqual(restore(graph,audit),before);self.assertEqual(args[0],before)
        self.assertEqual(len(graph['instances']),2);self.assertEqual(graph['instances'][0]['edge_id'],'NEW')
        self.assertEqual(graph['instances'][0]['sourceGeometry'],before['instances'][0]['sourceGeometry']);self.assertEqual(graph['old_attributes'],before['old_attributes'])
        self.assertEqual(graph['edges'][1]['equipment_inventory'],[]);self.assertEqual(graph['edges'][2]['equipment_inventory'][0]['count'],1);self.assertIn(ROOT,graph)
    def test_old_identity_wrong_pipe_system_or_missing_type_fails(self):
        for kind in ('identity','system','type'):
            args=list(self.fixture())
            if kind=='identity':args[0]['instances'][0]['source_device_name']='OTHER'
            elif kind=='system':args[0]['edges'][2]['system']=args[1]['edges'][2]['system']='return'
            else:args[0]['symbols']={}
            with self.subTest(kind=kind),self.assertRaises(ValueError):apply(*args)

if __name__=='__main__':unittest.main()
