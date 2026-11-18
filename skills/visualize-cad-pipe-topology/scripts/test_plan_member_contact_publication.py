import copy, json, tempfile, unittest, sys
from pathlib import Path
import refresh_plan_member_contacts as owner
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/viewer'))
from hil_server import identity

class PublicationTests(unittest.TestCase):
    def test_old_attributes_and_exact_new_evidence(self):
        record=dict(axis_edge_id='E1',mapping_id='M1',native_rays=[((0,0),(1,2))])
        before=[dict(edge_id='E1',values={'length':None,'DN':200}),dict(edge_id='E2',values={'length':12})]
        after=copy.deepcopy(before);after[0]['values'].update(dict(zip(owner.FIELDS,['M1','P1',json.dumps(record)])))
        self.assertEqual(owner.delta(before,after,[record])['new_length_values'],0)
        self.assertEqual(owner.canonical(record)['native_rays'],[[[0,0],[1,2]]])
        after[0]['values']['length']=0
        with self.assertRaisesRegex(ValueError,'old attribute'):owner.delta(before,after,[record])
        after=copy.deepcopy(before);after[1]['values']['other']=1
        with self.assertRaisesRegex(ValueError,'actual mapping|escaped'):owner.delta(before,after,[])

    def test_manual_value_survives_semantic_mapping_change(self):
        m={'projectId':'P','sourceHashes':{'graph':'g'},'reviewContentHashes':{'a':'old'}};revised=copy.deepcopy(m);revised['reviewContentHashes']['a']='new'
        with tempfile.TemporaryDirectory()as folder:
            parent=Path(folder)/'old';output=Path(folder)/'new';old=parent/'annotations'/identity(m);old.mkdir(parents=True)
            doc=dict(datasetId=identity(m),revision=4,errors=[{'id':'issue-1'}],confirmation={'reviewer':'专家'},
                edgeEdits={'E1':{'length':{'valueM':12.3},'reviewed':{'author':'专家'}},'E2':{'reviewed':{'author':'专家'}}},edgeEditHistory=[{'edgeId':'E1','action':'setLength'}])
            (old/'review.json').write_bytes(owner.encode(doc))
            owner.migrate_review(parent,output,m,revised,{'E1'})
            actual=owner.load(output/'annotations'/identity(revised)/'review.json')
            self.assertEqual(actual['edgeEdits']['E1']['length'],doc['edgeEdits']['E1']['length'])
            self.assertNotIn('reviewed',actual['edgeEdits']['E1']);self.assertEqual(actual['edgeEdits']['E2'],doc['edgeEdits']['E2'])
            self.assertIsNone(actual['confirmation']);self.assertEqual(actual['historicalConfirmations'][0]['reviewer'],'专家')
            self.assertEqual(actual['errors'],doc['errors']);self.assertEqual(owner.load(old/'review.json'),doc)

if __name__=='__main__':unittest.main()
