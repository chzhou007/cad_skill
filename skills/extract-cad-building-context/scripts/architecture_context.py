"""Read-only architectural CAD context, independent of the hydraulic graph."""
from pathlib import Path
import argparse,collections,hashlib,html,json,math,re
import ezdxf
from ezdxf.path import make_path,from_hatch

ALIASES=[('wall',r'WALL|墙'),('column',r'COLU|COLUMN|柱'),('door',r'DOOR|门'),('window',r'WINDOW|固定窗|窗'),('grid',r'AXIS|轴线|轴网'),('stair',r'STAIR|楼梯'),('floor',r'A-FLOR|楼板|^2D_ROOF$'),('outline',r'Arch-平面-轮廓|建筑.*轮廓|^(?:GROUND|看线|雨篷线|分水线)$'),('annotation',r'Arch-文字|Arch-注释|A-ANNO|PUB_TEXT|DIM$|标高|^SPACE$|房间编号'),('building_context',r'建筑底图|^Arch-|开洞|^PUB_HATCH$')]
ROOMS={'上线井':'Cable Shaft','弱电机房':'Low-voltage IT Room','辅助用房':'Support Room','配电装置室':'Switchgear Room','强电间':'Power Room','弱电间':'ELV Room','走廊':'Corridor','空调区':'Air-conditioning Zone','变配电室':'Power Distribution Room','空调机房':'Air-conditioning Plant Room','配电间':'Electrical Room','消防控制室':'Fire Control Room','消防控制中心':'Fire Control Center','消防控制':'Fire Control','安检':'Security Screening','金属探测':'Metal Detection','卸货平台':'Loading Platform','卫生间':'Restroom','男卫':'Male Restroom','女卫':'Female Restroom','楼梯间':'Stairwell','电梯厅':'Lift Lobby','电梯':'Lift','值班室':'Duty Room','休息室':'Rest Room','办公室':'Office','会议室':'Meeting Room','工具间':'Tool Room','储藏室':'Storage','储物间':'Storage','门厅':'Entrance Hall','水泵房':'Pump Room','水泵间':'Pump Room','蓄电池室':'Battery Room','电池室':'Battery Room','主变室':'Transformer Room','柴发机房':'Generator Room','柴油发电机房':'Diesel Generator Room','数据机房':'Data Hall','机房':'Equipment Room','上':'Up','下':'Down'}
ROOMS.update({'茶水间':'Pantry','水井':'Plumbing Shaft','排烟':'Smoke Exhaust','空调管井':'HVAC Pipe Shaft','电池间':'Battery Room','一段配电装置室':'Section 1 Switchgear Room','二段配电装置室':'Section 2 Switchgear Room','控制室':'Control Room','电容器室':'Capacitor Room','拆包间':'Unpacking Room','消控室':'Fire Control Room','运营商接入间':'Carrier Entry Room','淋浴间':'Shower Room','洽谈室':'Meeting Room','入口':'Entrance','出口':'Exit','发卡机':'Card Dispenser','还卡机':'Card Return','吧台':'Counter','售卖机':'Vending Machine','存包柜':'Locker','强电':'Electrical Power','暖通':'HVAC','服务台':'Service Desk','模拟信号':'Analog Signal','消防监控机柜':'Fire Monitoring Cabinet','电视墙':'Video Wall','3人':'3 persons','85英寸电视屏':'85 inch TV'})
ROOMS.update({'楼梯':'Stair','从上至下：':'Top to bottom:','从左至右：':'Left to right:','冷':'Cold (source fragment)','备品备件':'Spare Parts','换设备间':'Exchange Equipment Room (source fragment)','排烟井':'Smoke Exhaust Shaft','排烟机房':'Smoke Exhaust Fan Room','接入室':'Entry Room','新风井':'Fresh Air Shaft','水氟装':'Water-Refrigerant Assembly (source fragment)','水氟转换间':'Water-Refrigerant Conversion Room','灾后排气井':'Post-fire Exhaust Shaft','运营商':'Carrier','通':'Passage (source fragment)','道':'Passage (source fragment)','配电室':'Electrical Distribution Room','钢瓶间':'Cylinder Room','预留':'Reserved'})

