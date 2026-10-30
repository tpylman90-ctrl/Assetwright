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
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="generated")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def mat(name, color, metallic=0.25, roughness=0.45, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    # Base-color images are embedded in GLB, since Blender-only procedural
    # shaders are not portable to Godot/glTF viewers.
    size=256; rng=random.Random(name); marks=bytearray(size*size)
    for _ in range(190):
        x=rng.randrange(size); y=rng.randrange(size); length=rng.randrange(5,24)
        dx,dy=rng.choice(((1,0),(1,1),(1,-1),(0,1)))
        for k in range(length):
            px=x+dx*k; py=y+dy*k
            if 0<=px<size and 0<=py<size: marks[py*size+px]=1
    pix=array("f")
    for y in range(size):
        for x in range(size):
            shade=rng.uniform(.91,1.035)
            if marks[y*size+x]: shade*=.61
            pix.extend((min(1,color[0]*shade),min(1,color[1]*shade),min(1,color[2]*shade),1.0))
    image=bpy.data.images.new(name+" | packed albedo",width=size,height=size,alpha=False)
    image.pixels.foreach_set(pix); image.pack()
    tex=nodes.new("ShaderNodeTexImage"); tex.name=name+" embedded wear albedo"; tex.image=image
    links.new(tex.outputs["Color"],bsdf.inputs["Base Color"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 155.0
    noise.inputs["Detail"].default_value = 2.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.018
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        c = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        s = bsdf.inputs.get("Emission Strength")
        if c: c.default_value = (*color, 1.0)
        if s: s.default_value = emission
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
        b.segments = 3
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
    bpy.ops.mesh.primitive_torus_add(major_segments=40, minor_segments=10, major_radius=major, minor_radius=minor, location=loc)
    o=bpy.context.object; o.name=name; o.data.materials.append(material)
    o.rotation_euler={"X":(0,math.pi/2,0),"Y":(math.pi/2,0,0),"Z":(0,0,0)}[axis]
    return o


def beam_between(name, a, b, width, material, depth=None, bevel=0.02):
    a,b=Vector(a),Vector(b); d=b-a; mid=(a+b)*.5
    o=box(name, mid, (width, depth or width, d.length), material, bevel)
    o.rotation_euler=d.to_track_quat("Z","Y").to_euler()
    return o


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
    for i in range(12):
        a=math.tau*i/12
        px=x+math.cos(a)*.51*scale; py=y+math.sin(a)*.51*scale
        cyl(label+" rim fastener %02d"%i, (px,py,z+.16*scale), .025*scale, .035*scale, gold, "Z", 12)
    for i in range(8):
        a=math.tau*i/8
        px=x+math.cos(a)*.39*scale; py=y+math.sin(a)*.39*scale
        rod(label+" emitter vane %02d"%i,(px,py,z+.25*scale),(x+math.cos(a+.18)*.26*scale,y+math.sin(a+.18)*.26*scale,z+.25*scale),.018*scale,titanium,8)


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

    # Low central exoskeleton spine, keel, and open lattice floor.
    loft("Armored central keel",[(-1.55,.28,1.18,.92),(-1.10,.52,1.32,.83),(.20,.56,1.36,.78),(1.25,.66,1.48,.80),(1.72,.55,1.42,.88)],olive)
    box("Lower keel skid",(0,.15,.74),(.44,2.28,.16),black,.06)
    for x in (-.48,.48):
        rod("Longitudinal chassis tube",(x,-1.18,1.02),(x,1.58,1.05),.055,black,20)
        rod("Upper spine rail",(x,-.85,1.35),(x,1.40,1.45),.048,titanium,16)
    for y in (-.92,-.25,.52,1.24):
        rod("Crossmember",(-.53,y,1.0),(.53,y,1.0),.052,black,16)
        for x in (-.53,.53):
            cyl("Crossmember clevis",(x,y,1.0),.082,.08,gold,"X",24)

    # Open cockpit cell with seat, shoulder hoops, braced canopy frame, and controls.
    box("Cockpit floor pan",(0,.12,1.08),(.78,1.20,.12),black,.045)
    box("Pilot seat shell",(0,.18,1.38),(.54,.64,.18),olive,.09,(-.20,0,0))
    box("Seat cushion",(0,.04,1.49),(.43,.43,.16),leather,.08,(-.18,0,0))
    box("Seat back pad",(0,.46,1.72),(.44,.14,.62),leather,.09,(-.16,0,0))
    for x in (-.22,.22):
        box("Seat bolster",(x,.29,1.64),(.10,.38,.30),olive_light,.04,(-.18,0,0))
    for x in (-.18,.18):
        rod("Harness strap",(x,.14,1.91),(x*.5,.02,1.48),.025,gold,12)
    # A bolted roll cage defines the open cockpit silhouette.
    for x in (-.48,.48):
        rod("Front canopy pillar",(x,-.68,1.24),(x*.68,-.30,2.10),.045,titanium,16)
        rod("Rear canopy pillar",(x,.93,1.28),(x*.84,.48,2.08),.05,titanium,16)
        rod("Upper cockpit rail",(x*.68,-.30,2.10),(x*.84,.48,2.08),.045,black,16)
        rod("Sill rail",(x,-.65,1.23),(x,.88,1.25),.052,black,16)
    rod("Windshield crossbar",(-.32,-.30,2.10),(.32,-.30,2.10),.036,gold,14)
    rod("Rear canopy crossbar",(-.40,.48,2.08),(.40,.48,2.08),.036,gold,14)
    for x in (-.27,.27):
        rod("Canopy triangulation",(x,-.27,2.08),(x,.16,1.98),.025,titanium,12)
        rod("Canopy triangulation",(x,.16,1.98),(x*.82,.47,2.07),.025,titanium,12)
    box("Instrument pod",(0,-.38,1.83),(.59,.20,.16),black,.035,(-.18,0,0))
    box("Holographic instrument screen",(0,-.40,1.93),(.39,.035,.09),glass,.018,(-.18,0,0))
    for x in (-.21,.21): cyl("Cockpit control knob",(x,-.50,1.84),.035,.03,gold,"Y",16)

    # Front arm assemblies: paired mantis limbs, each with a triangular exoframe,
    # hinge stack, protected hydraulic actuator, and broad leading-edge armor.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        root=(side*.43,-.48,1.12); elbow=(side*1.18,-1.32,.78); wrist=(side*2.13,-2.62,.53)
        beam_between(label+" inner arm upper spar",root,elbow,.105,black,.115,.022)
        beam_between(label+" inner arm lower spar",(side*.50,-.28,.91),(side*1.24,-1.26,.57),.074,titanium,.078,.018)
        beam_between(label+" arm diagonal brace",(side*.50,-.28,.91),elbow,.060,gold,.065,.014)
        beam_between(label+" outer arm upper spar",elbow,wrist,.092,black,.095,.018)
        beam_between(label+" outer arm lower spar",(side*1.22,-1.30,.51),(side*2.10,-2.56,.35),.062,titanium,.066,.015)
        beam_between(label+" outer arm triangulation",elbow,(side*2.10,-2.56,.35),.052,gold,.056,.012)
        # Articulated joints are visibly layered instead of hidden in a smooth shell.
        for point,r in ((root,.15),(elbow,.19),(wrist,.14)):
            cyl(label+" exposed arm pivot",point,r,.16,black,"X",32)
            torus(label+" pivot retaining ring",(point[0]+side*.09,point[1],point[2]),r*.72,.025,gold,"X")
            cyl(label+" pivot cap",(point[0]+side*.12,point[1],point[2]),r*.43,.035,titanium,"X",24)
            cyl(label+" pivot bolt",(point[0]+side*.145,point[1],point[2]),r*.15,.018,dark,"X",16)
        # Raked shock piston / sleeve.
        beam_between(label+" actuator outer sleeve",(side*.66,-.48,1.08),(side*1.31,-1.30,.85),.074,dark,.074,.014)
        beam_between(label+" actuator polished ram",(side*.88,-.76,1.01),(side*1.42,-1.44,.82),.031,titanium,.032,.008)
        # Sculpted segmented forearm fairing, outlined in warning gold.
        fair=box(label+" olive arm armor",(side*1.62,-1.96,.70),(.40,1.56,.20),olive,.08,(0,0,side*.43))
        box(label+" arm crown plate",(side*1.62,-1.96,.815),(.28,1.34,.035),olive_light,.035,(0,0,side*.43))
        rod(label+" armor edge piping",(side*1.45,-1.35,.83),(side*1.99,-2.54,.63),.014,gold,10)
        # small segmented access panels and fasteners on each limb
        for y in (-1.55,-1.90,-2.25):
            box(label+" arm panel seam",(side*1.62,y,.84),(.24,.025,.018),dark,.006,(0,0,side*.43))
        for y in (-2.36,-1.48):
            cyl(label+" arm captive screw",(side*1.62,y,.845),.025,.02,titanium,"Z",12)
        # Wrist ring joins the arm directly to the hover cell.
        rod(label+" hover-cell mount",(side*2.10,-2.56,.49),(side*2.50,-2.78,.48),.075,black,20)
        make_hover_cell(side*2.65,-2.88,.34,1.0,label+" forward hover cell",(olive,black,titanium,glow,gold))

    # Rear saddle, modular equipment pods, and visibly serviceable mounting rails.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        rod(label+" equipment pod rail",(side*.52,.45,1.10),(side*1.28,1.02,1.16),.075,black,20)
        rod(label+" pod diagonal cradle",(side*.52,.82,.91),(side*1.26,.95,1.12),.060,titanium,16)
        box(label+" utility pod armored case",(side*1.17,.99,1.35),(.72,1.08,.72),olive,.09,(0,0,side*.06))
        box(label+" pod end cap",(side*1.17,1.55,1.35),(.58,.12,.58),olive_light,.045)
        box(label+" pod recessed panel",(side*1.17,.97,1.73),(.45,.60,.025),black,.025)
        box(label+" pod panel insert",(side*1.17,.97,1.75),(.34,.47,.018),olive,.018)
        # Rail channels and panel latches establish engineered scale.
        for xoff in (-.24,.24):
            rod(label+" pod longitudinal seam",(side*1.17+xoff,.51,1.70),(side*1.17+xoff,1.43,1.70),.012,gold,8)
        for y in (.62,1.35):
            for z in (1.11,1.57):
                cyl(label+" pod corner bolt",(side*1.17+side*.38,y,z),.032,.025,titanium,"X",12)
        for xoff in (-.14,.14):
            box(label+" pod vent recess",(side*1.17+xoff,.43,1.35),(.07,.025,.28),dark,.01)
            for i in range(4):
                box(label+" pod vent vane",(side*1.17+xoff,.41,1.25+i*.065),(.055,.02,.018),titanium,.006)
        add_text(label+" pod serial", "01", (side*1.17,1.79,1.24),.27,titanium,(math.pi/2,0,0))
        add_text(label+" pod marking", "MANTIS", (side*1.17,1.79,1.06),.075,gold,(math.pi/2,0,0))
        # Back-facing turbine pairs set flush into the rear drive cluster.
        tx=side*.47
        cyl(label+" turbine armored drum",(tx,1.78,1.34),.39,.72,black,"Y",48)
        torus(label+" turbine machined rim",(tx,2.15,1.34),.34,.055,titanium,"Y")
        torus(label+" turbine amber seal",(tx,2.18,1.34),.265,.022,gold,"Y")
        cyl(label+" turbine recessed throat",(tx,2.17,1.34),.245,.08,dark,"Y",40)
        cyl(label+" turbine hot core",(tx,2.225,1.34),.165,.035,hot,"Y",40)
        torus(label+" turbine inner halo",(tx,2.25,1.34),.19,.016,hot,"Y")
        for i in range(10):
            a=math.tau*i/10
            rod(label+" turbine stator vane",(tx+math.cos(a)*.22,2.23,1.34+math.sin(a)*.22),(tx+math.cos(a+.12)*.13,2.23,1.34+math.sin(a+.12)*.13),.016,titanium,8)
        for i in range(8):
            a=math.tau*i/8
            cyl(label+" turbine rim bolt",(tx+math.cos(a)*.34,2.205,1.34+math.sin(a)*.34),.025,.025,gold,"Y",12)

    # Tail fin structures rise behind the open cockpit, with struts and stiffeners.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        beam_between(label+" tail fin spar",(side*.55,1.05,1.32),(side*1.32,1.66,2.38),.11,black,.12,.024)
        beam_between(label+" tail fin brace",(side*.72,1.44,1.25),(side*1.28,1.57,2.27),.055,titanium,.06,.012)
        fin=box(label+" swept olive tail fin",(side*1.02,1.49,1.98),(.48,.88,.10),olive,.045,(side*.28,side*.38,side*.12))
        box(label+" tail fin inset",(side*1.02,1.46,2.04),(.27,.55,.018),olive_light,.015,(side*.28,side*.38,side*.12))
        for y in (1.27,1.48,1.69):
            box(label+" fin panel line",(side*1.02,y,2.055),(.23,.018,.012),dark,.004,(side*.28,side*.38,side*.12))
        cyl(label+" fin hinge",(side*.60,1.10,1.40),.095,.20,gold,"X",24)

    # Two compact aft lift units balance the nose arms; their rings remain visible in side/top views.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        beam_between(label+" aft lift strut",(side*.72,.72,.95),(side*.92,1.25,.60),.07,black,.075,.016)
        make_hover_cell(side*1.05,1.15,.35,.62,label+" aft hover cell",(olive,black,titanium,glow,gold))

    # Functional linkage detail, fluid lines, and hardware across the exoframe.
    for side,label in ((-1,"Port"),(1,"Starboard")):
        for y in (-.6,.05,.62):
            for z in (1.00,1.14):
                cyl(label+" frame clamp",(side*.50,y,z),.075,.12,gold,"X",20)
        # Two parallel hydraulic hoses follow the outside arm.
        for offset in (-.08,.08):
            pts=[(side*(1.15+offset),-1.28,.83),(side*(1.42+offset),-1.68,.78),(side*(1.78+offset),-2.18,.61)]
            for a,b in zip(pts,pts[1:]): rod(label+" braided hydraulic line",a,b,.018,dark,10)
        for i in range(6):
            y=-.18+i*.26
            box(label+" side sill tread",(side*.54,y,1.02),(.09,.14,.025),titanium,.008)

    # Studio-only ground, lighting, and cameras. The floor is excluded from export.
    floor_mat=mat("Studio floor (preview only)",(.095,.11,.13),.25,.72)
    box("Preview floor",(0,-.1,.015),(200,200,.10),floor_mat,0)
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    if hasattr(scene,"eevee"):
        scene.eevee.taa_render_samples=48
        scene.eevee.use_gtao=True
        scene.eevee.gtao_distance=.25
        scene.eevee.gtao_factor=1.25
        scene.eevee.use_soft_shadows=True
    scene.world.use_nodes=True
    world=scene.world.node_tree.nodes.get("Background")
    if world: world.inputs["Color"].default_value=(.12,.15,.19,1); world.inputs["Strength"].default_value=.45
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
    bpy.ops.object.light_add(type="AREA",location=(1,-5,8)); key=bpy.context.object; key.data.energy=1050; key.data.shape="DISK"; key.data.size=6; aim(key,(0,0,1))
    bpy.ops.object.light_add(type="AREA",location=(-5,1,4)); rim=bpy.context.object; rim.data.energy=900; rim.data.color=(.44,.68,1); rim.data.size=5; aim(rim,(0,0,1))
    bpy.ops.object.light_add(type="AREA",location=(4,4,5)); warm=bpy.context.object; warm.data.energy=850; warm.data.color=(1,.56,.25); warm.data.size=4; aim(warm,(0,0,1))
    bpy.ops.object.camera_add(location=(7,-9,6)); cam=bpy.context.object; cam.data.type="ORTHO"; cam.data.ortho_scale=8.8; aim(cam,(0,-.05,1.05)); scene.camera=cam

    os.makedirs(output_dir,exist_ok=True)
    # Export selected asset meshes only; no floor, cameras, or lights.
    bpy.ops.object.select_all(action="DESELECT")
    for o in scene.objects:
        if o.type=="MESH" and o.name!="Preview floor": o.select_set(True)
    meshes=[o for o in scene.objects if o.type=="MESH" and o.name!="Preview floor"]
    # Smart UVs are deterministic and keep all material detail inside the GLB.
    for o in meshes:
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active=o
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.uv.smart_project(island_margin=.02); bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    glb=os.path.abspath(os.path.join(output_dir,"mantis_mk1.glb"))
    bpy.ops.export_scene.gltf(filepath=glb,export_format="GLB",export_apply=True)

    specs=[
      ("hero_3q",(7,-9,6),(0,-.05,1.05),8.8),
      ("front",(0,-12,3.2),(0,-.1,1.05),7.5),
      ("side",(12,0,3.0),(0,-.1,1.05),8.5),
      ("rear",(0,12,3.1),(0,.1,1.1),7.5),
      ("top",(0,-.1,13),(0,-.1,.9),8.4),
    ]
    view_paths=[]
    for name,loc,target,scale in specs:
        cam.location=loc; cam.data.ortho_scale=scale; aim(cam,target); scene.camera=cam
        scene.render.resolution_x=960; scene.render.resolution_y=720
        path=os.path.abspath(os.path.join(output_dir,"mantis_mk1_"+name+".png")); scene.render.filepath=path
        try: bpy.ops.render.render(write_still=True)
        except Exception as exc:
            if scene.render.engine!="BLENDER_EEVEE": raise
            print("Eevee offscreen render failed; switching to Workbench:",exc)
            scene.render.engine="BLENDER_WORKBENCH"; scene.display.shading.light="STUDIO"; scene.display.shading.color_type="MATERIAL"; scene.display.shading.show_cavity=True
            bpy.ops.render.render(write_still=True)
        view_paths.append(path)

    # Compose five review views into a portable board with the hero view prominent.
    images=[bpy.data.images.load(p,check_existing=False) for p in view_paths]
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

    depsgraph=bpy.context.evaluated_depsgraph_get()
    triangle_count=0
    for ob in meshes:
        evaluated=ob.evaluated_get(depsgraph)
        evaluated_mesh=evaluated.to_mesh()
        triangle_count+=sum(max(0,len(poly.vertices)-2) for poly in evaluated_mesh.polygons)
        evaluated.to_mesh_clear()
    if triangle_count>60000:
        raise RuntimeError("Mantis exceeds the 60,000 triangle game budget: {}".format(triangle_count))
    record={
      "asset_id":"mantis_mk1_hover_racer",
      "display_name":"Mantis / MK I",
      "generator":"Assetwright procedural Blender ground-truth v1",
      "reference":"User-provided MANTIS / MK I concept sheet (2963.png); source image is not redistributed by this build.",
      "prompt":"Create a game-ready experimental exposed-frame hover speedster called Mantis / MK I. Use a low forward-swept profile and a rigid angular exoskeleton with olive-drab armor plates, black structural tubing, brushed titanium fittings, and amber caution hardware. Build twin articulated mantis-like front arms that sweep forward and outward and terminate in layered circular hover repulsor cells. Keep the single-seat cockpit open, with an exposed seat, harness, compact instrument panel, and a skeletal roll/canopy cage. Add modular armored side equipment pods with visible panel seams, vents, latches, and 01 markings. Place a paired visible turbine cluster at the rear, with concentric machined rings, stator vanes, and amber cores. Add swept tail fins and two smaller aft hover cells. Show believable mechanical connections, exposed actuators, hoses, fasteners, and layered armor; preserve the open-frame silhouette and separate readable parts. Export a textured GLB for a real-time game.",
      "negative_prompt":"No enclosed car body, no conventional wheels or tires, no landing legs, no smooth one-piece shell, no low-poly toy appearance, no omitted front arms, no missing hover cells, no opaque canopy, no unsupported floating details, no text outside modeled markings.",
      "game_target":{"engine":"Godot","format":"GLB","intended_use":"Real-time hover-racing game asset","triangle_budget_target":60000,"triangle_count":triangle_count,"texture_policy":"Procedural material response; no external image dependency"},
      "feature_labels":["open_exoskeleton","twin_forward_articulated_arms","front_hover_cells","open_single_seat_cockpit","skeletal_canopy_frame","modular_side_pods","paired_rear_turbines","swept_tail_fins","aft_hover_cells","olive_metal_materials","mechanical_hardware"],
      "axis_convention":{"forward":"-Y","right":"+X","up":"+Z"},
      "views":["hero_3q","front","side","rear","top"],
      "files":["mantis_mk1.glb","mantis_mk1_review_board.png"],
      "license":"No repository license declared; confirm distribution terms before redistribution"
    }
    with open(os.path.join(output_dir,"mantis_mk1_training_record.json"),"w",encoding="utf-8") as f: json.dump(record,f,indent=2)
    if not os.path.isfile(glb) or os.path.getsize(glb)<4096: raise RuntimeError("GLB export missing or unexpectedly small")
    print("MANTIS_BUILD_OK glb_bytes={} meshes={} outputs={}".format(os.path.getsize(glb),len(meshes),len(view_paths)+2))

if __name__=="__main__": build(parse_args().output_dir)

# The latest source revision includes the multi-view training-record output.
