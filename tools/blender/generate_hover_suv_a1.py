"""Assetwright A1 hover racing SUV: original reference-board-driven first pass.
Blender 3.6+/4.x. Axes: front -Y, rear +Y, up +Z. Editable procedural source.
Reference: /Assetwright/References/Hover_Race_SUV_Concept_A1.png
"""
import argparse, json, math, os, sys
import bpy
from mathutils import Vector

def args():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir", default="generated/hover_suv_a1")
    p.add_argument("--quick", action="store_true")
    return p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

def mat(name, rgb, metallic=0, roughness=.4, emission=0, alpha=1):
    m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,alpha);m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*rgb,1)
    p.inputs["Metallic"].default_value=metallic
    p.inputs["Roughness"].default_value=roughness
    p.inputs["Alpha"].default_value=alpha
    if emission:
        socket=p.inputs.get("Emission Color") or p.inputs.get("Emission")
        if socket: socket.default_value=(*rgb,1)
        strength=p.inputs.get("Emission Strength")
        if strength:strength.default_value=emission
    if alpha<1:
        if hasattr(m,"surface_render_method"):m.surface_render_method="DITHERED"
        elif hasattr(m,"blend_method"):m.blend_method="HASHED"
    return m

def mesh(name, verts, faces, material, smooth=True):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces);data.update();data.materials.append(material)
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    for polygon in data.polygons:polygon.use_smooth=smooth
    return ob

def subd(ob, levels=1):
    mod=ob.modifiers.new("Shape-preserving subdivision","SUBSURF")
    mod.levels=levels;mod.render_levels=levels
    return ob

def bevel(ob, radius=.03, segments=2):
    if radius:
        b=ob.modifiers.new("Manufactured edge breaks","BEVEL")
        b.width=radius;b.segments=segments
    ob.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
    return ob

