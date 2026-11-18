import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_source_crossview
from match_anchored_floor_main_network import MODE
def fixture():
    nodes={f'P{i}':f'I{i}' for i in range(6)};pairs=[];rows=[]
    for i,(a,b,system) in enumerate([(0,1,'supply'),(1,2,'supply'),(3,4,'return'),(4,5,'return')]):
        pair=dict(plan_edge='E'+str(i),iso_edge='A'+str(i),system=system,plan_start='P'+str(a),plan_end='P'+str(b),iso_start='I'+str(a),iso_end='I'+str(b));pairs.append(pair)
        rows.append(dict(mapping_id='M'+str(i),kind='anchored_same_floor_T_to_T_main',floor=1,system=system,plan_edges=[pair['plan_edge']],iso_edges=[pair['iso_edge']],
            **{k:pair[k] for k in ('plan_start','plan_end','iso_start','iso_end')},physical_ports_verified=False,physical_length_mm=None,human_accepted=False))
    anchors=[dict(equipment_id='D'+str(i),system=s,plan_T='P'+str(i+offset),iso_T='I'+str(i+offset)) for i in range(3) for s,offset in [('supply',0),('return',3)]]
    return dict(mode=MODE,status='source_checked_full_floor_main_correspondence_attributes_pending',floor=1,equipment_scope=['D0','D1','D2'],records=rows,
        plan_graph_sha256='G',evidence=dict(structure=dict(floor=1,node_mapping=nodes,anchors=anchors,pairs=pairs,unique_full_floor_T_network=True,physical_direction_inferred=False),
        native_T_proofs=dict(plan={n:{} for n in nodes},iso={n:{} for n in nodes.values()}),main_path_coverage=dict(plan={r['plan_edges'][0]:{} for r in rows},iso={r['iso_edges'][0]:{} for r in rows}),historical_scope_lineage=[],preserved_floor_attributes=None),
        local_graphs_mutated=False,expert_confirmation_claimed=False,physical_source_identity_resolved=False,physical_values_assigned=0,human_accepted=False,hil_ready=False,historical_main_paths=0,additional_main_paths=4)
class Tests(unittest.TestCase):
    def call(self,folder,data):
        with patch('match_anchored_floor_main_network.verify_output',return_value=data):return validate_source_crossview(folder)
    def test_dispatch_replays_new_owner_not_old_chain_count_rule(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=MODE)),encoding='utf8')
            result=self.call(temp,fixture());self.assertEqual(result['mapped_main_paths'],4);self.assertEqual(result['native_T_nodes'],6);self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_missing_native_evidence_anchors_or_changed_physical_scope_blocks(self):
        for case in ('T','path','anchor','port','length','history_count','duplicate'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                (Path(temp)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=MODE)),encoding='utf8');data=fixture();p=data['evidence']
                if case=='T':p['native_T_proofs']['plan'].pop('P0')
                elif case=='path':p['main_path_coverage']['iso'].pop('A0')
                elif case=='anchor':p['structure']['anchors'][0]['iso_T']='I5'
                elif case=='port':data['records'][0]['physical_ports_verified']=True
                elif case=='length':data['records'][0]['physical_length_mm']=0
                elif case=='history_count':data['historical_main_paths']=1
                else:data['records'][1]['mapping_id']=data['records'][0]['mapping_id']
                with self.assertRaises(ValueError):self.call(temp,data)
    def test_native_replay_failure_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=MODE)),encoding='utf8')
            with patch('match_anchored_floor_main_network.verify_output',side_effect=ValueError('native T moved')),self.assertRaisesRegex(ValueError,'native T moved'):validate_source_crossview(temp)
if __name__=='__main__':unittest.main()
