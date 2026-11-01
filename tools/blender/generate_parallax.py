"""Parallax / 01: original sculpted hover coupe, designed without image references.
Blender coordinates: nose -Y, rear +Y, up +Z. Free procedural source, no providers.
"""
import argparse, json, math, os, sys
import bpy, bmesh
from mathutils import Vector


def args():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',default='generated/parallax')
    p.add_argument('--shape-check',action='store_true')
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def material(name,color,metal=0,rough=.35,emission=0,alpha=1):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,alpha);m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough
    n.inputs['Alpha'].default_value=alpha
    if emission:
        (n.inputs.get('Emission Color') or n.inputs.get('Emission')).default_value=(*color,1)
        n.inputs['Emission Strength'].default_value=emission
    if alpha<1:
        if hasattr(m,'surface_render_method'):m.surface_render_method='DITHERED'
        elif hasattr(m,'blend_method'):m.blend_method='HASHED'
        if hasattr(m,'use_screen_refraction'):m.use_screen_refraction=True
        n.inputs['IOR'].default_value=1.46
    return m


def mesh(name,verts,faces,mat,smooth=True):
    d=bpy.data.meshes.new(name+' mesh');d.from_pydata(verts,[],faces);d.update();d.materials.append(mat)
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o)
    for p in d.polygons:p.use_smooth=smooth
    return o


def apply(o,mod):
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)


def soften(o,width=.025,segments=3):
    b=o.modifiers.new('Manufactured edge radius','BEVEL');b.width=width;b.segments=segments
    # Blender 4.0 requires Auto Smooth before evaluating weighted normals.
    if hasattr(o.data,'use_auto_smooth'):
        o.data.use_auto_smooth=True
    o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    return o


def box(name,loc,dims,mat,bevel=.025,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;o.rotation_euler=rot
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:soften(o,bevel)
    return o


def tube(name,points,radius,mat,cyclic=False):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=radius;d.bevel_resolution=2;d.resolution_u=5
    s=d.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
    for p,q in zip(s.bezier_points,points):p.co=q;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    s.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.data.materials.append(mat);return o


def cylinder(name,loc,r,depth,mat,vertices=48,axis='Z'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=loc)
    o=bpy.context.object;o.name=name;o.data.materials.append(mat)
    if axis=='Y':o.rotation_euler.x=math.pi/2
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o


def radial_shell(name,x,y,profile,mat,n=48):
    v=[];f=[]
    for z,r in profile:v.extend((x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),z) for i in range(n))
    for j in range(len(profile)-1):
        for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    return mesh(name,v,f,mat)


def ellipse_shell(name,x,z,profile,mat,n=48):
    v=[];f=[]
    for y,rx,rz in profile:v.extend((x+rx*math.cos(i*math.tau/n),y,z+rz*math.sin(i*math.tau/n)) for i in range(n))
    for j in range(len(profile)-1):
        for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    return mesh(name,v,[tuple(reversed(face)) for face in f],mat)


def subd(o,level):
    m=o.modifiers.new('Controlled quad surface','SUBSURF');m.levels=level;m.render_levels=level
    return o


SECTIONS=[
 (-3.00,.48,.15,.60,.33),(-2.93,.69,.15,.63,.30),(-2.65,1.08,.18,.69,.28),
 (-2.10,1.34,.34,.77,.29),(-1.50,1.47,.50,.85,.31),(-1.02,1.50,.61,.92,.33),
 (-.35,1.46,.64,.95,.35),(.40,1.57,.64,1.01,.39),(1.00,1.73,.58,1.12,.42),
 (1.42,1.85,.47,1.19,.45),(1.92,1.78,.30,1.17,.49),(2.40,1.51,.20,1.02,.58),
 (2.67,1.27,.18,.88,.64),(2.72,1.20,.18,.85,.64)]
CANOPY=[(-1.24,.51,.93,1.00),(-1.18,.56,.97,1.10),(-.92,.61,.99,1.37),
 (-.52,.63,1.01,1.60),(-.13,.64,1.03,1.69),(.35,.63,1.06,1.70),
 (.70,.59,1.10,1.56),(1.02,.52,1.14,1.34),(1.15,.47,1.16,1.20)]


def shoulder(side,mat,channel_mat):
    """Sculpted body with a true concave rocker trench and a loaded rear shoulder.
    The dark recess is an actual strip of the continuous control mesh, not
    a floating black decal or a straight pipe glued over a capsule.
    """
    v=[];f=[];n=16
    for y,w,inner,top,bot in SECTIONS:
        span=w-inner
        rear_crest=.069*math.exp(-((y-1.46)/.78)**2)
        points=[
            (inner,bot+.075), (inner,top-.09), (inner+.025,top-.03),
            (inner+.12,top+.035), (inner+span*.58,top+.10),
            (inner+span*.77,top+.135+rear_crest),
            (w-.105,top+.10+rear_crest),
            (w-.035,top+.015+rear_crest*.35),
            (w+.014,top-.12), (w-.002,bot+.32),
            (w-.080,bot+.265), (w-.18,bot+.20),
            (w-.205,bot+.16), (w-.075,bot+.085),
            (w-.12,bot+.008), (inner+.06,bot+.015)]
        v.extend((side*x,y,z) for x,z in points)
    for j in range(len(SECTIONS)-1):
        for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    f.extend([tuple(reversed(range(n))),tuple(range((len(SECTIONS)-1)*n,len(SECTIONS)*n))])
    if side<0:f=[tuple(reversed(face)) for face in f]
    o=mesh(('Port' if side<0 else 'Starboard')+' sculpted ceramic shoulder',v,f,mat)
    o.data.materials.append(channel_mat)
    for j in range(len(SECTIONS)-1):
        mid_y=(SECTIONS[j][0]+SECTIONS[j+1][0])*.5
        if -2.4<mid_y<2.48:
            for k in (10,11):o.data.polygons[j*n+k].material_index=1
    # Keep the V2 control sections: level 2 saves approximately 40k triangles
    # across the twin shoulders, with 64 samples around each cross-section.
    return subd(o,2)


