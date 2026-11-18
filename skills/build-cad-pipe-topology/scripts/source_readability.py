"""Strict native-text preflight, before source geometry or semantic trials."""
from pathlib import Path
import hashlib
import ezdxf
from ezdxf.filemanagement import dxf_file_info

def read_source(path):
    path=Path(path);info=dxf_file_info(path)
    doc=ezdxf.readfile(path,errors='strict');texts=[]
    for entity in doc.entitydb.values():
        if not entity.is_alive or entity.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF'):continue
        text=entity.plain_text()
        if '\ufffd' in text or any(0xd800<=ord(c)<=0xdfff for c in text):
            raise ValueError('Unreadable source text; stop before geometry trials: '+entity.dxf.handle)
        if any('\u4e00'<=c<='\u9fff' for c in text):
            texts.append({'handle':entity.dxf.handle,'entity_type':entity.dxftype(),'text':text})
    return doc,{'status':'PASS_STRICT_NATIVE_TEXT','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'dxf_version':info.version,'legacy_header_encoding':info.encoding,
                'actual_read_codec':'utf-8' if info.version>='AC1021' else info.encoding,
                'native_chinese_entity_count':len(texts),'native_chinese_samples':texts[:30],
                'scope':'Encoding integrity only; visual font legibility and exact project label reconciliation remain required. No binary proxy decoding.'}


def bind_graph_source(graph, source_sha256):
    """Bind a freshly constructed partial graph to its verified native input."""
    if not isinstance(source_sha256, str) or len(source_sha256) != 64 or any(c not in '0123456789abcdef' for c in source_sha256):
        raise ValueError('invalid native source sha256')
    metadata = graph.setdefault('metadata', {})
    if metadata.get('source_sha256', source_sha256) != source_sha256:
        raise ValueError('graph is bound to a different native source')
    metadata.update(source_sha256=source_sha256, hil_ready=False, graph_complete=False)
    return graph