def category(layer):
    # Bound XREF names are namespaces, not semantic layer names. Otherwise a
    # reference named '建筑底图' classifies every nested MEP/electrical layer.
    layer=re.split(r'\||\$\d+\$',layer)[-1]
    # Chinese valve layers contain the door character; they are MEP symbols.
    if re.search(r'阀门|阀件|仪表|(?:^|[-_])VALVE(?:[-_]|$)|(?:^|[-_])INSTRUMENT(?:[-_]|$)',layer,re.I):return None
    return next((c for c,p in ALIASES if re.search(p,layer,re.I)),None)

def english_label(text,record_id):
    text=re.sub(r'\s+',' ',text.strip()).replace('%%c','DIA ').replace('%%d',' deg ').replace('%%p',' +/- ').replace('±','+/-')
    if not text:return '', 'empty'
    if text.isascii():return text,'source_ascii'
    if re.fullmatch(r'[A-Za-z0-9-]+[甲乙丙]',text):return text[:-1]+' / source grade '+{'甲':'A','乙':'B','丙':'C'}[text[-1]],'dictionary_translation'
    for original in sorted(ROOMS,key=len,reverse=True):
        if original in text:
            rest=text.replace(original,'',1).strip()
            if not rest or rest.isascii():return (ROOMS[original]+' '+rest).strip(),'dictionary_translation'
    return 'Source label '+record_id,'translation_pending'

