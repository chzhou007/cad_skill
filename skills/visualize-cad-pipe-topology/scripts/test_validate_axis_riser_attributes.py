import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from test_attach_axis_riser_segment_attributes import data
from attach_axis_riser_segment_attributes import append
from test_native_axis_riser_DN_scopes import fixture
from validate_axis_riser_attributes import validate


class Tests(unittest.TestCase):
    def fixture(self):
        doc,local,ev,sp,p=fixture()
        from native_axis_riser_DN_scopes import attribute
        scope=attribute(doc,local,ev,sp,p,'S','G');scope['source_sha256']='a'*64;scope['graph_sha256']='b'*64
        local['metadata']['source_sha256']='a'*64;parent=copy.deepcopy(local);out,_=append(parent,local,scope,'c'*64,'d'*64)
        return doc,out
    def test_original_native_context_verifies_all_segment_source_LINEs(self):
        doc,g=self.fixture();self.assertEqual(validate(g,doc,'a'*64),4)
        with self.assertRaisesRegex(ValueError,'original native source'):validate(g)
    def test_forged_root_whole_edge_and_source_LINE_changes_block(self):
        for case in ['root','DN','length','point','line','hash','duplicate']:
            doc,g=self.fixture();row=next(e['axis_riser_attributes'][0] for e in g['edges'] if e.get('axis_riser_attributes'))
            if case=='root':del g['sourceAxisRiserSegmentAttributes']
            elif case=='DN':row['whole_edge_nominal_mm']=450
            elif case=='length':row['physical_length_mm']=0
            elif case=='point':row['scope_points'][0][0]+=1
            elif case=='line':doc.entitydb[row['source_line_handle']].dxf.layer='wrong'
            elif case=='hash':row['source_sha256']='e'*64
            else:g['sourceAxisRiserSegmentAttributes']['records'].append(copy.deepcopy(row))
            with self.subTest(case=case),self.assertRaises(ValueError):validate(g,doc,'a'*64)
    def test_ordinary_legacy_graph_needs_no_new_native_context(self):self.assertEqual(validate({'edges':[{'edge_id':'ordinary'}]}),0)


if __name__=='__main__':unittest.main()