def side_intake_cutter(name,side,mat):
    """Closed tapered cutter: long leading knife edge, deep center, rising aft exit."""
    sections=[(-.86,.685,.735),(-.69,.61,.82),(-.35,.565,.89),
              (.19,.565,.94),(.56,.605,.91),(.80,.72,.79)]
    v=[];f=[]
    for y,lo,hi in sections:
        v.extend([(side*1.19,y,lo),(side*2.10,y,lo),
                  (side*2.10,y,hi),(side*1.19,y,hi)])
    f.append((3,2,1,0))
    for j in range(len(sections)-1):
        for i in range(4):
            f.append((j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i))
    f.append(tuple(range((len(sections)-1)*4,len(sections)*4)))
    if side<0:f=[tuple(reversed(q)) for q in f]
    return mesh(name,v,f,mat,False)


def sculpted_rocker(side,mat):
    """Deep, swept lower aerodynamic blade following each lower shoulder."""
    v=[];f=[];sections=SECTIONS[3:13]
    for y,w,inner,top,bot in sections:
        sweep=.055*math.sin((y+2.1)/4.8*math.pi)
        x=w-.095;z=bot+.045+sweep
        v.extend((side*xx,y,zz) for xx,zz in [
            (x-.095,z+.09),(x+.023,z+.027),
            (x+.033,z-.020),(x-.070,z-.075)])
    for j in range(len(sections)-1):
        for i in range(4):f.append((j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i))
    f.extend([(3,2,1,0),tuple(range((len(sections)-1)*4,len(sections)*4))])
    if side<0:f=[tuple(reversed(q)) for q in f]
    return subd(mesh(('Port' if side<0 else 'Starboard')+' swept undercut rocker',v,f,mat),1)


def quarter_haunch(side,mat):
    """Fitted compound-curved rear shoulder fairing, tapered flush at both ends."""
    stations=[(.72,1.31,1.20,.016),(1.05,1.52,1.29,.065),
              (1.43,1.69,1.45,.103),(1.91,1.62,1.39,.087),
              (2.37,1.42,1.18,.014)]
    v=[];f=[]
    for y,x,z,halfwidth in stations:
        for offset,height in [(-halfwidth,-.025),(0,.015),(halfwidth,-.025)]:
            v.append((side*(x+offset),y,z+height))
    for j in range(len(stations)-1):
        for k in range(2):f.append((j*3+k,j*3+k+1,(j+1)*3+k+1,(j+1)*3+k))
    if side<0:f=[tuple(reversed(q)) for q in f]
    o=subd(mesh(('Port' if side<0 else 'Starboard')+' formed rear haunch',v,f,mat),1)
    thick=o.modifiers.new('Fairing bonded edge','SOLIDIFY');thick.thickness=.030
    return o


def race_spear(side,mat):
    """Original jet-age swept cove: raised fitted sheet, not a straight decal.
    Runs above the existing mechanical intake without obscuring it.
    """
    stations=[
        (-2.34,1.11,.756,.007),(-2.08,1.30,.850,.043),
        (-1.61,1.47,.930,.050),(-1.12,1.50,1.025,.036),
        (-.60,1.48,1.055,.020),(.12,1.56,1.125,.025),
        (.70,1.68,1.208,.043),(1.32,1.83,1.280,.053),
        (1.92,1.75,1.225,.044),(2.39,1.48,1.068,.008)]
    vertices=[];faces=[]
    for y,x,z,half in stations:
        vertices.extend([(side*(x-.027),y,z-half),
                         (side*(x+.012),y,z),
                         (side*(x-.027),y,z+half)])
    for j in range(len(stations)-1):
        for k in range(2):
            faces.append((j*3+k,j*3+k+1,(j+1)*3+k+1,(j+1)*3+k))
    if side<0:faces=[tuple(reversed(face)) for face in faces]
    o=subd(mesh(('Port' if side<0 else 'Starboard')+' racing cove spear',vertices,faces,mat),1)
    thick=o.modifiers.new('Pressed cove sheet edge','SOLIDIFY');thick.thickness=.015
    return o



def elliptical_formed_part(name,sections,mat,orientation='Y',resolution=14):
    """Closed, low-cost organically tapered mesh formed from editable elliptical stations.
    Sections are (along_axis, lateral_radius, vertical_or_depth_radius, transverse_center).
    For Y the fourth value is Z center; for Z it is Y center.
    """
    verts=[];faces=[]
    for station,width,depth,center in sections:
        for i in range(resolution):
            angle=math.tau*i/resolution
            if orientation=='Y':
                verts.append((width*math.cos(angle),station,center+depth*math.sin(angle)))
            else:
                verts.append((width*math.cos(angle),center+depth*math.sin(angle),station))
    for j in range(len(sections)-1):
        for i in range(resolution):
            faces.append((j*resolution+i,j*resolution+(i+1)%resolution,
                          (j+1)*resolution+(i+1)%resolution,(j+1)*resolution+i))
    faces.append(tuple(reversed(range(resolution))))
    faces.append(tuple(range((len(sections)-1)*resolution,len(sections)*resolution)))
    return subd(mesh(name,verts,faces,mat),1)


