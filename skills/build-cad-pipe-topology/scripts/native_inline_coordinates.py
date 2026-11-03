"""Source-native inline anchor geometry. Never interpret polyline OCS as WCS."""
import math

def ball_valve_anchor(insert):
    """Complete verified SH16 family signature; returns WCS center or None.

    Call with an already transformed INSERT for a nested source instance.
    get_points() supplies OCS xy/bulge; vertices_in_wcs() supplies positions.
    """
    if insert.dxftype()!='INSERT':return None
    native=list(insert.virtual_entities());lines=[e for e in native if e.dxftype()=='LINE'];polys=[e for e in native if e.dxftype()=='LWPOLYLINE']
    if len(native)!=4 or len(lines)!=3 or len(polys)!=1:return None
    poly=polys[0];local=list(poly.get_points())
    if len(local)!=2 or not all(abs(abs(float(v[4]))-1)<1e-5 for v in local):return None
    world=list(poly.vertices_in_wcs())
    center=[(world[0][i]+world[1][i])/2 for i in range(3)]
    if not all(math.isfinite(v)for v in center):raise ValueError('Nonfinite native component anchor')
    return {'center':center[:2],'source_ocs_extrusion':list(poly.dxf.extrusion),
            'signature':'complete_3_line_2_bulge_native_ball_valve','coordinate_frame':'WCS'}

def balancing_valve_anchor(insert):
    """Verified six-line bow-tie with two parallel adjustment strokes, in WCS."""
    if insert.dxftype()!='INSERT':return None
    parts=list(insert.virtual_entities())
    if len(parts)!=6 or any(e.dxftype()!='LINE'for e in parts):return None
    lines=sorted([(tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2])for e in parts],key=lambda ab:math.dist(*ab),reverse=True)
    d1,d2=lines[:2];length=math.dist(*d1);tol=max(length*1e-6,1e-7)
    mid=lambda ab:[(ab[0][i]+ab[1][i])/2 for i in (0,1)]
    vec=lambda ab:[ab[1][i]-ab[0][i]for i in (0,1)]
    cross=lambda u,v:u[0]*v[1]-u[1]*v[0]
    if not length or abs(length-math.dist(*d2))>tol or math.dist(mid(d1),mid(d2))>tol:return None
    if abs(cross(vec(d1),vec(d2)))<length*length*.1:return None
    corners=list(d1+d2);matches=lambda p:any(math.dist(p,q)<=tol for q in corners)
    flanges=[ab for ab in lines[2:]if matches(ab[0])and matches(ab[1])]
    if len(flanges)!=2 or abs(cross(vec(flanges[0]),vec(flanges[1])))>tol*length:return None
    if any(sum(math.dist(p,q)<=tol for ab in flanges for q in ab)!=1 for p in corners):return None
    controls=[ab for ab in lines[2:]if ab not in flanges]
    if len(controls)!=2 or abs(math.dist(*controls[0])-math.dist(*controls[1]))>tol:return None
    def on(p,ab):
        u=vec(ab);v=[p[i]-ab[0][i]for i in (0,1)];ll=sum(x*x for x in u)
        t=sum(u[i]*v[i]for i in (0,1))/ll
        return -1e-6<=t<=1+1e-6 and abs(cross(u,v))<=tol*math.sqrt(ll)
    for ab in controls:
        if abs(cross(vec(ab),vec(flanges[0])))>tol*length:return None
        if not .01*length<math.dist(*ab)<.5*length:return None
        if sum(any(on(p,d)for d in (d1,d2))for p in ab)!=1:return None
    return {'center':mid(d1),'signature':'complete_6_line_bowtie_adjustment_balancing_valve','coordinate_frame':'WCS'}