def extract(doc,transform,source_hash='',tolerance=1):
    records=[];issues=[];excluded=[];counts=collections.Counter();counter=0
    scale=transform['scale'];x0=transform['originX'];y0=transform['originY']
    def project(p):return [(p[0]-x0)/scale,(y0-p[1])/scale]
    def visit(entity,chain=(),inherited='0',depth=0,forced=None):
        nonlocal counter
        if depth>40:
            issues.append(dict(source_chain=chain,reason='block_depth_limit'));return
        kind=entity.dxftype();layer=entity.dxf.get('layer','0');layer=inherited if layer=='0'else layer
        original=entity.source_of_copy or entity;handle=entity.dxf.get('handle')or original.dxf.get('handle')or kind;chain=chain+(str(handle),)
        if kind=='INSERT':
            name=entity.dxf.name
            if name in doc.blocks and doc.blocks[name].block.dxf.flags&12:
                issues.append(dict(source_chain=chain,reason='xref_not_embedded',block=name));return
            try:
                refs=list(entity.multi_insert())if entity.mcount>1 else [entity]
                for ref in refs:
                    for attr in ref.attribs:visit(attr,chain,layer,depth+1)
                    def skipped(child,reason):
                        child_layer=child.dxf.get('layer','0');child_layer=layer if child_layer=='0'else child_layer
                        if category(child_layer):issues.append(dict(source_chain=list(chain),entity_type=child.dxftype(),reason='insert_child_not_renderable',detail=reason))
                    for child in ref.virtual_entities(skipped_entity_callback=skipped):visit(child,chain,layer,depth+1)
            except (ValueError,ezdxf.DXFError,NotImplementedError)as ex:issues.append(dict(source_chain=chain,reason='insert_expansion_failed',detail=str(ex)))
            return
        if kind in ['DIMENSION','ACAD_PROXY_ENTITY','MULTILEADER','MLEADER']:
            cat='dimension'if kind=='DIMENSION'else category(layer)
            if cat:
                try:
                    if kind in ['MULTILEADER','MLEADER']:
                        from ezdxf.render.mleader import virtual_entities
                        children=list(virtual_entities(entity))
                    else:children=list(entity.virtual_entities())
                    if not children:issues.append(dict(source_chain=chain,reason='no_cached_graphics',entity_type=kind))
                    for child in children:visit(child,chain,layer,depth+1,cat)
                except (ValueError,AttributeError,ezdxf.DXFError,NotImplementedError)as ex:issues.append(dict(source_chain=chain,reason='cached_graphics_unavailable',detail=str(ex)))
            return
        cat=category(layer)or forced
        if not cat:return
        counts[layer+':'+kind]+=1;counter+=1;rid=f'B{counter:06d}'
        row=dict(id=rid,category=cat,source_layer=layer,source_chain=list(chain),entity_type=kind,semantics='source_layer_candidate',paths=[])
        if kind in ['TEXT','MTEXT','ATTRIB']:
            text=entity.plain_text()if hasattr(entity,'plain_text')else entity.dxf.get('text','')
            label,status=english_label(text,rid)
            if not label:return
            pos=entity.dxf.insert if kind=='MTEXT'else entity.ocs().to_wcs(entity.dxf.insert)
            height=entity.dxf.char_height if kind=='MTEXT'else entity.dxf.height
            rotation=entity.get_rotation()if kind=='MTEXT'else entity.dxf.get('rotation',0)
            if kind!='MTEXT':
                from ezdxf.math import Vec3
                direction=entity.ocs().to_wcs(Vec3.from_deg_angle(rotation))
                rotation=math.degrees(math.atan2(direction.y,direction.x))
            row.update(source_text=text,label=label,label_status=status,position=[pos.x,pos.y],display_position=project(pos),font_height=height/scale,rotation=rotation)
            px,py=row['display_position'];fh=row['font_height'];theta=math.radians(-rotation);cw=math.cos(theta);sw=math.sin(theta)
            corners=[(px+x*cw-y*sw,py+x*sw+y*cw)for x,y in [(0,-fh),(len(label)*fh*.8,-fh),(len(label)*fh*.8,fh*.3),(0,fh*.3)]]
            xx,yy=zip(*corners);row['display_text_bounds']=[min(xx),min(yy),max(xx)-min(xx),max(yy)-min(yy)]
            native_layer=re.split(r'\||\$\d+\$',layer)[-1]
            row['semantic_type']='room_label_candidate'if native_layer in ['建筑底图','SPACE']or re.search('Arch-文字|A-ANNO-TEXT|房间编号',native_layer,re.I)else 'source_annotation'
            if status=='translation_pending':issues.append(dict(id=rid,source_chain=list(chain),reason='translation_pending',source_text=text))
        elif kind in ['POINT','ATTDEF']:
            excluded.append(dict(source_chain=list(chain),entity_type=kind,reason='definition_or_dimension_control_point_not_visible_building_geometry'));return
        elif kind=='WIPEOUT':
            pts=[[p.x,p.y]for p in entity.boundary_path_wcs()]
            row['paths']=[dict(points=pts,display_points=[project(v)for v in pts],fill=True)]
            row['render_role']='occlusion_mask'
        else:
            try:
                paths=list(from_hatch(entity))if kind=='HATCH'else [make_path(entity)]
                for path in paths:
                    pts=[[v.x,v.y]for v in path.flattening(tolerance)]
                    if len(pts)>1:row['paths'].append(dict(points=pts,display_points=[project(v)for v in pts],fill=kind in ['HATCH','SOLID','TRACE']))
            except (ValueError,TypeError,AttributeError,NotImplementedError)as ex:
                issues.append(dict(id=rid,source_chain=list(chain),reason='unsupported_architectural_geometry',entity_type=kind,detail=str(ex)));return
            if not row['paths']:return
        records.append(row)
    for e in doc.modelspace():visit(e)
    return dict(schemaVersion=1,source_sha256=source_hash,source_units=doc.header.get('$INSUNITS',0),transform=transform,records=records,issues=issues,explicit_exclusions=excluded,
        summary=dict(records=len(records),categories=dict(collections.Counter(r['category']for r in records)),labels=sum('label'in r for r in records),layer_entity_counts=dict(counts)),
        scope='Architectural source context only. No inferred rooms, room areas, storey heights, equipment containment, pipe connections or human review.')

def svg_markup(data,labels_only=False):
    chunks=[]
    for r in data['records']:
        body='';esc=lambda v:html.escape(str(v),quote=True)
        if 'label'in r:
            x,y=r['display_position'];a=-r['rotation'];height=max(.01,r['font_height'])
            body=f'<text x="{x:.6f}" y="{y:.6f}" transform="rotate({a:.6f} {x:.6f} {y:.6f})" font-size="{height:.6f}" font-family="Arial,sans-serif" fill="currentColor" stroke="none">{esc(r["label"])}</text>'
        elif not labels_only:
            # One compound HATCH path with evenodd preserves its openings.
            path=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in p['display_points'])+(' Z'if p['fill']else '')for p in r['paths'])
            fill='white'if r.get('render_role')=='occlusion_mask'else 'currentColor'if any(p['fill']for p in r['paths'])else 'none'
            if path:body=f'<path d="{path}" fill="{fill}" fill-rule="evenodd" stroke="{"none"if r.get("render_role")=="occlusion_mask"else "currentColor"}" stroke-width=".7" vector-effect="non-scaling-stroke"/>'
        if body:chunks.append(f'<g data-building-id="{r["id"]}" data-building-category="{r["category"]}" data-source-handle="{esc("/".join(r["source_chain"]))}">{body}</g>')
    return ''.join(chunks)

