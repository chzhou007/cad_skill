"""Inventory opaque proxy metadata without decoding proprietary payloads."""
from collections import Counter

def inventory(doc):
 classes=list(doc.classes.classes.values());rows=[]
 for e in doc.modelspace():
  if e.dxftype()!='ACAD_PROXY_ENTITY':continue
  tags=e.acdb_proxy_entity;ids=[t.value for t in tags if t.code==91];class_id=ids[0] if len(ids)==1 and isinstance(ids[0],int) else None
  index=class_id-500 if class_id is not None else -1;c=classes[index] if 0<=index<len(classes) else None
  graphic=bytes(e.proxy_graphic or b'');refs=[]
  for t in tags:
   if t.code not in (330,340,350,360) or t.value=='0':continue
   target=doc.entitydb.get(t.value);row={'code':t.code,'handle':t.value,'target_type':target.dxftype() if target else 'unresolved'}
   if target and target.dxftype()=='BLOCK_RECORD':row['block_name']=target.dxf.name
   refs.append(row)
  rows.append({'handle':e.dxf.handle,'layer':e.dxf.layer,'proxy_class_number':class_id,'ordinal_class_candidate':c.dxf.name if c else None,'ordinal_cpp_candidate':c.dxf.cpp_class_name if c else None,'class_mapping_status':'unverified_class_table_ordinal_candidate' if c else 'unresolved','graphic_bytes':len(graphic),'empty_graphic_header_only':graphic==b'\x08\x00\x00\x00\x00\x00\x00\x00','object_data_bits':next((t.value for t in tags if t.code==161),None),'class_data_bits':next((t.value for t in tags if t.code==162),None),'references':refs})
 groups=Counter((x['layer'],x['proxy_class_number'],x['ordinal_class_candidate'],x['graphic_bytes'],x['empty_graphic_header_only']) for x in rows)
 return {'records':rows,'groups':[{'layer':k[0],'proxy_class_number':k[1],'ordinal_class_candidate':k[2],'graphic_bytes':k[3],'empty_graphic_header_only':k[4],'count':v} for k,v in sorted(groups.items(),key=lambda kv:str(kv[0]))],'scope':'Class-table ordinal is an unverified candidate. Proprietary payloads were not decoded; block references do not provide individual placement or hydraulic connection.'}
