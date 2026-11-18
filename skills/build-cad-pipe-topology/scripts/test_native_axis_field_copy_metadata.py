"""FIELD copy warnings require real dictionaries and a literal native cache."""
import unittest
import ezdxf
from ezdxf.entities import factory
from ezdxf.lldxf.extendedtags import ExtendedTags
from plan_pipe_diameter_scopes import copied_metadata

class AxisFieldMetadataTests(unittest.TestCase):
    def fixture(self,value='11',layer='xref$0$AXIS_TEXT',cached='11',evaluator='_text',reference=False):
        doc=ezdxf.new();block=doc.blocks.new('AX');block.add_attdef('A',(0,0),text=value)
        insert=doc.modelspace().add_blockref('AX',(0,0));attr=insert.add_attrib('A',value,(0,0),dxfattribs={'layer':layer})
        extension=attr.new_extension_dict().dictionary;fields=extension.add_new_dict('ACAD_FIELD')
        raw='0\nFIELD\n5\nABCDEF\n330\n'+fields.dxf.handle+'\n100\nAcDbField\n1\n'+evaluator+'\n2\n'+cached+'\n1\n'+cached+'\n301\n'+cached+'\n'
        if reference:raw+='360\n123\n'
        entity=factory.load(ExtendedTags.from_text(raw),doc);doc.entitydb.add(entity);fields['TEXT']=entity
        message='copy process ignored FIELD(#ABCDEF) - this may cause problems in AutoCAD'
        return doc,attr,entity,extension,fields,message

    def test_only_literal_axis_cache_is_classified_without_evaluation(self):
        doc,attr,e,ext,fields,msg=self.fixture();before=attr.dxfattribs().copy()
        proof=copied_metadata(doc,msg)
        self.assertEqual(proof['owner_handle'],attr.dxf.handle);self.assertEqual(proof['visible_text'],'11')
        self.assertFalse(proof['field_expression_evaluated']);self.assertEqual(before,attr.dxfattribs())

    def test_parameter_fields_cache_disagreement_and_external_reference_rejected(self):
        for options in [dict(value='DN150',cached='DN150'),dict(value='11',cached='12'),dict(layer='DN_NOTE'),dict(evaluator='AcObjProp'),dict(reference=True)]:
            with self.subTest(options=options):
                doc,*_,msg=self.fixture(**options)
                with self.assertRaises(ValueError):copied_metadata(doc,msg)

    def test_invented_warning_and_broken_actual_ownership_rejected(self):
        for mode in ('missing','kind','text-key','extension-key','owner','unknown'):
            doc,attr,e,ext,fields,msg=self.fixture()
            if mode=='missing':msg=msg.replace('ABCDEF','BAD')
            if mode=='kind':msg=msg.replace('FIELD','ACAD_PROXY_OBJECT')
            if mode=='text-key':fields.remove('TEXT')
            if mode=='extension-key':ext.remove('ACAD_FIELD')
            if mode=='owner':ext.dxf.owner='BAD'
            if mode=='unknown':msg='copy process ignored LINE(#ABCDEF) - this may cause problems in AutoCAD'
            with self.subTest(mode=mode),self.assertRaises(ValueError):copied_metadata(doc,msg)

if __name__=='__main__':unittest.main()
