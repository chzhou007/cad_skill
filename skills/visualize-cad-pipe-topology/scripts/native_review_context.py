"""Render a wide native CAD locator image around explicitly scoped issues.

No topology inference or entity/layer filtering: the drawing frontend owns
native source rendering, including its known proxy/font limitations.
"""
import copy
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle
from ezdxf.addons.drawing import Frontend, RenderContext, layout
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
from ezdxf.fonts import fonts
from ezdxf.math import BoundingBox2d, Vec3

FONT = Path('C:/Windows/Fonts/simhei.ttf')


def record_source(doc):
    if not FONT.is_file():
        raise ValueError('readable Chinese rendering font missing')
    font = fonts.get_font_face(FONT.name)
    if font.family != 'SimHei':
        raise ValueError('Chinese font silently fell back')
    context = RenderContext(doc)
    context.resolve_font = lambda entity: font
    backend = SVGBackend()
    Frontend(context, backend, config=Configuration(background_policy=BackgroundPolicy.BLACK,
        min_lineweight=.08, hatching_timeout=5)).draw_layout(doc.modelspace(), finalize=True)
    return backend


def expanded_window(boxes, min_width=20000, min_height=14000, factor=2.5):
    x0=min(b['bbox'][0] for b in boxes); x1=max(b['bbox'][1] for b in boxes)
    y0=min(b['bbox'][2] for b in boxes); y1=max(b['bbox'][3] for b in boxes)
    cx=(x0+x1)/2;cy=(y0+y1)/2
    w=max(min_width,(x1-x0)*factor);h=max(min_height,(y1-y0)*factor)
    # Keep the rendered overview readable on the review page.
    if w/h<1.35:w=h*1.35
    if w/h>2.2:h=w/2.2
    return [cx-w/2,cx+w/2,cy-h/2,cy+h/2]


def render_context(recording, window, boxes, destination, title):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    x0,x1,y0,y1=window
    if not (x0<x1 and y0<y1):raise ValueError('invalid context window')
    for b in boxes:
        a,c,d,e=b['bbox']
        if not (x0<=a<c<=x1 and y0<=d<e<=y1):raise ValueError('locator outside context')
    player=recording.player().copy()
    player.crop_rect((x0,y0),(x1,y1),distance=.2)
    font=FontProperties(fname=str(FONT))
    fig=plt.figure(figsize=(16,16*(y1-y0)/(x1-x0)),facecolor='black')
    ax=fig.add_axes([.015,.015,.97,.92]);ax.set_facecolor('black')
    mpl=MatplotlibBackend(ax,adjust_figure=False);player.replay(mpl);mpl.finalize()
    for b in boxes:
        a,c,d,e=b['bbox']
        ax.add_patch(Rectangle((a,d),c-a,e-d,fill=False,edgecolor='#ff643b',lw=2.4,ls='--',zorder=100))
        ax.annotate(b['label'],(a,e),xytext=(3,4),textcoords='offset points',
            fontproperties=font,fontsize=11,color='white',zorder=101,
            bbox=dict(facecolor='#a92c0a',edgecolor='none',alpha=.95,pad=3))
    ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal',adjustable='box');ax.set_autoscale_on(False);ax.set_axis_off()
    fig.text(.02,.97,title,fontproperties=font,fontsize=15,color='white',va='top')
    fig.savefig(destination.with_suffix('.png'),dpi=160,facecolor='black')
    if tuple(ax.get_xlim())!=(x0,x1) or tuple(ax.get_ylim())!=(y0,y1):
        raise ValueError('PNG crop moved during aspect adjustment')
    plt.close(fig)
    # The SVG preserves zoom detail and the same native WCS crop.
    backend=SVGBackend();player.replay(backend)
    root=backend.get_xml_root_element(layout.Page(300,300*(y1-y0)/(x1-x0)),
        settings=layout.Settings(crop_at_margins=True,min_stroke_width=.03),
        render_box=BoundingBox2d([(x0,y0),(x1,y1)]))
    ns='{http://www.w3.org/2000/svg}'
    for b in boxes:
        a,c,d,e=b['bbox'];p=backend.transformation_matrix.transform(Vec3(a,d,0));q=backend.transformation_matrix.transform(Vec3(c,e,0))
        ET.SubElement(root,ns+'rect',{'x':str(min(p.x,q.x)),'y':str(min(p.y,q.y)),
            'width':str(abs(q.x-p.x)),'height':str(abs(q.y-p.y)),
            'fill':'none','stroke':'#ff643b','stroke-width':'2200','stroke-dasharray':'6000 3000'})
        text=ET.SubElement(root,ns+'text',{'x':str(min(p.x,q.x)),
            'y':str(min(p.y,q.y)-3500),'fill':'#ffb09b','font-size':'11000',
            'font-family':'Microsoft YaHei,SimHei,sans-serif','paint-order':'stroke',
            'stroke':'#000','stroke-width':'2000'})
        text.text=b['label']
    destination.with_suffix('.svg').write_text(ET.tostring(root,encoding='unicode'),encoding='utf8')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    return {'png_sha256':sha(destination.with_suffix('.png')),
        'svg_sha256':sha(destination.with_suffix('.svg')),'window_wcs':window,'locators':copy.deepcopy(boxes),
        'rendering':'native_modelspace_no_layer_or_entity_filter',
        'font_substitution':str(FONT),'physical_or_topology_changes':False,
        'limitations':['Native frontend unsupported/proxy entities may be absent; CAD remains authoritative.',
                       'Source text decoded strictly; SimHei substitutes native CAD font glyphs.']}
