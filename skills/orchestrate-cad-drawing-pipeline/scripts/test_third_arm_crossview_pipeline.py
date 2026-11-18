import unittest
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from pipeline import reconstruct_third_arm_crossview_batch,validate_third_arm_crossview_batch
from rebuild_third_arm_crossview_batch import MODE

class Tests(unittest.TestCase):
    def data(self):
        proof=dict(mode=MODE,complete_original_provider_replayed=True,current_native_T_and_path_scopes_replayed=True,
            all_old_provider_observations_preserved=True,source_graphs_mutated=False,physical_values_assigned=0,DN_used_for_matching=False,
            component_owners_or_counts_changed=False,global_cycle_equivalence_claimed=False,human_accepted=False,counts={})
        return proof,dict(counts={})
    def test_formal_batch_owner_and_independent_validator_keep_HIL_pending(self):
        with patch('rebuild_third_arm_crossview_batch.verify_output',return_value=self.data()):self.assertEqual(validate_third_arm_crossview_batch('run')['status'],'pending')
        with patch('rebuild_third_arm_crossview_batch.produce')as produce,patch('pipeline.validate_third_arm_crossview_batch',return_value={}):reconstruct_third_arm_crossview_batch('manifest','run')
        produce.assert_called_once_with('manifest','run')
    def test_source_replay_component_mutation_or_attribute_promotion_blocks(self):
        for key,value in [('complete_original_provider_replayed',False),('current_native_T_and_path_scopes_replayed',False),('component_owners_or_counts_changed',True),('physical_values_assigned',1),('global_cycle_equivalence_claimed',True)]:
            result=self.data();result[0][key]=value
            with self.subTest(key=key),patch('rebuild_third_arm_crossview_batch.verify_output',return_value=result),self.assertRaises(ValueError):validate_third_arm_crossview_batch('run')

    def test_fixed_parent_protocol_preserves_canonical_bytes_when_owner_returns_tuples(self):
        with tempfile.TemporaryDirectory()as temporary:
            root=Path(temporary);skills=root/'skills';scripts=skills/'build-cad-pipe-topology/scripts';scripts.mkdir(parents=True)
            (scripts/'legacy_named_provider_inventory.py').write_text("def verify_output(path):\n    return {'pairs':[('PLAN','AXIS')], 'human_accepted':False}\n",encoding='utf8')
            (scripts/'confirm_crossview_paths.py').write_text("import json\ndef encode(value):\n    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\\n').encode('utf8')\n",encoding='utf8')
            native=root/'native';native.mkdir();value=dict(pairs=[['PLAN','AXIS']],human_accepted=False);raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();(native/'provider-inventory.json').write_bytes(raw)
            sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();snapshot=root/'snapshot.json';snapshot.write_text(json.dumps(dict(files={p.relative_to(skills).as_posix():sha(p)for p in scripts.glob('*.py')})),encoding='utf8')
            worker=Path(__file__).with_name('replay_fixed_legacy_named_provider.py');output=root/'checked'
            result=subprocess.run([sys.executable,'-X','utf8','-B',str(worker),'--skills-root',str(skills),'--snapshot',str(snapshot),'--native-run',str(native),'--expected-sha256',sha(native/'provider-inventory.json'),'--output',str(output)],capture_output=True,text=True,encoding='utf8')
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual((output/'proof.json').read_bytes(),raw)

if __name__=='__main__':unittest.main()