def export(source,graph,output):
    source=Path(source);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    doc=ezdxf.readfile(source);digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if graph:
        g=json.loads(Path(graph).read_text(encoding='utf8'))
        if 'transform'not in g:
            # Neutral viewer projection contract v1, not topology inference.
            nodes=g.get('nodes',[])
            if not nodes:raise ValueError('Graph needs nodes or an explicit display transform')
            xs=[float(n['x'])for n in nodes];ys=[float(n['y'])for n in nodes]
            if not all(math.isfinite(v)for v in xs+ys):raise ValueError('Graph coordinates must be finite')
            span=max(max(xs)-min(xs),max(ys)-min(ys))or 1
            g['transform']=dict(originX=min(xs)-span*.015,originY=max(ys)+span*.015,scale=span/1000)
    else:
        from ezdxf import bbox
        bounds=bbox.extents(doc.modelspace(),fast=True)
        if not bounds.has_data:raise ValueError('Source has no measurable native geometry')
        span=max(bounds.extmax.x-bounds.extmin.x,bounds.extmax.y-bounds.extmin.y,1)
        g={'transform':dict(originX=bounds.extmin.x,originY=bounds.extmax.y,scale=span/1000)}
    result=extract(doc,g['transform'],digest,max(g['transform']['scale']/100,.001))
    points=[q for r in result['records']for p in r['paths']for q in p['display_points']]
    for r in result['records']:
        if 'display_position'in r:
            x,y=r['display_position'];h=r['font_height'];points.extend([[x-h,y-h],[x+len(r['label'])*h*.7,y+h]])
    if points:
        xs,ys=zip(*points);pad=max(max(xs)-min(xs),max(ys)-min(ys),1)*.03
        box=[min(xs)-pad,min(ys)-pad,max(xs)-min(xs)+2*pad,max(ys)-min(ys)+2*pad]
    else:box=[0,0,1000,800]
    result['display_bounds']=box
    (output/'architecture.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    for name,only in [('architecture.svg',False),('architecture-labels.svg',True)]:
        (output/name).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="'+' '.join(map(str,box))+'"><g color="#687789">'+svg_markup(result,only)+'</g></svg>',encoding='utf8')
    return result

def validate_context(data,graph):
    if data['source_sha256']!=graph['provenance']['sha256']:raise ValueError('Building source hash differs from graph source')
    if data['transform']!=graph['transform']:raise ValueError('Building transform differs from graph coordinates')
    if len(data['records'])!=data['summary']['records']or len({r['id']for r in data['records']})!=len(data['records']):raise ValueError('Building record counts or IDs differ')
    if any(i['reason']!='translation_pending'for i in data['issues']):raise ValueError('Unrendered building source geometry')
    tf=data['transform']
    for r in data['records']:
        if 'label'in r and not r['label'].isascii():raise ValueError('Non-English building display label')
        for p in r['paths']:
            if len(p['points'])!=len(p['display_points']):raise ValueError('Building point count changed')
            for (x,y),(px,py)in zip(p['points'],p['display_points']):
                if not all(math.isfinite(v)for v in [x,y,px,py])or abs(px-(x-tf['originX'])/tf['scale'])>1e-7 or abs(py-(tf['originY']-y)/tf['scale'])>1e-7:raise ValueError('Building coordinates differ from source transform')
    return dict(status='PASS',records=len(data['records']),labels=data['summary']['labels'],translation_pending=sum(i['reason']=='translation_pending'for i in data['issues']),room_boundaries='unverified; not inferred')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dxf',required=True);p.add_argument('--graph');p.add_argument('--output',required=True);a=p.parse_args()
    r=export(a.dxf,a.graph,a.output);print(json.dumps(r['summary']))