def tapered_seat_cushion(name,x,sections,mat,orientation='Y',resolution=14):
    """Organic cushioned shell with all geometry authored relative to a seat center."""
    v=[];f=[]
    for along,radial,thick,center in sections:
        for i in range(resolution):
            a=math.tau*i/resolution
            if orientation=='Y':
                v.append((x+radial*math.cos(a),along,center+thick*math.sin(a)))
            else:
                v.append((x+radial*math.cos(a),center+thick*math.sin(a),along))
    for j in range(len(sections)-1):
        for i in range(resolution):
            f.append((j*resolution+i,j*resolution+(i+1)%resolution,
                      (j+1)*resolution+(i+1)%resolution,(j+1)*resolution+i))
    f.extend([tuple(reversed(range(resolution))),
              tuple(range((len(sections)-1)*resolution,len(sections)*resolution))])
    return subd(mesh(name,v,f,mat),1)


def racing_strap(name,points,width,mat):
    """Flat belt ribbon with a fitted profile, rather than floating round tubing."""
    vertices=[];faces=[]
    for x,y,z in points:
        vertices.extend([(x-width*.5,y,z),(x+width*.5,y,z)])
    for k in range(len(points)-1):
        faces.append((2*k,2*k+1,2*k+3,2*k+2))
    obj=mesh(name,vertices,faces,mat,False)
    solid=obj.modifiers.new('Woven belt thickness','SOLIDIFY');solid.thickness=.007
    return obj


def formed_racing_seat(x,leather,insert,alloy,shell):
    """Soft ellipsoidal stations shape the base, wraparound back and headrest."""
    label='Driver' if x<0 else 'Co-driver'
    tapered_seat_cushion(label+' continuous formed underpan',x,[
        (-.29,.11,.048,.827),(-.24,.200,.065,.834),
        (-.08,.222,.080,.829),(.20,.219,.080,.835),
        (.40,.184,.070,.863),(.47,.088,.045,.864)],shell)
    tapered_seat_cushion(label+' contoured leather base',x,[
        (-.245,.070,.030,.890),(-.20,.153,.057,.894),
        (-.01,.158,.064,.893),(.24,.153,.061,.905),
        (.40,.103,.035,.917)],leather)
    tapered_seat_cushion(label+' continuous sculpted back shell',x,[
        (.875,.128,.050,.337),(.94,.190,.077,.375),
        (1.13,.213,.082,.484),(1.30,.190,.071,.553),
        (1.43,.162,.061,.568),(1.50,.081,.038,.574)],shell,'Z')
    tapered_seat_cushion(label+' tailored central back pad',x,[
        (.915,.083,.021,.305),(1.00,.135,.051,.327),
        (1.15,.137,.053,.413),(1.31,.128,.046,.493),
        (1.395,.084,.026,.526)],insert,'Z')
    tapered_seat_cushion(label+' rounded head cushion',x,[
        (1.405,.083,.025,.531),(1.435,.137,.067,.544),
        (1.490,.142,.070,.558),(1.533,.092,.041,.565)],leather,'Z')
    for sign in (-1,1):
        wing_x=x+sign*.163
        tapered_seat_cushion(label+' formed thigh bolster '+str(sign),wing_x,[
            (-.21,.028,.023,.917),(-.12,.052,.063,.923),
            (.09,.054,.067,.929),(.27,.049,.059,.944),
            (.405,.025,.022,.946)],leather)
        tapered_seat_cushion(label+' wraparound shoulder bolster '+str(sign),wing_x,[
            (.95,.035,.018,.315),(1.05,.058,.053,.348),
            (1.24,.064,.054,.469),(1.37,.048,.035,.531),
            (1.415,.020,.018,.547)],leather,'Z')
        racing_strap(label+' inset shoulder belt '+str(sign),[
            (x+sign*.102,.555,1.405),(x+sign*.102,.500,1.32),
            (x+sign*.076,.425,1.15),(x+sign*.058,.330,1.035),
            (x+sign*.036,.285,.967)],.031,insert)
        box(label+' belt upper anchor '+str(sign),
            (x+sign*.105,.605,1.415),(.052,.045,.037),alloy,.010)
    for i in range(3):
        yy=-.07+i*.112
        tube(label+' subtle seat upholstery seam '+str(i),[
            (x-.104,yy,.954),(x,yy+.006,.962),(x+.104,yy,.954)],.0035,alloy)
    return label


def shaped_dash(name,mat):
    """One continuous dashboard/bulkhead, with feet bonded to the cockpit floor.
    Longitudinal sections curl into the existing inner sills: no floating bridge.
    """
    vs=[];fs=[]
    # The low front and rear returns enter the cockpit floor at z~0.48,
    # making the dash a supported bulkhead, not a disconnected floating slab.
    cross=[(-1.12,.505),(-1.115,.915),(-1.080,1.049),
           (-.985,1.119),(-.805,1.174),(-.685,1.157),
           (-.640,1.093),(-.670,.785),(-.820,.505)]
    xs=[-.64,-.622,-.54,-.40,-.20,0,.20,.40,.54,.622,.64]
    N=len(cross)
    for x in xs:
        edge=max(0, (abs(x)-.39)/.25)
        for y,z in cross:
            # Taper the dash outer tips down into the side walls.
            vs.append((x,y+.018*edge,z-.135*edge))
    for j in range(len(xs)-1):
        for k in range(N):
            fs.append((j*N+k,j*N+(k+1)%N,(j+1)*N+(k+1)%N,(j+1)*N+k))
    fs.extend([tuple(reversed(range(N))),
               tuple(range((len(xs)-1)*N,len(xs)*N))])
    return subd(mesh(name,vs,fs,mat),1)