def box(name, location, dimensions, material, radius=.03, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    ob=bpy.context.object;ob.name=name;ob.dimensions=dimensions
    ob.rotation_euler=rotation
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    ob.data.materials.append(material)
    return bevel(ob,radius)

def curve(name, points, radius, material):
    data=bpy.data.curves.new(name,"CURVE");data.dimensions="3D"
    data.resolution_u=12;data.bevel_depth=radius;data.bevel_resolution=2
    spline=data.splines.new("POLY");spline.points.add(len(points)-1)
    for p,v in zip(spline.points,points):p.co=(*v,1)
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    ob.data.materials.append(material)
    return ob

def surface(name, rows, material):
    """Quad loft. Each station supplies equal number of XYZ control points."""
    vertices=[v for row in rows for v in row]
    n=len(rows[0]);faces=[]
    for j in range(len(rows)-1):
        for i in range(n-1):
            faces.append((j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i))
    ob=mesh(name,vertices,faces,material)
    return ob

def ring(name,x,y,profile,material,segments=32):
    """Axially stepped elliptical lift-pod shell: profile entries (z, rx, ry)."""
    verts=[];faces=[]
    for z,rx,ry in profile:
        for i in range(segments):
            t=math.tau*i/segments
            verts.append((x+rx*math.cos(t),y+ry*math.sin(t),z))
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments
            faces.append((a,b,b+segments,a+segments))
    return mesh(name,verts,faces,material)

def vehicle():
    silver=mat("A1 ceramic silver body",(.62,.67,.75),.66,.27)
    red=mat("A1 racing crimson",(.54,.018,.028),.37,.28)
    black=mat("A1 carbon and intakes",(.025,.033,.047),.18,.52)
    dark=mat("A1 satin graphite lower body",(.075,.085,.105),.52,.39)
    glass=mat("A1 smoked dark sapphire glazing",(.045,.09,.125),.16,.17,alpha=.7)
    cyan=mat("A1 cyan hover emission",(.015,.72,1.0),.12,.24,emission=4)
    cabin=mat("A1 dark cabin",(.09,.11,.14),.03,.7)
    upholstery=mat("A1 racing red interior",(.35,.018,.027),.02,.6)

    # Low-density full-width master shell; no floating wing-like outer fenders.
    # Each section: y, width, bottom z, shoulder z, crown z.
    sections=[
       (-3.54,.70,.68,1.03,1.12),
       (-3.32,1.22,.60,1.10,1.24),
       (-2.90,1.69,.58,1.20,1.34),
       (-2.43,1.86,.57,1.28,1.39),
       (-1.82,1.79,.60,1.32,1.40),
       (-1.10,1.70,.62,1.36,1.43),
       (-.40,1.75,.62,1.39,1.47),
       (.36,1.83,.62,1.44,1.52),
       (1.16,1.94,.62,1.49,1.55),
       (1.90,2.00,.61,1.50,1.57),
       (2.46,1.92,.61,1.43,1.51),
       (3.00,1.74,.63,1.32,1.41),
       (3.36,1.48,.67,1.20,1.26)]
    verts=[];faces=[];n=16
    for y,w,bot,s,crown in sections:
        pts=[(-w*.78,bot),(-w,bot+.14),(-w,bot+.44),
            (-w, s-.10),(-w+.12,s+.07),(-w*.73,s+.13),
            (-w*.40,crown), (0,crown+.035),(w*.40,crown),
            (w*.73,s+.13),(w-.12,s+.07),(w,s-.10),
            (w,bot+.44),(w,bot+.14),(w*.78,bot),(0,bot-.025)]
        verts.extend((x,y,z) for x,z in pts)
    for j in range(len(sections)-1):
        for i in range(n):
            faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces += [tuple(reversed(range(n))),tuple(range((len(sections)-1)*n,len(sections)*n))]
    body=mesh("PRIMARY / continuous sculpted SUV body",verts,faces,silver)
    subd(body,1)

    # Lower rocker is an actual deep, recessed assembly rather than a light strip.
    for side in (-1,1):
        s="L" if side<0 else "R"
        curve(s+" sculpted shoulder seam",[(side*1.59,-2.95,1.23),
              (side*1.73,-2.30,1.32),(side*1.60,-1.25,1.37),
              (side*1.75,.1,1.48),(side*1.92,1.48,1.53),
              (side*1.77,2.75,1.35)],.014,dark)
        box(s+" true recessed sill shadow",(side*1.74,-.03,.82),
            (.082,4.25,.19),black,.035)
        box(s+" shaped carbon lower rocker",(side*1.76,-.03,.65),
            (.21,4.05,.13),dark,.04)

    # Body-following crimson hood stripes and diagonal racing shoulder graphics.
    for side in (-1,1):
        s="L" if side<0 else "R"
        sideband=surface(s+" hood paint band",[
           [(side*.19,-3.42,1.174),(side*.43,-3.42,1.16)],
           [(side*.24,-3.1,1.342),(side*.48,-3.1,1.335)],
           [(side*.29,-2.5,1.444),(side*.57,-2.5,1.43)],
           [(side*.31,-1.91,1.458),(side*.59,-1.91,1.46)],
           [(side*.28,-1.38,1.497),(side*.51,-1.38,1.48)]],red)
        sideband.data.polygons.foreach_set if False else None
        surface(s+" rear speed graphic",[
           [(side*1.63,.92,1.45),(side*1.76,.92,1.44)],
           [(side*1.83,1.45,1.5),(side*1.94,1.45,1.49)],
           [(side*1.86,2.20,1.44),(side*1.96,2.20,1.43)],
           [(side*1.64,2.75,1.32),(side*1.81,2.75,1.32)]],red)

    # Roof packaging: windshield/front -1.26 to -.46, roof to +1.69.
    box("Cockpit deep black perimeter", (0,.35,1.48),(2.46,3.5,.10),black,.05)
    surface("Front swept sapphire windshield",[
       [(-1.20,-1.30,1.40),(0,-1.38,1.48),(1.20,-1.30,1.40)],
       [(-.91,-.52,2.07),(0,-.59,2.15),(.91,-.52,2.07)]],glass)
    surface("Roof metallic primary crown",[
       [(-.94,-.56,2.075),(0,-.64,2.15),(.94,-.56,2.075)],
       [(-1.03,.58,2.15),(0,.58,2.22),(1.03,.58,2.15)],
       [(-1.01,1.61,2.10),(0,1.65,2.18),(1.01,1.61,2.10)]],silver)
    surface("Sloping rear sapphire hatch glass",[
       [(-1.02,1.61,2.10),(0,1.65,2.18),(1.02,1.61,2.10)],
       [(-1.28,2.42,1.48),(0,2.48,1.57),(1.28,2.42,1.48)]],glass)
    for side in (-1,1):
        s="L" if side<0 else "R"
        # Side glazing split by structurally fitted B-pillar.
        surface(s+" front side glazing",[
            [(side*1.20,-1.30,1.40),(side*.91,-.52,2.07)],
            [(side*1.24,.35,1.44),(side*1.01,.35,2.14)]],glass)
        surface(s+" rear side glazing",[
            [(side*1.24,.39,1.44),(side*1.01,.39,2.14)],
            [(side*1.31,1.61,1.51),(side*1.01,1.61,2.10)],
            [(side*1.30,2.22,1.49),(side*1.12,1.92,1.87)]],glass)
        curve(s+" A pillar",[(side*1.21,-1.31,1.37),(side*.91,-.52,2.09)],.045,black)
        curve(s+" B pillar",[(side*1.24,.37,1.42),(side*1.01,.39,2.18)],.049,black)
        curve(s+" C pillar",[(side*1.31,2.22,1.48),(side*1.01,1.61,2.11)],.067,silver)
        curve(s+" roof rail",[(side*.91,-.52,2.13),(side*1.04,.52,2.20),
              (side*1.02,1.61,2.15)],.035,black)
        box(s+" door belt rail",(side*1.19,.41,1.405),(.07,2.95,.07),dark,.025)
        box(s+" side mirror",(side*1.38,-.85,1.60),(.28,.39,.15),black,.06)
        box(s+" deeply mounted lower intake",(side*1.78,-.86,1.00),
             (.20,.73,.22),black,.035)

    # Four separate hover boots: recessed, blocky aerodynamic shrouds with
    # physically distinct upper collar, graphite casing and emissive levitation ring.
    for side in (-1,1):
        for ypos,tag in [(-2.45,"front"),(2.0,"rear")]:
            cx=side*1.52;label=("L" if side<0 else "R")+" "+tag
            ring(label+" integral fender shroud",cx,ypos,
                [(.75,.51,.68),(.96,.57,.75),(1.13,.61,.79)],silver,32)
            ring(label+" hover module dark casing",cx,ypos,
                [(.35,.44,.58),(.41,.49,.64),(.69,.54,.69),(.82,.56,.72)],black,32)
            ring(label+" luminous field coil",cx,ypos,
                [(.31,.38,.53),(.34,.47,.61),(.39,.47,.61),(.42,.39,.53)],cyan,32)
            ring(label+" shielded lower diffuser",cx,ypos,
                [(.22,.20,.38),(.29,.37,.54),(.30,.40,.56)],dark,32)
            box(label+" hover suspension tie",(side*1.20,ypos,.71),
                (.54,.34,.22),dark,.065)
            # Casing inset sculpted with directional dark metal slats.
            for k in (-1,0,1):
                box(label+" aft ventilation "+str(k),
                    (side*1.96,ypos+k*.20,.71),(.027,.12,.28),black,.016)

    # Distinct front fascia, air intake depth, LED light slits and aero skirt.
    box("Nose black inset main grille",(0,-3.46,.92),(1.48,.10,.31),black,.07)
    box("Nose lower carbon chin",(0,-3.53,.68),(1.80,.21,.17),dark,.07)
    for side in (-1,1):
        s="L" if side<0 else "R"
        box(s+" razor front LED strip",(side*.98,-3.37,1.205),
            (.75,.045,.045),cyan,.015)
        box(s+" front auxiliary light",(side*1.40,-3.31,.78),
            (.22,.055,.085),cyan,.017)
        box(s+" rear brake illuminated bar",(side*.74,3.32,1.36),
            (1.22,.055,.095),red,.018)
    box("Rear carbon diffuser",(0,3.28,.74),(2.70,.25,.30),dark,.07)
    box("Rear hatch dark center panel",(0,3.25,1.34),(2.22,.10,.37),black,.045)
    box("Roof spoiler aerodynamic blade",(0,2.61,2.09),
        (2.34,.48,.09),silver,.048)
    for side in (-1,1):
        box(("L" if side<0 else "R")+" spoiler pedestal",
            (side*.94,2.36,1.97),(.15,.38,.19),dark,.04)

    # Actual cockpit blockout, spatially beneath glazing (not floating outside).
    box("Cabin black floor",(0,.39,1.05),(2.23,2.82,.12),cabin,.09)
    box("Dashboard integrated upper brow",(0,-1.13,1.47),(2.18,.46,.22),dark,.09)
    box("Instrument binnacle",(-.53,-1.24,1.62),(.67,.30,.12),black,.055)
    box("Wide center display",(.16,-1.37,1.56),(.46,.08,.19),cyan,.024)
    box("Deep center console",(0,.15,1.20),(.32,1.57,.22),dark,.06)
    for side in (-1,1):
        x=side*.53
        box(("L" if side<0 else "R")+" bolstered seat base",
            (x,.64,1.22),(.78,.83,.16),upholstery,.13)
        box(("L" if side<0 else "R")+" seatback",
            (x,.99,1.52),(.74,.20,.62),upholstery,.095,
            (-.14,0,0))
        box(("L" if side<0 else "R")+" headrest",
            (x,1.12,1.84),(.38,.20,.19),cabin,.065)
    return {"source":"Hover Race SUV Concept A1", "front_axis":"-Y",
            "height":2.22,"length":6.90,"width_approx":4.0,
            "pods":4,"lod0_triangles_max":120000}

def tri_count(objects):
    dg=bpy.context.evaluated_depsgraph_get();total=0
    for ob in objects:
        if ob.type not in {"MESH","CURVE"}:continue
        o=ob.evaluated_get(dg)
        temp=o.to_mesh()
        if temp:
            temp.calc_loop_triangles();total+=len(temp.loop_triangles)
            o.to_mesh_clear()
    return total

def export_glb(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB",
                              use_selection=True,export_apply=True,
                              export_animations=False)

def export_lod(path, originals, ratio):
    bpy.ops.object.select_all(action="DESELECT")
    copies=[];dg=bpy.context.evaluated_depsgraph_get()
    for original in originals:
        if original.type not in {"MESH","CURVE"}:continue
        evaluated=original.evaluated_get(dg)
        data=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=dg)
        if not data:continue
        ob=bpy.data.objects.new("LOD "+original.name,data)
        bpy.context.collection.objects.link(ob);ob.matrix_world=original.matrix_world.copy()
        if len(data.polygons)>45:
            dec=ob.modifiers.new("Game LOD reduction","DECIMATE")
            dec.ratio=ratio
        copies.append(ob)
    export_glb(path,copies)
    for ob in copies:bpy.data.objects.remove(ob,do_unlink=True)

