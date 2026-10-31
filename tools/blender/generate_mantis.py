"""Build the Assetwright Mantis MK I exposed-frame hover racer.

Deterministic, editable Blender geometry for a model-generation training exemplar.
Axes: nose is -Y, rear is +Y, up is +Z. Outputs a game-ready GLB, five review
views, contact sheet, and a machine-readable prompt/feature record.
"""
import argparse
import json
import math
import os
import random
import sys
from array import array
import bpy
import bmesh
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="generated")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def mat(name, color, metallic=0.25, roughness=0.45, emission=0.0):
    """Portable authored PBR maps; no render-only noise shader or fake baked AO."""
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    nodes,links=m.node_tree.nodes,m.node_tree.links; bsdf=nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*color,1)
    bsdf.inputs["Metallic"].default_value=metallic
    bsdf.inputs["Roughness"].default_value=roughness
    if emission:
        c=bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        e=bsdf.inputs.get("Emission Strength")
        if c: c.default_value=(*color,1)
        if e: e.default_value=emission
        return m
    size=256; rng=random.Random(name); base=array("f"); rough=array("f"); normals=array("f")
    # Fine coating grain, directional brushing and sparse pinprick chips.
    # Avoid the earlier oversized random dark strokes repeated across every part.
    textile="upholstery" in name; brushed="titanium" in name
    for y in range(size):
        row=rng.uniform(-.025,.025) if brushed else 0
        for x in range(size):
            grain=rng.uniform(-.025,.025)
            broad=.018*math.sin(x*.045)*math.sin(y*.067)
            weave=.018*math.sin(x*math.pi/2)*math.sin(y*math.pi/2) if textile else 0
            chip=rng.random()<.0015 and "olive" in name
            shade=1+grain+broad+row+weave
            rgb=tuple(c*shade for c in color)
            if chip: rgb=tuple(c*.80+.045 for c in color)
            base.extend((*rgb,1))
            r=max(.08,min(.90,roughness+grain*1.8+broad+row+(.10 if chip else 0)))
            rough.extend((r,r,r,1))
            nx=.5+(weave*.35 if textile else grain*.12)
            ny=.5+(row*.35 if brushed else grain*.12)
            normals.extend((nx,ny,1,1))
    def texture(label,pixels,data=False):
        im=bpy.data.images.new(name+" | "+label,width=size,height=size,alpha=False)
        if data: im.colorspace_settings.name="Non-Color"
        im.pixels.foreach_set(pixels); im.pack()
        node=nodes.new("ShaderNodeTexImage");node.image=im;node.label=label
        return node
    albedo=texture("coating albedo",base)
    links.new(albedo.outputs["Color"],bsdf.inputs["Base Color"])
    rough_tex=texture("surface roughness",rough,True)
    links.new(rough_tex.outputs["Color"],bsdf.inputs["Roughness"])
    normal_tex=texture("micro surface normal",normals,True)
    normal=nodes.new("ShaderNodeNormalMap");normal.inputs["Strength"].default_value=.35
    links.new(normal_tex.outputs["Color"],normal.inputs["Color"])
    links.new(normal.outputs["Normal"],bsdf.inputs["Normal"])
    return m


def box(name, loc, dims, material, bevel=0.04, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bevel:
        b = o.modifiers.new("Machined corner radii", "BEVEL")
        b.width = bevel
        b.segments = 2 if max(dims)<.16 else 3
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=b.name)
    o.modifiers.new("Weighted hard-surface normals", "WEIGHTED_NORMAL")
    return o


def rod(name, a, b, radius, material, vertices=16, radius2=None):
    a, b = Vector(a), Vector(b)
    v = b-a
    mid = (a+b)*0.5
    if radius2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=v.length, location=mid)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=radius2, depth=v.length, location=mid)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = v.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(material)
    o.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return o