def contoured_door_side(side,mat):
    """Fitted curved interior kick panel with integrated armrest shelf."""
    outline=[
        (-.68,.535,.806,.975),(-.54,.555,.795,1.010),
        (-.21,.579,.799,1.028),(.16,.588,.804,1.035),
        (.47,.566,.816,1.037),(.74,.527,.825,.994)]
    vs=[];fs=[]
    # Per-station, U-shaped five point span: longitudinal rounded side-pad.
    for y,x,zlow,zhigh in outline:
        for xx,zz in [(x-.047,zlow),(x-.064,zlow+.045),
                      (x-.070,zhigh-.067),(x-.045,zhigh),
                      (x+.009,zhigh-.042),(x+.020,zlow+.036)]:
            vs.append((side*xx,y,zz))
    N=6
    for j in range(len(outline)-1):
        for i in range(N):
            fs.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
    fs.extend([tuple(reversed(range(N))),
               tuple(range((len(outline)-1)*N,len(outline)*N))])
    if side<0:fs=[tuple(reversed(face)) for face in fs]
    return subd(mesh(('Port' if side<0 else 'Starboard')+' contoured cockpit interior wall',
                     vs,fs,mat),1)


def competition_gauge_pod(x,z,black,alloy,glow):
    """A small recessed dual gauge pod seated into the continuous dashboard."""
    # Low-profile black formed binnacle embedded in its upper aft-facing wall.
    ellipse_shell('Integrated driver dial enclosure',x,z,[
        (-.760,.258,.140),(-.684,.248,.135),(-.603,.231,.125),
        (-.575,.211,.114)],black,32)
    for idx,(cx,r) in enumerate([(-.365,.072),(-.194,.064)]):
        cylinder('Integrated dial dark recess '+str(idx),
                 (cx,-.565,1.135),r,.017,black,28,'Y')
        cylinder('Integrated dial champagne rim '+str(idx),
                 (cx,-.552,1.135),r*1.01,.011,alloy,28,'Y')
        cylinder('Integrated dial smoked blue face '+str(idx),
                 (cx,-.539,1.135),r*.83,.009,glow,28,'Y')
        tube('Integrated dial needle '+str(idx),[
            (cx,-.531,1.135),(cx+r*.45,-.524,1.156)],.004,alloy)


def fitted_cockpit_console(mat,leather,alloy):
    """A single narrow console blending down into the floor between the seats."""
    tapered_seat_cushion('Cockpit flowing center console',0,[
        (-.635,.065,.044,.816),(-.50,.090,.079,.830),
        (-.29,.103,.091,.831),(-.05,.105,.094,.829),
        (.24,.113,.091,.825),(.54,.095,.080,.827),
        (.70,.054,.044,.823)],mat)
    tapered_seat_cushion('Cockpit tapered padded center armrest',0,[
        (.22,.047,.024,.906),(.31,.083,.035,.912),
        (.48,.087,.047,.912),(.61,.052,.024,.906)],leather)
    cylinder('Cockpit inset selector bezel',(0,-.297,.939),.054,.018,alloy,24)
    cylinder('Cockpit inset selector knob',(0,-.297,.951),.030,.022,mat,20)

def center_patch(name,rows,mat,subdivision=2):
    v=[];f=[];n=11
    for y,w,z in rows:
        for i in range(n):
            t=-1+2*i/(n-1);v.append((w*t,y,z-.045*t*t))
    for j in range(len(rows)-1):
        for i in range(n-1):f.append((j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i))
    o=subd(mesh(name,v,f,mat),subdivision)
    m=o.modifiers.new('Fitted panel thickness','SOLIDIFY');m.thickness=.045
    return o


def canopy_surface(mat):
    v=[];f=[];n=25
    for y,w,edge,peak in CANOPY:
        for i in range(n):
            t=-math.pi/2+math.pi*i/(n-1);v.append((w*math.sin(t),y,edge+(peak-edge)*max(0,1-abs(math.sin(t))**4)))
    for j in range(len(CANOPY)-1):
        for i in range(n-1):f.append((j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i))
    o=subd(mesh('Canopy smoked sapphire glazing',v,f,mat),2)
    m=o.modifiers.new('Laminated glazing thickness','SOLIDIFY');m.thickness=.012
    return o


def stats(objects):
    dg=bpy.context.evaluated_depsgraph_get();total=0;groups={}
    for o in objects:
        e=o.evaluated_get(dg);m=e.to_mesh();count=sum(len(p.vertices)-2 for p in m.polygons);e.to_mesh_clear()
        total+=count
        group='body' if any(t in o.name.lower() for t in ('ceramic','hood','keel','spine','fin')) else 'cockpit' if any(t in o.name.lower() for t in ('canopy','seat','dash','telemetry','yoke')) else 'propulsion_lighting'
        groups[group]=groups.get(group,0)+count
    return total,groups


def detail_budget(objects):
    """Rank evaluated object costs to guide future silhouette-preserving LOD work."""
    dg=bpy.context.evaluated_depsgraph_get()
    entries=[]
    for o in objects:
        evaluated=o.evaluated_get(dg)
        m=evaluated.to_mesh()
        count=sum(max(0,len(poly.vertices)-2) for poly in m.polygons)
        evaluated.to_mesh_clear()
        entries.append({'object':o.name,'triangles':count})
    return sorted(entries,key=lambda item:item['triangles'],reverse=True)


def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]


def export(path,objects):
    select(objects);bpy.ops.export_scene.gltf(filepath=os.path.abspath(path),export_format='GLB',use_selection=True,export_apply=True)