def render_review(objects, path, eye, target):
    scene=bpy.context.scene
    scene.camera.location=eye
    direction=Vector(target)-scene.camera.location
    scene.camera.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=path
    bpy.ops.render.render(write_still=True)

def main():
    a=args();os.makedirs(a.output_dir,exist_ok=True)
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    brief=vehicle()
    originals=list(bpy.context.scene.objects)
    count=tri_count(originals)
    if count>120000:raise RuntimeError("LOD0 exceeds budget: "+str(count))
    export_glb(os.path.join(a.output_dir,"hover_suv_a1.glb"),originals)
    if not a.quick:
        export_lod(os.path.join(a.output_dir,"hover_suv_a1_lod1.glb"),originals,.36)
        export_lod(os.path.join(a.output_dir,"hover_suv_a1_lod2.glb"),originals,.12)
    box("Preview floor",(0,0,.02),(28,28,.06),
        mat("Preview neutral studio surface",(.18,.20,.24),.05,.85),.01)
    world=bpy.context.scene.world
    if world:
        world.use_nodes=True
        bg=world.node_tree.nodes.get("Background")
        if bg:bg.inputs["Color"].default_value=(.12,.14,.18,1);bg.inputs["Strength"].default_value=.8
    bpy.ops.object.camera_add(location=(7,-10,5))
    cam=bpy.context.object;bpy.context.scene.camera=cam;cam.data.type="ORTHO";cam.data.ortho_scale=10.2
    bpy.ops.object.light_add(type="AREA",location=(-5,-3,9))
    bpy.context.object.data.energy=2400;bpy.context.object.data.shape="DISK";bpy.context.object.data.size=10
    bpy.ops.object.light_add(type="AREA",location=(5,3,7))
    bpy.context.object.data.energy=1900;bpy.context.object.data.size=8
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE" if bpy.app.version<(4,2,0) else "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x=960 if not a.quick else 640
    scene.render.resolution_y=640 if not a.quick else 460
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.view_settings.view_transform="Standard"
    for suffix,eye in [
        ("hero_3q",(7,-10,5)),("rear_3q",(7,10,5)),
        ("side",(10,0,3.2)),("top",(0,0,12)),
        ("front",(0,-12,3.3)),("rear",(0,12,3.3))]:
        render_review(originals,os.path.join(a.output_dir,"hover_suv_a1_"+suffix+".png"),eye,(0,0,1.12))
        if a.quick and suffix=="hero_3q":break
    record={"concept":"Hover Race SUV Concept A1",
        "reference_library_path":"/Assetwright/References/Hover_Race_SUV_Concept_A1.png",
        "stage":"first-pass geometry; requires visual review",
        "game_target":brief, "evaluated_lod0_triangles":count,
        "validation":"GLB generated and LOD0 source geometry budget checked"}
    with open(os.path.join(a.output_dir,"hover_suv_a1_record.json"),"w") as f:
        json.dump(record,f,indent=2)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(a.output_dir,"hover_suv_a1.blend"))
    print("HOVER_SUV_A1",json.dumps(record))

if __name__=="__main__":main()