def cyl(name, loc, radius, depth, material, axis="Z", vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o=bpy.context.object; o.name=name; o.data.materials.append(material)
    direction={"X":(0,math.pi/2,0),"Y":(math.pi/2,0,0),"Z":(0,0,0)}[axis]
    o.rotation_euler=direction
    o.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return o


def torus(name, loc, major, minor, material, axis="Z"):
    bpy.ops.mesh.primitive_torus_add(major_segments=32, minor_segments=(6 if minor<.025 else 8), major_radius=major, minor_radius=minor, location=loc)
    o=bpy.context.object; o.name=name; o.data.materials.append(material)
    o.rotation_euler={"X":(0,math.pi/2,0),"Y":(math.pi/2,0,0),"Z":(0,0,0)}[axis]
    for face in o.data.polygons: face.use_smooth=True
    return o


def beam_between(name, a, b, width, material, depth=None, bevel=0.02):
    a,b=Vector(a),Vector(b); d=b-a; mid=(a+b)*.5
    o=box(name, mid, (width, depth or width, d.length), material, bevel)
    o.rotation_euler=d.to_track_quat("Z","Y").to_euler()
    return o


def swept_plate(name, start, end, width_root, width_tip, z, thickness, material):
    """Tapered, swept polygonal armor plate following an articulated arm."""
    a=Vector((start[0],start[1],0)); b=Vector((end[0],end[1],0))
    side=Vector((-(b-a).y,(b-a).x,0)).normalized()
    points=[a+side*width_root,b+side*width_tip,b-side*width_tip,a-side*width_root]
    verts=[(p.x,p.y,z-thickness*.5) for p in points]+[(p.x,p.y,z+thickness*.5) for p in points]
    faces=[(0,1,2,3),(7,6,5,4)]
    for i in range(4): faces.append((i,(i+1)%4,(i+1)%4+4,i+4))
    me=bpy.data.meshes.new(name+" mesh"); me.from_pydata(verts,[],faces); me.materials.append(material); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
    bevel=ob.modifiers.new("Armored tapered edge breaks","BEVEL"); bevel.width=min(.025,thickness*.24); bevel.segments=3
    ob.modifiers.new("Weighted plate normals","WEIGHTED_NORMAL")
    return ob


def swept_fin(name, side, material):
    """Extruded swept vertical tail fin, profiled in the rear/vertical plane."""
    profile=[(1.08,1.42),(1.37,2.28),(1.78,2.57),(2.34,2.62),(2.12,1.53)]
    x0=side*.84; x1=side*1.02
    verts=[(x0,y,z) for y,z in profile]+[(x1,y,z) for y,z in profile]
    faces=[tuple(range(5)),tuple(reversed(range(5,10)))]
    for i in range(5): faces.append((i,(i+1)%5,(i+1)%5+5,i+5))
    me=bpy.data.meshes.new(name+" mesh"); me.from_pydata(verts,[],faces); me.materials.append(material); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
    bevel=ob.modifiers.new("Tail-fin machined edge","BEVEL"); bevel.width=.035; bevel.segments=3
    ob.modifiers.new("Weighted fin normals","WEIGHTED_NORMAL")
    return ob


def make_hover_cell(x, y, z, scale, label, mats):
    armor, black, titanium, glow, gold = mats
    # Layered magnetic-disc housing; top is visible from the 3/4 camera.
    cyl(label+" armored lower shroud", (x,y,z), .58*scale, .30*scale, black, "Z", 48)
    cyl(label+" segmented side belt", (x,y,z+.02*scale), .53*scale, .20*scale, armor, "Z", 48)
    torus(label+" outer titanium bumper", (x,y,z-.015*scale), .55*scale, .045*scale, titanium)
    torus(label+" luminous lift ring", (x,y,z-.105*scale), .49*scale, .034*scale, glow)
    torus(label+" upper locking ring", (x,y,z+.13*scale), .47*scale, .022*scale, gold)
    cyl(label+" recessed emitter well", (x,y,z+.17*scale), .34*scale, .07*scale, black, "Z", 40)
    cyl(label+" ceramic emitter face", (x,y,z+.215*scale), .27*scale, .035*scale, glow, "Z", 40)
    cyl(label+" central magnetic cap", (x,y,z+.24*scale), .13*scale, .06*scale, titanium, "Z", 32)
    for i in range(14):
        a=math.tau*i/14
        px=x+math.cos(a)*.51*scale; py=y+math.sin(a)*.51*scale
        cyl(label+" rim fastener %02d"%i, (px,py,z+.16*scale), .025*scale, .035*scale, gold, "Z", 12)
    for i in range(12):
        a=math.tau*i/12
        px=x+math.cos(a)*.39*scale; py=y+math.sin(a)*.39*scale
        rod(label+" emitter vane %02d"%i,(px,py,z+.25*scale),(x+math.cos(a+.18)*.26*scale,y+math.sin(a+.18)*.26*scale,z+.25*scale),.018*scale,titanium,8)
    # Segmented armored skirt and individually recessed cooling slots.
    for i in range(14):
        a=math.tau*i/14
        rx,ry=math.cos(a),math.sin(a)
        px=x+rx*.535*scale; py=y+ry*.535*scale
        box(label+" skirt armor segment %02d"%i,(px,py,z+.02*scale),(.065*scale,.235*scale,.145*scale),armor,.014*scale,(0,0,a))
        sx=x+rx*.577*scale; sy=y+ry*.577*scale
        box(label+" skirt cooling slot %02d"%i,(sx,sy,z+.02*scale),(.018*scale,.072*scale,.036*scale),black,.004*scale,(0,0,a))
        cyl(label+" skirt latch %02d"%i,(x+rx*.558*scale,y+ry*.558*scale,z+.104*scale),.017*scale,.022*scale,gold,"Z",12)
    # The lower emitter is carried by a recessed cage, not a featureless cylinder.
    torus(label+" lower field coil", (x,y,z-.155*scale), .405*scale, .022*scale, titanium)
    for i in range(6):
        a=math.tau*i/6
        rod(label+" lower coil brace %02d"%i,(x+math.cos(a)*.36*scale,y+math.sin(a)*.36*scale,z-.12*scale),(x+math.cos(a)*.48*scale,y+math.sin(a)*.48*scale,z-.07*scale),.022*scale,black,10)


def loft(name, sections, material):
    """Angular fairing around the keel. Section=(y, half-width, top-z, bottom-z)."""
    verts=[]; faces=[]
    for y,w,top,bottom in sections:
        c=min(w*.28,(top-bottom)*.22)
        ring=[(-w+c,bottom),(w-c,bottom),(w,bottom+c),(w,top-c),(w-c,top),(-w+c,top),(-w,top-c),(-w,bottom+c)]
        verts.extend((x,y,z) for x,z in ring)
    n=8; faces.append(tuple(range(n))); faces.append(tuple(reversed(range((len(sections)-1)*n,len(sections)*n))))
    for s in range(len(sections)-1):
        for j in range(n): faces.append((s*n+j,(s+1)*n+j,(s+1)*n+(j+1)%n,s*n+(j+1)%n))
    me=bpy.data.meshes.new(name+" mesh"); me.from_pydata(verts,[],faces); me.materials.append(material); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
    bev=ob.modifiers.new("Three-cut edge breaks","BEVEL"); bev.width=.025; bev.segments=3
    ob.modifiers.new("Weighted panel normals","WEIGHTED_NORMAL")
    return ob


def add_text(name, body, loc, size, material, rot=(math.pi/2,0,0), align="CENTER"):
    cu=bpy.data.curves.new(name+" glyphs","FONT"); cu.body=body; cu.size=size; cu.align_x=align; cu.extrude=.0015; cu.bevel_depth=.0005
    ob=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(ob); ob.location=loc; ob.rotation_euler=rot; ob.data.materials.append(material); return ob


def build(output_dir):
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    olive=mat("01 | ceramic olive armor",(.22,.27,.15),.62,.36)
    olive_light=mat("02 | exposed olive edges",(.37,.42,.23),.68,.30)
    black=mat("03 | carbon-black frame",(.035,.048,.052),.78,.29)
    titanium=mat("04 | brushed titanium",(.42,.47,.49),.82,.25)
    gold=mat("05 | amber hardware",(.78,.39,.07),.72,.28)
    dark=mat("06 | recessed graphite",(.012,.019,.021),.55,.42)
    leather=mat("07 | seat upholstery",(.11,.075,.047),.15,.66)
    glass=mat("08 | cockpit instrument glass",(.025,.12,.16),.48,.18,.25)
    glow=mat("09 | cold white hover emission",(.55,.85,1.0),.18,.18,4.0)
    hot=mat("10 | turbine amber emission",(1.0,.25,.025),.12,.2,3.0)

    # The reference includes a second open cage bay behind the seat.
    # Translate complete rear modules after compact-drive shaping; never stretch hardware.
    rear_bay_length=.72
    pod_shift=rear_bay_length*.5
    aft_modules=set()
    def remember_aft(before):
        aft_modules.update(set(bpy.context.scene.objects)-before)

    # Reference-led proportions: overall length 6.4, width 3.6, low open cage.
    # Individual parts are authored in final world coordinates; no post-hoc scaling.
    def panel(name, points, offset, material, bevel=.014):
        n=len(points); off=Vector(offset)
        verts=list(points)+[tuple(Vector(p)+off) for p in points]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
        ob=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(ob)
        ob.data.materials.append(material)
        mod=ob.modifiers.new("Manufactured edge radius","BEVEL"); mod.width=bevel; mod.segments=2 if bevel<=.006 else 3
        ob.modifiers.new("Panel normals","WEIGHTED_NORMAL")
        return ob

    def ring_shell(name,x,z,profile,material):
        # Revolved open profile: real nozzle wall and recessed internal throat.
        n=40; verts=[]; faces=[]
        for y,r in profile:
            verts.extend((x+r*math.cos(i*math.tau/n),y,z+r*math.sin(i*math.tau/n)) for i in range(n))
        for j in range(len(profile)-1):
            for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
        me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update(); me.materials.append(material)
        ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
        for face in me.polygons: face.use_smooth=True
        return ob

    def joint(name, p, side, radius=.12):
        x,y,z=p
        cyl(name+" bearing",p,radius,.20,black,"X",32)
        cyl(name+" flange",(x+side*.12,y,z),radius*.9,.035,titanium,"X",32)
        torus(name+" retaining race",(x+side*.145,y,z),radius*.67,.014,gold,"X")
        cyl(name+" recessed hub",(x+side*.17,y,z),radius*.44,.028,dark,"X",24)
        cyl(name+" axle bolt",(x+side*.19,y,z),radius*.19,.032,titanium,"X",6)

    box("Open cockpit recessed floor",(0,.18,.73),(.92,2.05,.10),black,.04)
    box("Rear equipment deck",(0,1.51+rear_bay_length,.82),(1.42,1.25,.14),black,.04)
    for y in (-.75,-.1,.55,1.12+rear_bay_length,1.72+rear_bay_length):
        rod("Chassis crossmember",(-.66,y,.76),(.66,y,.76),.045,titanium,20)
    # Two descending nose blades leave a narrow center split and an open underside.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        def pt(x,y,z): return (side*x,y,z)
        panel(label+" pointed lower nose spar",[pt(.10,-3.48,.42),pt(.26,-3.40,.42),pt(.67,-1.05,.91),pt(.58,-.72,1.05),pt(.33,-1.86,.76)],(0,0,.08),black)
        panel(label+" sculpted nose cheek",[pt(.14,-3.30,.55),pt(.36,-2.73,.84),pt(.76,-1.10,1.30),pt(.57,-.81,1.35),pt(.24,-2.24,.92)],(0,0,.065),olive)
        panel(label+" inset nose shoulder",[pt(.39,-2.49,.92),pt(.66,-1.28,1.27),pt(.57,-1.14,1.31),pt(.34,-2.18,1.02)],(0,0,.018),olive_light,.007)
        rod(label+" lower sill",pt(.30,-2.44,.60),pt(.67,1.54+rear_bay_length,.78),.055,black,24)
        rod(label+" cockpit shoulder sill",pt(.61,-1.02,1.21),pt(.74,1.26+rear_bay_length,1.23),.045,titanium,24)
        panel(label+" triangular sill armor",[pt(.65,-.95,1.17),pt(.76,.78,1.20),pt(.70,1.12,.94),pt(.57,-.22,.81)],(side*.045,0,0),olive)
        panel(label+" sill recessed relief",[pt(.699,-.58,1.10),pt(.78,.65,1.13),pt(.73,.76,1.02)],(side*.012,0,0),dark,.006)
        # Continuous cage triangles, with visibly connected lower and upper anchors.
        a=pt(.64,-1.13,1.23); b=pt(.48,-.15,2.04); c=pt(.49,.69,2.07)
        aft_top=pt(.49,.69+rear_bay_length,2.07)
        aft_lower=pt(.74,.69+rear_bay_length,1.23)
        d=pt(.78,1.48+rear_bay_length,1.24)
        for name,u,v,r in (
            ("raked windshield pillar",a,b,.045),("roof rail",b,c,.044),
            ("rear bay upper longeron",c,aft_top,.044),
            ("rear bay lower longeron",pt(.74,.69,1.23),aft_lower,.045),
            ("rear bay aft upright",aft_top,aft_lower,.045),
            ("rear cage pillar",aft_top,d,.052),
            ("rear diagonal",c,pt(.70,.72,.80),.038),
            ("rear deck brace",pt(.70,.72,.80),d,.034)):
            rod(label+" "+name,u,v,r,titanium,20)
        for q in (a,b,c,d): joint(label+" cage junction",q,side,.065)
        # Low-profile collars keep the extra bay readable without a dense bolt cluster.
        cyl(label+" rear bay aft corner",aft_top,.070,.14,black,"X",16)
        cyl(label+" rear bay corner pin",(aft_top[0]+side*.08,aft_top[1],aft_top[2]),.025,.025,gold,"X",8)
        # Long close-set arms, clevis gaps, paired links and telescoping hydraulics.
        root=pt(.85,-.70,1.12); elbow=pt(1.12,-1.64,.88); wrist=pt(1.30,-2.91,.59)
        for name,u,v in (("upper link",root,elbow),("forward link",elbow,wrist)):
            for dx in (-.065,.065):
                u1=(u[0]+dx,u[1],u[2]); v1=(v[0]+dx,v[1],v[2])
                direction=Vector(v1)-Vector(u1)
                web=loft(label+" "+name+" forged web",[(0,.045,.065,-.065),
                    (direction.length*.16,.075,.075,-.075),
                    (direction.length*.72,.055,.060,-.060),
                    (direction.length,.036,.05,-.05)],black)
                web.rotation_euler=direction.to_track_quat("Y","Z").to_euler()
                web.location=Vector(u1)
            rod(label+" hydraulic barrel",(u[0],u[1],u[2]+.10),tuple(Vector(u).lerp(Vector(v),.58)+Vector((0,0,.10))),.048,gold,24)
            rod(label+" polished piston",tuple(Vector(u).lerp(Vector(v),.54)+Vector((0,0,.10))),(v[0],v[1],v[2]+.10),.024,titanium,24)
            rod(label+" return hose",(u[0]-side*.09,u[1],u[2]+.04),(v[0]-side*.09,v[1],v[2]+.04),.014,dark,12)
        for q,r in ((root,.15),(elbow,.13),(wrist,.105)): joint(label+" suspension pivot",q,side,r)
        panel(label+" arm triangular cover",[pt(.94,-.83,1.16),pt(1.21,-1.58,.96),pt(1.20,-1.75,.88),pt(.96,-1.40,.93)],(0,0,.035),olive)
        rod(label+" lower wishbone",pt(.83,-.66,.78),pt(1.30,-2.91,.50),.034,titanium,20)
        rod(label+" cell gimbal spindle",wrist,pt(1.30,-2.91,.42),.075,black,24)
        make_hover_cell(side*1.30,-2.91,.29,.83,label+" forward lift",(olive,black,titanium,glow,gold))
        # Cross-section shells taper into a chamfered front and a pinched aft cap.
        # Outer hatches are cut into the shell, not laid over an unbroken box face.
        for idx,y in enumerate((.65+pod_shift,1.48+pod_shift)):
            x=side*1.12
            shell=loft(label+" shaped pod shell "+str(idx),[
                (y-.39,.21,1.32,.91),(y-.30,.32,1.45,.81),
                (y-.22,.35,1.47,.80),(y+.22,.35,1.43,.80),
                (y+.31,.29,1.36,.86),(y+.37,.20,1.29,.93)],olive)
            shell.location.x=x
            # A real shallow service cavity with an olive panel recessed behind the lip.
            cutter=box("TEMP pod cavity cutter",(x+side*.35,y,1.125),(.15,.48,.37),dark,.025)
            bpy.context.view_layer.objects.active=shell
            for existing in list(shell.modifiers):
                bpy.ops.object.modifier_apply(modifier=existing.name)
            mod=shell.modifiers.new("Recessed service pocket","BOOLEAN")
            mod.object=cutter; mod.operation="DIFFERENCE"
            bpy.context.view_layer.objects.active=shell
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cutter,do_unlink=True)
            box(label+" pod pocket shadow",(x+side*.282,y,1.125),(.012,.465,.35),dark,.020)
            box(label+" fitted hatch",(x+side*.294,y,1.125),(.014,.415,.30),olive,.018)
            for yy in (y-.16,y+.16):
                box(label+" hatch recessed latch",(x+side*.315,yy,1.025),(.030,.055,.055),titanium,.008)
            for yy in (y-.25,y+.25):
                # Formed crown ribs follow the shoulder instead of floating flat straps.
                panel(label+" pod shoulder rib",[pt(.86,yy,1.38),pt(.94,yy,1.48),pt(1.30,yy,1.46),pt(1.43,yy,1.33)],(0,.038,0),black,.009)
            panel(label+" swept pod lower carrier",[pt(.72,y-.30,.79),pt(1.30,y-.30,.76),pt(1.43,y+.26,.81),pt(.77,y+.30,.85)],(0,0,.055),black)
            for yy in (y-.22,y+.22):
                beam_between(label+" pod fitted mounting clevis",pt(.64,yy,.78),pt(1.03,yy,.83),.085,titanium,.11,.012)
        add_text(label+" serial","01",pt(1.426,.65+pod_shift,1.045),.22,titanium,(math.pi/2,0,side*math.pi/2))
        for yy in (1.36+pod_shift,1.60+pod_shift):
            box(label+" rear pod vent bed",pt(1.426,yy,1.15),(.014,.16,.21),dark,.012)
            for zz in (1.08,1.14,1.20):
                box(label+" recessed vent louver",pt(1.437,yy,zz),(.018,.125,.018),black,.004)
        before_aft=set(bpy.context.scene.objects)
        # Exposed rear turbine: open annular wall, recessed core and swept vanes.
        tx=side*.57
        ring_shell(label+" contoured hollow turbine",tx,1.19,[(1.45,.32),(1.57,.44),(1.72,.47),(2.28,.47),(2.36,.50),(2.55,.50),(2.65,.47),(2.65,.35),(2.57,.34),(2.42,.34),(2.30,.27),(2.04,.24)],black)
        for y,r in ((1.61,.43),(1.98,.46),(2.39,.47),(2.63,.48)):
            torus(label+" turbine flange",(tx,y,1.19),r,.024,titanium,"Y")
        torus(label+" nozzle lip",(tx,2.64,1.19),.435,.018,gold,"Y")
        cyl(label+" recessed core backplate",(tx,2.02,1.19),.24,.035,dark,"Y",48)
        cyl(label+" recessed hot core",(tx,2.07,1.19),.105,.04,hot,"Y",40)
        torus(label+" internal core ring",(tx,2.09,1.19),.18,.012,gold,"Y")
        for i in range(16):
            a=i*math.tau/16
            def radial(r,y,t): return (tx+r*math.cos(t),y,1.19+r*math.sin(t))
            panel(label+" swept stator",[radial(.25,2.17,a),radial(.40,2.48,a+.13),radial(.40,2.38,a+.19),radial(.25,2.10,a+.06)],(0,.012,0),gold,.003)
            rod(label+" casing stiffener",radial(.455,1.98,a),radial(.46,2.36,a),.014,titanium,10)
        rod(label+" engine lower cradle",pt(.90,1.14,.65),pt(.97,2.55,.71),.048,black,20)
        rod(label+" engine rear bumper",pt(.97,2.55,.71),pt(.25,2.63,.65),.042,titanium,20)
        # Swept thin fins grow from the rear cage, rather than standing vertically.
        panel(label+" swept stabilizer",[pt(.77,1.14,1.33),pt(.86,1.72,1.90),pt(1.04,2.48,2.24),pt(1.08,2.65,2.24),pt(.87,1.87,1.35)],(side*.045,0,0),olive)
        rod(label+" fin leading stiffener",pt(.80,1.18,1.37),pt(1.05,2.49,2.23),.018,titanium,16)
        joint(label+" fin root bracket",pt(.80,1.34,1.42),side,.08)
        make_hover_cell(side*.86,1.72,.64,.48,label+" aft lift",(olive,black,titanium,glow,gold))
        box(label+" integrated lift saddle",pt(.86,1.72,.785),(.46,.45,.065),black,.025)
        for dy in (-.16,.16):
            beam_between(label+" lift cradle cheek",pt(.86,1.72+dy,.77),pt(.72,1.72+dy,.88),.055,titanium,.07,.012)
        remember_aft(before_aft)
        for y in (-.45,.05,.55):
            rod(label+" cockpit floor diagonal",pt(.62,y,.80),pt(.40,y+.35,1.14),.025,black,16)

    # Secondary engineered forms from the reference close-ups.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        def pt(x,y,z): return (side*x,y,z)
        # Layered forward-link armor follows the linkage slope, leaving pistons exposed.
        panel(label+" forward link armored web",[pt(1.18,-1.80,.90),pt(1.36,-2.67,.65),pt(1.39,-2.79,.56),pt(1.25,-2.22,.64),pt(1.16,-1.85,.78)],(side*.035,0,0),olive)
        panel(label+" forward link inset",[pt(1.224,-1.94,.81),pt(1.355,-2.61,.63),pt(1.31,-2.32,.67)],(side*.012,0,0),gold,.005)
        for y,z,x in ((-1.94,.83,1.23),(-2.56,.65,1.35)):
            cyl(label+" web attachment",pt(x,y,z),.025,.035,titanium,"X",8)
        # Triangular gussets and paired mounting ears reinforce the cage intersections.
        for y in (-.98,1.12+rear_bay_length):
            panel(label+" sill triangular gusset",[pt(.69,y,1.19),pt(.69,y+.26,1.19),pt(.69,y+.19,.99)],(side*.035,0,0),black)
            for yy in (y+.05,y+.20): cyl(label+" gusset bolt",pt(.735,yy,1.15),.024,.022,titanium,"X",8)
        # Four small edge fasteners on each large cheek, without filling flat panels.
        for x,y,z in ((.25,-2.74,.82),(.39,-2.16,1.04),(.54,-1.60,1.21),(.66,-1.18,1.33)):
            cyl(label+" nose countersunk screw",pt(x,y,z),.022,.015,titanium,"Z",8)
        box(label+" nose running lamp bed",pt(.59,-1.45,1.23),(.055,.35,.05),black,.012,(.28,0,0))
        for y in (-1.55,-1.48,-1.41): box(label+" running lamp emitter",pt(.59,y,1.26),(.035,.035,.025),glow,.007)
        before_aft=set(bpy.context.scene.objects)
        # Low stacked turbine control heads occupy the rear deck above the engines.
        box(label+" turbine governor cradle",pt(.57,1.83,1.69),(.56,.68,.10),black,.035)
        box(label+" turbine governor casing",pt(.57,1.83,1.81),(.43,.53,.15),olive,.035)
        cyl(label+" governor recessed fan",pt(.57,1.83,1.90),.18,.035,dark,"Z",40)
        torus(label+" governor retaining lip",pt(.57,1.83,1.92),.17,.017,titanium)
        for i in range(8):
            a=i*math.tau/8
            rod(label+" governor grille",(side*.57+.065*math.cos(a),1.83+.065*math.sin(a),1.934),(side*.57+.15*math.cos(a+.23),1.83+.15*math.sin(a+.23),1.934),.012,titanium,8)
        for y in (1.64,2.05):
            rod(label+" engine service line",pt(.90,y,1.48),pt(.77,y,1.79),.022,gold,16)
        # Visible rear cooling plates and cylinder straps replace a bare barrel.
        for i in range(5):
            y=1.67+i*.105
            box(label+" turbine cooling plate",pt(.97,y,1.23),(.055,.025,.33),black,.008)
        for y in (1.62,2.30):
            for a in (.35,1.2,2.1):
                x=side*.57+.47*math.cos(a); z=1.19+.47*math.sin(a)
                box(label+" turbine flange clamp",(x,y,z),(.07,.09,.07),gold,.013)
        # Rear frame triangulation supports the drive cluster and stabilizers.
        rod(label+" rear triangulated rail",pt(.49,.69,2.07),pt(.72,1.46,1.66),.031,black,20)
        rod(label+" engine diagonal tie",pt(.72,1.46,1.66),pt(.96,2.44,.73),.032,black,20)
        remember_aft(before_aft)

    # Narrow center cowling slopes toward the split tip; cockpit remains entirely open.
    panel("Sloping nose center",[(-.07,-3.24,.53),(.07,-3.24,.53),(.43,-1.22,1.31),(-.43,-1.22,1.31)],(0,0,.04),black)
    panel("Inset nose access cover",[(-.17,-2.35,.89),(.17,-2.35,.89),(.34,-1.42,1.25),(-.34,-1.42,1.25)],(0,0,.015),dark)
    for x in (-.27,.27):
        rod("Windshield lower support",(x,-1.12,1.32),(x,-.82,1.50),.025,black,16)
    rod("Roof front crossbar",(-.48,-.15,2.04),(.48,-.15,2.04),.036,titanium,24)
    rod("Roof rear crossbar",(-.49,.69,2.07),(.49,.69,2.07),.036,titanium,24)
    rod("Rear bay aft roof crossbar",(-.49,.69+rear_bay_length,2.07),(.49,.69+rear_bay_length,2.07),.036,titanium,20)
    rod("Rear bay aft belt crossbar",(-.74,.69+rear_bay_length,1.23),(.74,.69+rear_bay_length,1.23),.035,black,20)
    # Contoured seat shell with raised thigh and shoulder bolsters.
    for side in (-1,1):
        panel("Bucket seat curved side",[(side*.29,-.24,.85),(side*.31,.35,.89),(side*.34,.68,1.76),(side*.23,.77,1.92),(side*.21,.53,1.08),(side*.20,-.28,1.00)],(side*.035,0,0),black,.025)
    box("Seat cushion",(0,.05,.94),(.48,.58,.16),leather,.075)
    box("Seat back",(0,.52,1.36),(.48,.14,.71),leather,.075,(-.18,0,0))
    box("Headrest",(0,.64,1.80),(.32,.16,.22),leather,.06)
    for x in (-.18,.18):
        box("Seat thigh bolster",(x,.03,1.03),(.10,.50,.12),dark,.04)
        beam_between("Flat woven shoulder harness",(x,.40,1.67),(x*.60,-.06,1.06),.062,leather,.009,.003)
    for z in (1.17,1.33,1.49): box("Seat cushion stitched segment",(0,.42,z),(.32,.022,.09),dark,.014,(-.18,0,0))
    box("Harness buckle",(0,-.06,1.07),(.12,.06,.07),titanium,.015)
    box("Dashboard binnacle",(0,-.85,1.30),(.76,.20,.14),black,.04)
    box("Instrument display",(0,-.77,1.40),(.35,.09,.02),glass,.01)
    rod("Steering stem",(0,-.85,1.23),(0,-.54,1.34),.03,titanium,20)
    rod("Steering yoke",(-.23,-.54,1.34),(.23,-.54,1.34),.027,black,20)
    for x in (-.23,.23): rod("Yoke handgrip",(x,-.54,1.28),(x,-.54,1.43),.038,leather,20)
    box("Rear electronics spine",(0,1.39+rear_bay_length,1.12),(.28,.72,.45),dark,.04)
    for y in (1.16,1.33,1.50,1.67): box("Electronics heat sink",(0,y+rear_bay_length,1.36),(.30,.035,.07),titanium,.008)
    # Detailed cockpit switch banks and fitted pedal well stay inside approved silhouette.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        x=side*.36
        box(label+" cockpit console",(x,-.18,1.04),(.13,.64,.12),black,.024)
        box(label+" switch recess",(x,-.18,1.106),(.095,.48,.012),dark,.008)
        for i in range(4):
            y=-.36+i*.12
            cyl(label+" switch mounting collar",(x,y,1.12),.023,.012,titanium,"Z",12)
            rod(label+" toggle",(x,y,1.13),(x,y-.012,1.165),.008,gold,8)
        box(label+" pedal tread",(side*.17,-.65,.84),(.16,.19,.025),titanium,.012,(.25,0,0))
        for y in (-.71,-.65,-.59): box(label+" pedal grip groove",(side*.17,y,.861),(.12,.015,.008),dark,.002)
        # A formed clevis wraps each front suspension root instead of a floating axle.
        for yy in (-.78,-.63):
            panel(label+" suspension root mounting ear",[(side*.68,yy,1.02),(side*.89,yy,1.03),(side*.94,yy,1.20),(side*.77,yy,1.29)],(0,.035,0),olive,.012)
        rod(label+" pivot locking pin",(side*.89,-.83,1.12),(side*.89,-.56,1.12),.026,titanium,16)
        before_aft=set(bpy.context.scene.objects)
        # Connected bent service lines with couplers, offset from the frame tubes.
        pts=[(side*.78,.72,1.40),(side*.85,.97,1.52),(side*.86,1.24,1.54),(side*.78,1.53,1.60)]
        for i,(a,b) in enumerate(zip(pts,pts[1:])):
            rod(label+" coolant hose",a,b,.028,dark,16)
        for q in (pts[0],pts[-1]):
            cyl(label+" hose coupling",q,.042,.08,gold,"Z",12)
        # Thin protective fin relief follows the swept shape without changing its outline.
        panel(label+" stabilizer relief",[(side*.91,1.68,1.74),(side*1.055,2.40,2.16),(side*.96,1.93,1.69)],(side*.008,0,0),olive_light,.005)
        # Fastened dorsal saddle between roll cage and serviceable rear drive.
        box(label+" rear electrical junction",(side*.32,1.21,1.24),(.22,.30,.15),black,.025)
        for y in (1.13,1.29): cyl(label+" junction captive bolt",(side*.32,y,1.325),.018,.012,titanium,"Z",8)
        remember_aft(before_aft)
    # Instrument graphics are real emissive geometry, readable in the exported GLB.
    for i in range(6):
        box("Instrument telemetry bar",(-.135+i*.05,-.77,1.414),(.025,.018+(i%3)*.012,.002),glow,0)
    for x in (-.28,.28):
        cyl("Dashboard selector bezel",(x,-.80,1.385),.045,.015,titanium,"Z",24)
        cyl("Dashboard selector knob",(x,-.80,1.40),.030,.025,dark,"Z",12)
    box("Harness metal clasp",(0,-.065,1.113),(.075,.045,.012),gold,.008)
    for x in (-.18,.18):
        for y in (-.13,.05,.23): box("Seat stitch",(x,y,1.117),(.009,.07,.004),olive_light,0)

    # Shorten only the front suspension reach about its fixed root; retain circular cells.
    def arm_y(y): return -.70+(y+.70)*.80
    bpy.context.view_layer.update()
    arm_tags=("upper link","forward link","hydraulic barrel","polished piston","return hose",
              "suspension pivot","arm triangular cover","lower wishbone","cell gimbal spindle",
              "forward lift","web attachment")
    for ob in list(bpy.context.scene.objects):
        if ob.type!="MESH" or not any(t in ob.name for t in arm_tags): continue
        if "forward lift" in ob.name:
            ob.location.y+=.442  # rigid translation preserves circular rim and fastener spacing
        elif "suspension pivot" in ob.name:
            ob.location.y=arm_y(ob.location.y)
        else:
            world=ob.matrix_world.copy(); inv=world.inverted()
            for v in ob.data.vertices:
                q=world@v.co; q.y=arm_y(q.y); v.co=inv@q

    before_aft=set(bpy.context.scene.objects)
    # Rear-facing mechanical detail is authored for the chase camera, not only the hero view.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        tx=side*.57
        def rp(r,y,a): return (tx+r*math.cos(a),y,1.19+r*math.sin(a))
        # Separate tapered nozzle petals with seams, flanged clamps and inner heat shields.
        for i in range(12):
            a=i*math.tau/12; half=math.pi/12*.84
            panel(label+" exhaust petal",[rp(.475,2.37,a-half),rp(.485,2.64,a-half),rp(.485,2.64,a+half),rp(.475,2.37,a+half)],(0,.016,0),titanium,.005)
            rod(label+" petal actuator",rp(.48,2.29,a),rp(.49,2.57,a),.018,black,12)
            cyl(label+" petal lock screw",rp(.50,2.60,a),.018,.028,gold,"Y",8)
        for i in range(8):
            a=i*math.tau/8
            rod(label+" inner ion channel",rp(.275,2.16,a),rp(.385,2.47,a),.009,hot,8)
        torus(label+" recessed combustion ring",(tx,2.22,1.19),.26,.012,hot,"Y")
        # Recessed stepped center cone visible from behind without closing the nozzle mouth.
        rod(label+" turbine center bullet",(tx,2.06,1.19),(tx,2.29,1.19),.10,titanium,32,radius2=.035)
        cyl(label+" center ignition lens",(tx,2.30,1.19),.037,.015,hot,"Y",24)
        # Angular under-engine guards join the rear cradle, with real open spaces.
        panel(label+" lower engine guard",[(side*.27,2.14,.69),(side*.93,2.14,.73),(side*.96,2.62,.66),(side*.35,2.69,.60)],(0,0,.035),black,.012)
        for x in (.39,.70,.88):
            panel(label+" diffuser vane",[(side*x,2.12,.69),(side*x,2.63,.62),(side*x,2.53,.49),(side*x,2.23,.52)],(side*.018,0,0),titanium,.004)
        beam_between(label+" rear engine bracket",(side*.89,2.05,.77),(side*.96,2.42,.90),.065,olive,.09,.016)
        # Rear service lights sit above the nozzle mouths.
        box(label+" rear marker housing",(side*.90,2.19,1.62),(.25,.09,.08),black,.015)
        box(label+" rear amber marker",(side*.90,2.241,1.62),(.18,.015,.025),hot,.006)
    box("Rear bridge instrument enclosure",(0,2.20,1.72),(.40,.34,.22),black,.03)
    box("Rear bridge recessed plate",(0,2.377,1.72),(.29,.018,.13),olive,.012)
    add_text("Rear Mantis identification","MANTIS",(0,2.392,1.69),.060,titanium,(math.pi/2,0,math.pi))
    for x in (-.16,.16): cyl("Rear bridge captive fastener",(x,2.39,1.72),.018,.018,gold,"Y",8)

    remember_aft(before_aft)

    # Compact rear drive packaging: apply one rigid-axis mapping to every fitted part.
    # Radial scaling reduces the funnel silhouette; the shallower axial span makes a
    # dense drive module. Mounts, stators, petals and lamps share the same transform.
    engine_tags=("turbine", "nozzle", "core", "stator", "casing stiffener",
                 "exhaust petal", "petal actuator", "petal lock", "ion channel",
                 "combustion", "center ignition", "engine", "governor", "rear marker", "rear amber")
    bpy.context.view_layer.update()
    for ob in list(bpy.context.scene.objects):
        if ob.type!="MESH" or not ob.name.startswith(("Port ","Starboard ")): continue
        if not any(tag in ob.name for tag in engine_tags): continue
        side=-1 if ob.name.startswith("Port ") else 1
        world=ob.matrix_world.copy(); inv=world.inverted()
        for v in ob.data.vertices:
            q=world@v.co
            q.x=side*.57+(q.x-side*.57)*.86
            q.z=1.19+(q.z-1.19)*.86
            q.y=1.58+(q.y-1.58)*.78
            v.co=inv@q
    before_aft=set(bpy.context.scene.objects)
    # Controlled segmented barrel jackets, fitted over the compact engine profile.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        tx=side*.57
        for i in range(10):
            angle=math.tau*i/10; half=math.pi/10*.80
            verts=[]
            for y,r in ((1.68,.413),(1.73,.438),(2.10,.438),(2.16,.407)):
                verts.extend((tx+r*math.cos(a),y,1.19+r*math.sin(a)) for a in (angle-half,angle+half))
            mesh=bpy.data.meshes.new(label+" barrel jacket mesh")
            mesh.from_pydata(verts,[],[(j,j+1,j+3,j+2) for j in (0,2,4)])
            mesh.materials.append(black); mesh.update()
            ob=bpy.data.objects.new(label+" fitted barrel jacket",mesh); bpy.context.collection.objects.link(ob)
            solid=ob.modifiers.new("Thick segmented casing","SOLIDIFY"); solid.thickness=.025
            bevel=ob.modifiers.new("Casing edge radii","BEVEL"); bevel.width=.009; bevel.segments=1
        # A thick terminal collar encloses the nozzle vanes without a wide bell mouth.
        ring_shell(label+" thick recessed terminal collar",tx,1.19,
            [(2.13,.42),(2.18,.445),(2.38,.445),(2.42,.408),
             (2.42,.307),(2.36,.298),(2.20,.298)],titanium)
        for y in (1.76,2.08):
            torus(label+" barrel retaining band",(tx,y,1.19),.445,.018,black,"Y")

    remember_aft(before_aft)
    # Every turbine, fin, rear lift cell, bracket and service fitting shares this
    # translation. Circular rims and relative mounting distances remain unchanged.
    for ob in aft_modules:
        ob.location.y+=rear_bay_length

    # Convert lettering too, so exports, triangle accounting and LODs share one mesh set.
    for ob in list(bpy.context.scene.objects):
        if ob.type=="FONT":
            bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active=ob
            bpy.ops.object.convert(target="MESH")

    # Studio-only ground, lighting, and cameras. The floor is excluded from export.
    floor_mat=mat("Studio floor (preview only)",(.16,.19,.22),.25,.72)
    box("Preview floor",(0,-.1,.015),(200,200,.10),floor_mat,0)
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT" if bpy.app.version >= (4,2,0) else "BLENDER_EEVEE"
    if hasattr(scene,"eevee"):
        for key,value in {"taa_render_samples":48,"taa_samples":48,"use_gtao":True,
                          "gtao_distance":.25,"gtao_factor":1.25,"use_soft_shadows":True}.items():
            if hasattr(scene.eevee,key): setattr(scene.eevee,key,value)
    scene.world.use_nodes=True
    world=scene.world.node_tree.nodes.get("Background")
    if world: world.inputs["Color"].default_value=(.24,.28,.33,1); world.inputs["Strength"].default_value=.55
    scene.view_settings.view_transform="AgX"
    scene.render.image_settings.file_format="PNG"
    scene.render.resolution_percentage=100
    scene.render.film_transparent=False
    scene.render.resolution_x=1280; scene.render.resolution_y=960
    scene.render.image_settings.color_mode="RGBA"
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type="BOTH"
    scene.display.shading.cavity_ridge_factor=1.3
    scene.display.shading.cavity_valley_factor=1.0
    def aim(o,target): o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()
    bpy.ops.object.light_add(type="AREA",location=(1,-5,8)); key=bpy.context.object; key.data.energy=1350; key.data.shape="DISK"; key.data.size=6; aim(key,(0,0,1))
    bpy.ops.object.light_add(type="AREA",location=(-5,1,4)); rim=bpy.context.object; rim.data.energy=1150; rim.data.color=(.44,.68,1); rim.data.size=5; aim(rim,(0,0,1))
    bpy.ops.object.light_add(type="AREA",location=(4,4,5)); warm=bpy.context.object; warm.data.energy=1000; warm.data.color=(1,.56,.25); warm.data.size=4; aim(warm,(0,0,1))
    bpy.ops.object.camera_add(location=(7,-9,6)); cam=bpy.context.object; cam.data.type="ORTHO"; cam.data.ortho_scale=8.8; aim(cam,(0,-.05,1.05)); scene.camera=cam

    os.makedirs(output_dir,exist_ok=True)
    # Export selected asset meshes only; no floor, cameras, or lights.
    bpy.ops.object.select_all(action="DESELECT")
    for o in scene.objects:
        if o.type=="MESH" and o.name!="Preview floor": o.select_set(True)
    meshes=[o for o in scene.objects if o.type=="MESH" and o.name!="Preview floor"]
    # Smooth curved strips while splitting hard corners; weighted normals preserve panels.
    for ob in meshes:
        for face in ob.data.polygons: face.use_smooth=True
        if hasattr(ob.data,"use_auto_smooth"):
            ob.data.use_auto_smooth=True
            ob.data.auto_smooth_angle=math.radians(45)
        for modifier in ob.modifiers:
            if modifier.type=="WEIGHTED_NORMAL": modifier.keep_sharp=True
    # Blender 4.1+ no longer exposes Mesh.use_auto_smooth. Split only manufactured
    # corners; cylinder spans remain smooth, while collar lips stop looking inflated.
    if bpy.app.version >= (4,1,0):
        for ob in meshes:
            if not any(mod.type=="EDGE_SPLIT" for mod in ob.modifiers):
                mod=ob.modifiers.new("Manufactured corner normal breaks","EDGE_SPLIT")
                mod.split_angle=math.radians(35)
                mod.use_edge_angle=True
    depsgraph=bpy.context.evaluated_depsgraph_get()
    triangle_count=0
    assembly_triangles={}
    for ob in meshes:
        evaluated=ob.evaluated_get(depsgraph)
        evaluated_mesh=evaluated.to_mesh()
        count=sum(max(0,len(poly.vertices)-2) for poly in evaluated_mesh.polygons)
        triangle_count+=count
        name=ob.name.lower()
        group="drive" if any(t in name for t in ("turbine","engine","barrel","nozzle","stator","petal","core","combustion","governor","collar")) else "pods" if any(t in name for t in ("pod","hatch","vent","serial")) else "lift" if "lift" in name else "chassis_cockpit"
        assembly_triangles[group]=assembly_triangles.get(group,0)+count
        evaluated.to_mesh_clear()
    print("MANTIS_BUDGET",json.dumps({"total":triangle_count,"assemblies":assembly_triangles}),flush=True)
    if triangle_count>120000:
        raise RuntimeError("Mantis exceeds the 120,000 triangle hero-asset budget: {}".format(triangle_count))


    # Smart UVs are deterministic and keep all material detail inside the GLB.
    for o in meshes:
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active=o
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bm=bmesh.from_edit_mesh(o.data); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bmesh.update_edit_mesh(o.data); bpy.ops.uv.smart_project(island_margin=.02); bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    glb=os.path.abspath(os.path.join(output_dir,"mantis_mk1.glb"))
    bpy.ops.export_scene.gltf(filepath=glb,export_format="GLB",export_apply=True,use_selection=True)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(output_dir,"mantis_mk1.blend")))

    # Reduced LOD exports are produced from the same detailed source geometry.
    # Tiny fasteners and seams are culled by size, then remaining parts are decimated.
    def export_lod(label, ratio, detail_cutoff):
        copies=[]
        for original in meshes:
            if label=="LOD2" and any(tag in original.name for tag in ("petal actuator","petal lock screw","inner ion channel")):
                continue
            if max(original.dimensions) < detail_cutoff:
                continue
            obj=original.copy()
            # Decimate evaluated geometry so bevel/solidify costs cannot evade LOD reduction.
            depsgraph=bpy.context.evaluated_depsgraph_get()
            obj.data=bpy.data.meshes.new_from_object(original.evaluated_get(depsgraph),depsgraph=depsgraph)
            obj.modifiers.clear()
            obj.name=label+"_"+original.name
            scene.collection.objects.link(obj)
            poly_count=len(obj.data.polygons)
            if poly_count>24:
                dec=obj.modifiers.new(label+" controlled polygon reduction","DECIMATE")
                dec.decimate_type="COLLAPSE"
                dec.ratio=ratio
                dec.use_collapse_triangulate=True
            copies.append(obj)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in copies: obj.select_set(True)
        if copies:
            bpy.context.view_layer.objects.active=copies[0]
            depsgraph=bpy.context.evaluated_depsgraph_get()
            lod_triangles=0
            for obj in copies:
                evaluated=obj.evaluated_get(depsgraph)
                mesh=evaluated.to_mesh()
                lod_triangles+=sum(max(0,len(poly.vertices)-2) for poly in mesh.polygons)
                evaluated.to_mesh_clear()
            path=os.path.abspath(os.path.join(output_dir,"mantis_mk1_"+label.lower()+".glb"))
            bpy.ops.export_scene.gltf(filepath=path,export_format="GLB",export_apply=True,use_selection=True)
        else:
            lod_triangles=0
            path=""
        for obj in copies:
            data=obj.data
            bpy.data.objects.remove(obj,do_unlink=True)
            if data.users==0: bpy.data.meshes.remove(data)
        return lod_triangles

    lod1_triangles=export_lod("LOD1",.23,.035)
    lod2_triangles=export_lod("LOD2",.045,.10)
    if not 0<lod1_triangles<=45000: raise RuntimeError("LOD1 must remain within the 15k-45k triangle target: {}".format(lod1_triangles))
    if not 0<lod2_triangles<=20000: raise RuntimeError("LOD2 must remain within the 10k-20k triangle target: {}".format(lod2_triangles))

    specs=[
      ("hero_3q",(8,-10,5.4),(0,-.05+rear_bay_length*.5,1.05),9.4),
      ("front",(0,-12,1.15),(0,-.1,1.15),5.5),
      ("side",(12,-.4+rear_bay_length*.5,1.15),(0,-.4+rear_bay_length*.5,1.15),8.3),
      ("rear",(0,12,1.15),(0,.1,1.15),5.5),
      ("top",(0,-.42+rear_bay_length*.5,13),(0,-.42+rear_bay_length*.5,.9),10.7),
      ("cockpit_detail",(3,-3,3.6),(0,-.05,1.30),3.15),
      ("drive_detail",(4,5+rear_bay_length,3.0),(0,1.75+rear_bay_length,1.23),3.9),
      ("rear_3q",(7,9+rear_bay_length,4.6),(0,.35+rear_bay_length*.5,1.10),8.6),
      ("chase",(0,9+rear_bay_length,4.4),(0,.10+rear_bay_length*.5,1.1),7.9),
    ]
    view_paths=[]
    for name,loc,target,scale in specs:
        cam.location=loc; cam.data.ortho_scale=scale; aim(cam,target); scene.camera=cam
        scene.render.resolution_x=960; scene.render.resolution_y=720
        path=os.path.abspath(os.path.join(output_dir,"mantis_mk1_"+name+".png")); scene.render.filepath=path
        try: bpy.ops.render.render(write_still=True)
        except Exception as exc:
            if scene.render.engine not in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"): raise
            print("Eevee offscreen render failed; switching to Workbench:",exc)
            scene.render.engine="BLENDER_WORKBENCH"; scene.display.shading.light="STUDIO"; scene.display.shading.color_type="MATERIAL"; scene.display.shading.show_cavity=True
            bpy.ops.render.render(write_still=True)
        view_paths.append(path)

    # Compose five review views into a portable board with the hero view prominent.
    images=[bpy.data.images.load(p,check_existing=False) for p in view_paths[:5]]
    tile_w,tile_h=960,720
    sheet=bpy.data.images.new("Mantis MK I Assetwright review board",width=tile_w*2,height=tile_h*3,alpha=False)
    pix=array("f",[0.04,0.05,0.06,1.0])*(tile_w*2*tile_h*3)
    placements=[(0,2),(tile_w,2),(0,1),(tile_w,1),(0,0)]
    for im,(ox,oy) in zip(images,placements):
        src=array("f",[0.0])*(tile_w*tile_h*4); im.pixels.foreach_get(src)
        for row in range(tile_h):
            a=row*tile_w*4; b=((oy*tile_h+row)*(tile_w*2)+ox)*4
            pix[b:b+tile_w*4]=src[a:a+tile_w*4]
    sheet.pixels.foreach_set(pix); sheet.filepath_raw=os.path.abspath(os.path.join(output_dir,"mantis_mk1_review_board.png")); sheet.file_format="PNG"; sheet.save()
    for im in images: bpy.data.images.remove(im)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(output_dir,"mantis_mk1.blend")))

    # Low-poly compound collision proxy: broad hull, arm envelopes, and four lift pods.
    collision_objects=[]
    collision_objects.append(box("COLLISION_MainHull",(0,.70+rear_bay_length*.5,1.30),(1.50,4.0+rear_bay_length,1.80),dark,0))
    for side,label in ((-1,"Port"),(1,"Starboard")):
        collision_objects.append(beam_between("COLLISION_"+label+"Nose",(side*.13,-3.40,.49),(side*.52,-1.05,1.17),.35,dark,.30,0))
        collision_objects.append(box("COLLISION_"+label+"EquipmentPods",(side*1.12,1.06+pod_shift,1.12),(.72,1.65,.72),dark,0))
        collision_objects.append(beam_between("COLLISION_"+label+"Arm",(side*.85,-.70,1.12),(side*1.30,-2.468,.45),.34,dark,.34,0))
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.50,depth=.25,location=(side*1.30,-2.468,.29))
        collision_objects.append(bpy.context.object); collision_objects[-1].name="COLLISION_"+label+"FrontLift"
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.29,depth=.17,location=(side*.86,1.72+rear_bay_length,.64))
        collision_objects.append(bpy.context.object); collision_objects[-1].name="COLLISION_"+label+"RearLift"
        collision_objects[-1].data.materials.append(dark)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in collision_objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=collision_objects[0]
    collision_path=os.path.abspath(os.path.join(output_dir,"mantis_mk1_collision.glb"))
    bpy.ops.export_scene.gltf(filepath=collision_path,export_format="GLB",export_apply=True,use_selection=True)
    collision_triangles=sum(sum(max(0,len(poly.vertices)-2) for poly in obj.data.polygons) for obj in collision_objects)
    for obj in collision_objects:
        data=obj.data
        bpy.data.objects.remove(obj,do_unlink=True)
        if data.users==0: bpy.data.meshes.remove(data)

    record={
      "asset_id":"mantis_mk1_hover_racer",
      "display_name":"Mantis / MK I",
      "generator":"Assetwright procedural Blender extended rear rectangular cage bay v9",
      "rear_frame_bay":{"length":rear_bay_length,"front_y":.69,"aft_y":.69+rear_bay_length,"pod_shift_y":pod_shift,"drive_shift_y":rear_bay_length},
      "reference":"User-provided MANTIS / MK I concept and wireframe sheets; source image is not redistributed by this build.",
      "prompt":"Create a game-ready experimental exposed-frame hover speedster called Mantis / MK I. Use a low forward-swept profile and a rigid angular exoskeleton with olive-drab armor plates, black structural tubing, brushed titanium fittings, and amber caution hardware. Build twin articulated mantis-like front arms that extend mostly forward close beside the split nose and terminate in layered circular hover repulsor cells. Extend the rear exoskeleton with a second open rectangular frame bay behind the seat, with parallel upper rails and an aft crossbar before the sloping rear engine supports. Keep the rear drive, fins and tucked lift cells together beyond that bay. Keep the single-seat cockpit open, with an exposed seat, harness, compact instrument panel, and a skeletal roll/canopy cage. Add modular armored side equipment pods with visible panel seams, vents, latches, and 01 markings. Place a paired visible turbine cluster at the rear, with concentric machined rings, stator vanes, and amber cores. Add swept tail fins and two smaller aft hover cells tucked tightly beneath the rear chassis. Shorten front suspension reach by 20 percent about the original root. Emphasize layered exhaust petals, recessed combustion rings, center cones, under-engine guards and rear service fittings for the driving camera. Use an open triangulated chassis, long split tapered nose, descending cheek panels, close-set articulated arms, and exposed hollow turbine nozzles. Avoid a solid central hull. Show believable mechanical connections, exposed actuators, hoses, fasteners, and layered armor; preserve the open-frame silhouette and separate readable parts. Export a textured GLB for a real-time game.",
      "negative_prompt":"No enclosed car body, no conventional wheels or tires, no landing legs, no smooth one-piece shell, no low-poly toy appearance, no omitted front arms, no missing hover cells, no opaque canopy, no unsupported floating details, no text outside modeled markings.",
      "game_target":{"engine":"Godot","format":"GLB","intended_use":"Real-time hover-racing game asset","triangle_budget_target":120000,"triangle_count":triangle_count,"assembly_triangles":assembly_triangles,"lods":{"LOD0":triangle_count,"LOD1":lod1_triangles,"LOD2":lod2_triangles},"collision_triangles":collision_triangles,"texture_policy":"Embedded albedo, roughness and authored micro-normal maps; high-to-low normal, AO and curvature baking not implemented"},
      "feature_labels":["open_exoskeleton","extended_rear_rectangular_bay","twin_forward_articulated_arms","front_hover_cells","open_single_seat_cockpit","skeletal_canopy_frame","modular_side_pods","paired_rear_turbines","swept_tail_fins","aft_hover_cells","olive_metal_materials","mechanical_hardware"],
      "axis_convention":{"forward":"-Y","right":"+X","up":"+Z"},
      "views":["hero_3q","front","side","rear","top","cockpit_detail","drive_detail","rear_3q","chase"],
      "files":["mantis_mk1.blend","mantis_mk1.glb","mantis_mk1_lod1.glb","mantis_mk1_lod2.glb","mantis_mk1_collision.glb","mantis_mk1_review_board.png"],
      "license":"No repository license declared; confirm distribution terms before redistribution"
    }
    with open(os.path.join(output_dir,"mantis_mk1_training_record.json"),"w",encoding="utf-8") as f: json.dump(record,f,indent=2)
    if not os.path.isfile(glb) or os.path.getsize(glb)<4096: raise RuntimeError("GLB export missing or unexpectedly small")
    for artifact in ("mantis_mk1_lod1.glb","mantis_mk1_lod2.glb","mantis_mk1_collision.glb"):
        artifact_path=os.path.join(output_dir,artifact)
        if not os.path.isfile(artifact_path) or os.path.getsize(artifact_path)<1024: raise RuntimeError("{} missing or unexpectedly small".format(artifact))
    print("MANTIS_BUILD_OK glb_bytes={} meshes={} outputs={}".format(os.path.getsize(glb),len(meshes),len(view_paths)+2))

if __name__=="__main__": build(parse_args().output_dir)

# The latest source revision includes the multi-view training-record output.