def build(out,shape_check=False):
    os.makedirs(out,exist_ok=True);bpy.context.preferences.filepaths.save_version=0
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    ivory=material('01 Porcelain titanium ceramic',(.72,.76,.73),.42,.27)
    teal=material('02 Midnight petrol composite',(.018,.065,.084),.65,.31)
    black=material('03 Graphite mechanisms',(.016,.023,.030),.68,.34)
    silver=material('04 Satin titanium',(.33,.40,.44),.82,.26)
    violet=material('05 Violet field emission',(.30,.045,1),.15,.22,4)
    white=material('06 Ice white lamps',(.52,.90,1),.1,.22,5)
    amber=material('07 Amber rear lamps',(1,.18,.035),.1,.28,3)
    glass=material('08 Smoked sapphire canopy',(.027,.10,.15),.22,.13,0,.66)
    upholstery=material('09 Petrol seat fabric',(.04,.095,.11),.05,.72)
    gold=material('10 Warm brass badge',(.58,.35,.11),.78,.31)
    ivory_leather=material('11 Ivory tailored seat leather',(.71,.67,.56),.05,.73)
    navy_leather=material('12 Dark blue racing seat leather',(.034,.073,.116),.04,.64)
    champagne=material('13 Satin champagne alloy',(.55,.43,.29),.75,.31)
    instrument=material('14 Blue instrument luminescence',(.18,.63,.84),.13,.23,2.4)
    body=[shoulder(-1,ivory,black),shoulder(1,ivory,black)]
    # Apply the organic control surfaces before cutting true through-body lift wells.
    for ob in body:
        apply(ob,ob.modifiers[0])
        side=-1 if ob.name.startswith('Port') else 1
        for label,x,y,r,top in [('Fore',1.03,-1.70,.295,.94),('Aft',1.20,1.31,.35,1.28)]:
            cutter=cylinder('TEMP lift aperture',(side*x,y,.8),r,2.5,black,64)
            m=ob.modifiers.new(label+' lift well aperture','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
            apply(ob,m);bpy.data.objects.remove(cutter,do_unlink=True)
        cutter=side_intake_cutter('TEMP tapered side intake',side,black)
        m=ob.modifiers.new('Deep tapered side intake','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
        apply(ob,m);bpy.data.objects.remove(cutter,do_unlink=True)
        b=ob.modifiers.new('Lift aperture edge break' ,'BEVEL');b.width=.009;b.segments=2;b.limit_method='ANGLE';b.angle_limit=.7
    # A continuous dark belly supplies a real cockpit floor and a tapered, raised tail.
    keel=center_patch('Composite center keel',[(y,w*.81,bot+.13) for y,w,inner,top,bot in SECTIONS],teal,2)
    for mod in list(keel.modifiers):apply(keel,mod)
    for side in (-1,1):
        for x,y,r in [(1.03,-1.70,.295),(1.20,1.31,.35)]:
            cutter=cylinder('TEMP belly lift passage',(side*x,y,.6),r,2.5,black,64)
            m=keel.modifiers.new('Open belly lift passage','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
            apply(keel,m);bpy.data.objects.remove(cutter,do_unlink=True)
    box('Front graphite chin bridge',(0,-2.94,.405),(1.07,.20,.11),teal,.045)
    center_patch('Sculpted split hood' ,[(y,inner+.075,top+.035) for y,w,inner,top,bot in SECTIONS[:6]],ivory,2)
    center_patch('Rear ceramic bridge',[(y,inner+.12,top+.04) for y,w,inner,top,bot in SECTIONS[8:]],ivory,2)
    center_patch('Rear dorsal spine',[(.96,.11,1.22),(1.10,.12,1.28),(1.65,.10,1.31),(2.20,.075,1.19),(2.62,.055,.98)],teal,2)
    canopy_surface(glass)
    for side,label in [(-1,'Port'),(1,'Starboard')]:
        sculpted_rocker(side,teal)
        quarter_haunch(side,ivory)
        race_spear(side,champagne)
        # A two-tone jet-age accent sweeps the upper fender above the intake.
        tube(label+' racing cove shadow line',[
            (side*1.28,-2.07,.81),(side*1.45,-1.62,.88),
            (side*1.50,-1.10,.98),(side*1.48,-.57,1.02),
            (side*1.63,.65,1.16),(side*1.81,1.32,1.23),
            (side*1.71,1.94,1.18)],.0075,teal)
        tube(label+' rear haunch inset seam',[(side*1.31,.76,1.225),(side*1.53,1.08,1.325),
             (side*1.69,1.46,1.48),(side*1.62,1.92,1.42),(side*1.43,2.35,1.205)],.009,teal)
        tube(label+' canopy compression seal',[(side*w,y,z+.006) for y,w,z,p in CANOPY],.026,black)
        tube(label+' ceramic canopy sill',[(side*(w+.036),y,z-.025) for y,w,z,p in CANOPY],.018,ivory)
        # The open intake has a recessed backing tray, leaned splitters and a
        # continuous upper lip; the geometry follows the actual tapered cut.
        box(label+' intake shadow plenum',(side*1.174,-.025,.735),(.045,1.32,.31),black,.025)
        for yy,height in [(-.53,.15),(-.23,.245),(.12,.275),(.46,.24)]:
            box(label+' canted intake splitter',(side*1.37,yy,.73),(.20,.028,height),silver,.010,(-.12,0,-.17))
        tube(label+' sculpted intake eyebrow',[(side*1.50,-.80,.76),(side*1.49,-.63,.855),
            (side*1.49,-.30,.93),(side*1.53,.23,.98),(side*1.62,.67,.94)],.027,teal)
        tube(label+' lower intake sill',[(side*1.48,-.70,.58),(side*1.49,-.35,.54),
            (side*1.52,.20,.54),(side*1.61,.70,.66)],.022,silver)
        tube(label+' recessed intake field core',[(side*1.21,-.53,.615),
            (side*1.21,-.16,.60),(side*1.21,.30,.61),(side*1.21,.60,.69)],.011,violet)
        # Headlamps sit in molded front corner channels.
        lamp=[(side*.76,-2.70,.77),(side*.98,-2.53,.82),(side*1.15,-2.24,.86)]
        tube(label+' front lamp recess',lamp,.034,black);tube(label+' front lamp emitter',[(x,y-.006,z+.018) for x,y,z in lamp],.012,white)
        # Continuous lower accent traces the actual side chine and the forward pitch.
        rocker_trace=[(side*1.18,-2.10,.37),(side*1.39,-1.50,.40),
                      (side*1.40,-.35,.45),(side*1.51,.42,.49),
                      (side*1.67,1.14,.55),(side*1.68,1.86,.63),
                      (side*1.43,2.38,.72)]
        tube(label+' recessed rocker shadow lip',rocker_trace,.030,black)
        tube(label+' lower energy filament',[(x+side*.022,y,z+.005) for x,y,z in rocker_trace],.011,violet)
        tube(label+' rear lamp recess',[(side*.74,2.47,1.02),(side*1.10,2.47,1.04),(side*1.39,2.26,1.10)],.032,black)
        tube(label+' rear tail lamp',[(side*.74,2.485,1.035),(side*1.10,2.485,1.055),(side*1.39,2.275,1.115)],.011,amber)
        # Solid roots and a thin trailing tip create a swept split tail, not add-on boxes.
        fin_rows=[(1.46,.80,.15,1.18),(1.58,.88,.20,1.24),(2.12,1.14,.18,1.40),(2.53,1.33,.07,1.43),(2.61,1.37,.015,1.40)]
        vv=[];ff=[]
        for y,x,w,z in fin_rows:
            vv.extend([(side*(x-w),y,z-.05),(side*(x+w),y,z-.035),(side*(x+w),y,z+.015),(side*(x-w),y,z+.045)])
        for j in range(len(fin_rows)-1):
            for k in range(4):ff.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
        ff += [(3,2,1,0),tuple(range((len(fin_rows)-1)*4,len(fin_rows)*4))]
        subd(mesh(label+' sculpted split tail fin',vv,ff,ivory),2)
        # Flattened oval drive ports nest into the rear body under the split stabilizers.
        tx=side*.67
        ellipse_shell(label+' oval drive housing',tx,.68,[(2.31,.34,.20),(2.43,.375,.225),(2.70,.375,.225),(2.84,.35,.20),(2.84,.29,.145),(2.74,.285,.14),(2.43,.25,.12)],black)
        ellipse_shell(label+' satin drive terminal',tx,.68,[(2.72,.38,.23),(2.80,.38,.23),(2.85,.35,.20),(2.85,.29,.145),(2.80,.29,.145)],silver)
        ellipse_shell(label+' recessed drive field',tx,.68,[(2.68,.26,.125),(2.69,.26,.125),(2.69,.24,.11)],violet)
        for i in range(7):
            x=tx-.22+i*.073
            box(label+' drive stator',(x,2.59,.68),(.018,.19,.20),silver,.006)
        ellipse_shell(label+' drive machined throat',tx,.68,
            [(2.73,.287,.138),(2.78,.302,.147),(2.815,.310,.151)],champagne,32)
        ellipse_shell(label+' drive deep ion collar',tx,.68,
            [(2.65,.19,.092),(2.685,.20,.099),(2.705,.192,.094)],violet,32)
        # Four integrated vertical lift ducts, with open wells and recessed stator fans.
        for pos,x,y,r,top in [('Fore',1.03,-1.70,.295,.94),('Aft',1.20,1.31,.35,1.28)]:
            x*=side;bottom=.21 if pos=='Fore' else .28
            radial_shell(label+' '+pos+' recessed lift well',x,y,[(bottom,r*.94),(top-.04,r*.99),(top,r),(top+.018,r*.94),(top+.018,r*.85),(top-.10,r*.84),(bottom,r*.84)],black)
            radial_shell(label+' '+pos+' titanium duct lip',x,y,[(top-.01,r*1.01),(top+.012,r*1.01),(top+.025,r*.94),(top+.012,r*.88)],silver)
            radial_shell(label+' '+pos+' violet lift coil',x,y,[(bottom+.02,r*.87),(bottom+.04,r*.87),(bottom+.04,r*.80)],violet)
            cylinder(label+' '+pos+' stator hub',(x,y,top-.08),r*.22,.09,silver,32)
            for i in range(10):
                a=math.tau*i/10
                points=[]
                for rr,aa,zz in [(r*.22,a,top-.07),(r*.81,a+.23,top-.10),(r*.82,a+.37,top-.12),(r*.24,a+.21,top-.10)]:
                    points.append((x+rr*math.cos(aa),y+rr*math.sin(aa),zz))
                vane=mesh(label+' '+pos+' curved stator vane',points,[(0,1,2,3)],teal)
                m=vane.modifiers.new('Stator vane thickness','SOLIDIFY');m.thickness=.016
    # Curved canopy cross frames define the glass perimeter without a separate bubble.
    for idx in (1,6):
        y,w,edge,peak=CANOPY[idx]
        tube('Canopy formed arch '+str(idx),[(w*math.sin(t),y,edge+(peak-edge)*max(0,1-abs(math.sin(t))**4)+.008) for t in [-math.pi/2+math.pi*i/18 for i in range(19)]],.018,teal)
    # Cockpit V4: fitted control meshes replace isolated beveled block volumes.
    # The dashboard is a full structural fairing anchored at y=-1.12, with
    # continuous returns into the side walls; instruments are inset aft.
    shaped_dash('Cockpit integrated jet-age dashboard shell',teal)
    for side,label in [(-1,'Port'),(1,'Starboard')]:
        contoured_door_side(side,navy_leather)
        tube(label+' cockpit armrest metal inset',[
            (side*.515,-.52,.982),(side*.520,-.23,1.005),
            (side*.521,.18,1.012),(side*.523,.52,1.007)],.008,champagne)
    for x in (-.265,.265):
        formed_racing_seat(x,ivory_leather,navy_leather,champagne,teal)
    fitted_cockpit_console(teal,ivory_leather,champagne)
    competition_gauge_pod(-.278,1.135,black,champagne,instrument)
    # The steering column is physically attached to the aft-facing binnacle.
    tube('Driver anchored steering column',[
        (-.265,-.584,1.10),(-.265,-.502,1.11),(-.265,-.420,1.131)],.022,silver)
    wheel_x=-.265
    wheel_points=[(wheel_x+.138*math.cos(a),-.379,1.130+.138*math.sin(a))
                  for a in [math.tau*i/24 for i in range(24)]]
    tube('Driver slim heritage competition wheel',wheel_points,.012,champagne,True)
    cylinder('Driver leather steering hub',(wheel_x,-.390,1.130),.037,.038,navy_leather,24,'Y')
    for a in (math.pi/2,math.pi*7/6,math.pi*11/6):
        tube('Driver mounted steering spoke',[(wheel_x,-.375,1.13),
             (wheel_x+.129*math.cos(a),-.375,1.13+.129*math.sin(a))],.0085,silver)
    tube('Passenger flowing dash reveal',[(.055,-.642,1.137),(.25,-.646,1.143),
         (.46,-.657,1.112),(.60,-.702,1.035)],.008,champagne)
    for i in range(4):
        box('Cockpit recessed tactile toggles '+str(i),
             (.06+i*.037,-.615,1.082),(.018,.022,.014),champagne,.004)
    tube('Hood central inset',[(0,-2.85,.69),(0,-2.40,.75),(0,-1.78,.85),(0,-1.12,.96)],.012,teal)
    text=bpy.data.curves.new('Parallax badge glyphs','FONT');text.body='PARALLAX';text.align_x='CENTER';text.size=.075;text.extrude=.001
    ob=bpy.data.objects.new('Parallax hood identification',text);bpy.context.collection.objects.link(ob);ob.location=(0,-2.02,.83);ob.data.materials.append(gold)
    # Freeze all curves as editable meshes; recalculate consistent normals before export.
    for o in list(bpy.context.scene.objects):
        if o.type in ('CURVE','FONT'):
            select([o]);bpy.ops.object.convert(target='MESH')
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for o in objects:
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
        if hasattr(o.data,'use_auto_smooth'):
            o.data.use_auto_smooth=True;o.data.auto_smooth_angle=math.radians(50)
    total,groups=stats(objects)
    heavy=detail_budget(objects)
    print('PARALLAX_BUDGET',json.dumps({'total':total,'assemblies':groups,
                                      'top_meshes':heavy[:20]}),flush=True)
    if not 0<total<=120000:raise RuntimeError('Parallax exceeds 120k triangle budget: '+str(total))
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT' if bpy.app.version>=(4,2,0) else 'BLENDER_EEVEE'
    if hasattr(scene,'eevee'):
        for key,value in {'taa_render_samples':40,'use_gtao':True,'gtao_distance':.35,'gtao_factor':1.25}.items():
            if hasattr(scene.eevee,key):setattr(scene.eevee,key,value)
    scene.world.use_nodes=True;world=scene.world.node_tree.nodes.get('Background');world.inputs['Color'].default_value=(.16,.20,.26,1);world.inputs['Strength'].default_value=.5
    floor=material('STUDIO floor',(.055,.074,.095),.25,.58)
    box('STUDIO floor',(0,0,.035),(200,200,.08),floor,0)
    def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    for loc,energy,color,size in [((2,-4,7),1800,(.80,.90,1),5),((-5,1,4),1600,(.48,.65,1),5),((4,5,5),2100,(1,.76,.50),4)]:
        bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=energy;l.data.color=color;l.data.shape='DISK';l.data.size=size;aim(l,(0,0,.8))
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
    scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    views=[('hero_3q',(8,-10,5.6),(0,-.05,.95),8.6),('front',(0,-12,1.2),(0,0,1),5.2),
           ('side',(12,-.1,1.35),(0,-.1,1),7.2),('rear_3q',(8,10,4.8),(0,.3,.9),8.3),
           ('rear',(0,12,1.2),(0,0,1),5.2),('top',(0,-.1,12),(0,-.1,0),9.1),
           ('cockpit',(3,-3,3.7),(0,-.05,1.15),3.3),('chase',(0,10,4.4),(0,0,.9),7.7),
           ('interior_open',(2.35,-1.58,3.05),(0,.05,1.08),2.55),
           ('instruments',(1.12,-1.85,1.92),(-.18,-.47,1.17),1.58)]
    if shape_check:
        scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.display.shading.show_shadows=False
        scene.render.resolution_x=960;scene.render.resolution_y=720
        for name,loc,target,scale in [views[0],views[2],views[5]]:
            cam.location=loc;cam.data.ortho_scale=scale;aim(cam,target);scene.render.filepath=os.path.abspath(os.path.join(out,'parallax_'+name+'_shape.png'));bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(out,'parallax_shape_check.blend')))
        print('PARALLAX_SHAPE_CHECK_OK');return
    # Smart UVs support downstream texture authoring; the PBR factors are portable today.
    for o in objects:
        select([o]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
    glb=os.path.join(out,'parallax_01.glb');export(glb,objects)
    lods={'LOD0':total}
    for name,ratio,cutoff,budget in [('LOD1',.32,.035,45000),('LOD2',.10,.09,20000)]:
        dg=bpy.context.evaluated_depsgraph_get();copies=[]
        for original in objects:
            if max(original.dimensions)<cutoff:continue
            o=original.copy();o.data=bpy.data.meshes.new_from_object(original.evaluated_get(dg),depsgraph=dg);o.modifiers.clear();bpy.context.collection.objects.link(o)
            if len(o.data.polygons)>32:
                m=o.modifiers.new(name+' evaluated reduction','DECIMATE');m.ratio=(max(ratio,.28) if 'glazing' in original.name else ratio);m.use_collapse_triangulate=True
            copies.append(o)
        count,_=stats(copies)
        if not 0<count<=budget:raise RuntimeError(name+' budget exceeded: '+str(count))
        export(os.path.join(out,'parallax_01_'+name.lower()+'.glb'),copies);lods[name]=count
        for o in copies:
            d=o.data;bpy.data.objects.remove(o,do_unlink=True)
            if d.users==0:bpy.data.meshes.remove(d)
    # Save the source with a useful hero camera; studio objects are never exported.
    cam.location=views[0][1];cam.data.ortho_scale=views[0][3];aim(cam,views[0][2]);bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(out,'parallax_01.blend')))
    glazing=[o for o in objects if 'Canopy smoked sapphire glazing' in o.name]
    for name,loc,target,scale in views:
        # Cutaway views only: actual Blender vehicle geometry remains unchanged.
        # Hide just the glass, not the seals or cabin structure, for inspection.
        for o in glazing:o.hide_render=name in ('interior_open','instruments')
        cam.location=loc;cam.data.ortho_scale=scale;aim(cam,target)
        scene.render.filepath=os.path.abspath(os.path.join(out,'parallax_01_'+name+'.png'))
        bpy.ops.render.render(write_still=True)
    for o in glazing:o.hide_render=False
    proxy=[]
    for y,w,length,z,height in [(-2.10,1.15,1.7,.52,.50),(-.35,1.44,2.1,.70,.90),(1.65,1.65,2.0,.78,.85)]:
        proxy.append(box('COLLISION Parallax hull',(0,y,z),(w*2,length,height),black,0))
    proxy.append(box('COLLISION canopy',(0,.05,1.44),(1.20,2.05,.70),black,0))
    collision,_=stats(proxy);export(os.path.join(out,'parallax_01_collision.glb'),proxy)
    for o in proxy:bpy.data.objects.remove(o,do_unlink=True)
    record={'asset_id':'parallax_01_hover_coupe','display_name':'Parallax / 01',
      'generator':'Parallax v4: organically lofted seats, bonded dashboard and cutaway cockpit detailing',
      'blender_version':bpy.app.version_string, 'prompt':'Create an original Parallax two-seat jet-age hover racer. Its existing sculpted silhouette recalls late-1950s American competition roadsters, especially the photographed 1957 Corvette SS XP-64, without replicating protected marks or exact bodywork. Preserve long porcelain shoulders, the blue canopy, four vertical lift ducts and paired rear drives. Add fitted sweeping racing coves, compact luxurious competition seating, period-inspired circular driver gauges, a polished competition steering rim, a tailored two-seat center console, subdued champagne brightwork and richer jet-derived drive interiors. Keep the racer athletic and elegant, never a lounge-style luxury sedan.',
      'negative_prompt':'No wheels, no primitive boxes as the main body, no weapons, no paid provider assets, no studio geometry in exports.',
       'v2_surface_design':['continuous concave rocker control mesh','swept dark lower aero blade',
                            'deep tapered side intake with backing plenum','loaded shoulder-to-rear haunch control surfaces',
                            'formed rear quarter fairing and molded trailing shoulder'],
       'v3_reference_direction':'Original hover racer with broad jet-age cues from 1957 American competition roadsters, not an exact replica',
       'v3_assemblies':['fitted racing cove spears','rear drive machined throats',
                         'tailored two-seat competition buckets','center console and selector',
                         'retro-futurist analogue driver instruments','competition wheel',
                         'premium cabin side upholstery and brightwork'],
       'v4_cockpit_rebuild':['station-lofted cushion and integrated headrest',
                             'contoured seat backs and side bolsters','flat shoulder belts',
                             'continuous full-depth dashboard/bulkhead',
                             'embedded cockpit gauge pod and mounted steering column',
                             'one-piece formed center console','formed cabin door-side pads'],
      'reference_images':[], 'axis_convention':{'forward':'-Y','right':'+X','up':'+Z'},
      'game_target':{'engine':'Godot','triangle_budget':120000,'triangle_count':total,
                      'assembly_triangles':groups,'top_meshes':heavy[:20],
                      'lods':lods,'collision_triangles':collision},
      'geometry_optimization':{'shoulder_subdivision':2,'lift_ring_segments':48,
                                'rear_ellipse_segments':48,'budget_scope':'evaluated mesh before renders'},
      'materials':'Portable glTF PBR color/metal/roughness/emission factors; transparent canopy. Smart-projected UVs. No high-to-low or AO baking.',
      'views':[v[0] for v in views], 'validation_scope':'Evaluated/export budgets and static mesh artifacts; no engine driving or LOD-transition validation.',
      'license':'Original procedural geometry; repository distribution license not yet declared.'}
    with open(os.path.join(out,'parallax_01_training_record.json'),'w') as f:json.dump(record,f,indent=2)
    print('PARALLAX_BUILD_OK',json.dumps({'lods':lods,'collision':collision,'glb_bytes':os.path.getsize(glb)}),flush=True)


if __name__=='__main__':
    a=args();build(a.output_dir,a.shape_check)
