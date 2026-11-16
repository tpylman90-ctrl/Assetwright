"""Inspect user-authored Gemini catamaran GLB in actual Blender 4.5.3.
Geometry imported unmodified. Render PBR materials in Cycles.
"""
import json
from pathlib import Path
import bpy
from mathutils import Vector

out=Path.cwd()/"generated/gemini_v3"
source=out/"gemini_catamaran_trimesh.glb"
assert source.is_file() and source.stat().st_size>10000,source

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
parts=sorted((o for o in bpy.data.objects if o.type=="MESH"),key=lambda x:x.name)
assert len(parts)==8,[o.name for o in parts]
expected=["01_Pearl_Armor","02_Cosmic_Navy_Aero","03_Violet_Anodized","04_Brushed_Titanium",
          "05_Copper_Stators","06_Cockpit_Interiors","07_Tinted_Canopies","08_Cyan_Emission"]
assert all(any(o.name.startswith(n) for o in parts) for n in expected),[o.name for o in parts]

corners=[o.matrix_world@Vector(c) for o in parts for c in o.bound_box]
mins=[round(min(c[i] for c in corners),4) for i in range(3)]
maxs=[round(max(c[i] for c in corners),4) for i in range(3)]
tris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in parts)
assert tris>5000,tris
assert mins[2]>=-.06 and maxs[2]>=1.4,(mins,maxs)
assert maxs[0]>=1.70 and mins[0]<=-1.70,(mins,maxs)
report=dict(
    source="tools/blender/inbox/gemini_catamaran_v3.py",
    description="Gemini dual catamaran, 2 cockpits, 4 hover pods and twin plasma thrusters",
    user_script_truncated=True,
    assistant_completed="End of cyan emission section + material definitions + GLB export only",
    imported_by="Blender "+bpy.app.version_string,
    imported_mesh_groups=len(parts),
    mesh_names=[o.name for o in parts],
    triangle_count=tris,
    bounds_min_blender_xyz=mins,
    bounds_max_blender_xyz=maxs,
    source_coordinate_system="X width; Y up; Z forward",
    blender_coordinate_system="X width; Z up; -Y forward",
)
(out/"gemini_geometry_audit.json").write_text(json.dumps(report,indent=2))
print("GEMINI_BLENDER_IMPORT_OK",json.dumps(report),flush=True)

bpy.ops.object.select_all(action="DESELECT")
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
p=out/"gemini_catamaran_blender.glb"
bpy.ops.export_scene.gltf(filepath=str(p),export_format="GLB",
                           use_selection=True,export_apply=True,export_yup=True)
assert p.stat().st_size>10000
print("GEMINI_BLENDER_EXPORT_OK",p.stat().st_size,flush=True)

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED'
scene.render.threads=4
scene.render.resolution_x=960
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
scene.view_settings.view_transform="AgX"

world=bpy.data.worlds.new("Neutral hangar studio")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.14,.16,.19,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.65
scene.world=world

def aim(obj,point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat("-Z","Y").to_euler()
def light(name,loc,power,size):
    d=bpy.data.lights.new(name,'AREA')
    d.energy=power
    d.shape='DISK'
    d.size=size
    o=bpy.data.objects.new(name,d)
    scene.collection.objects.link(o)
    o.location=loc
    aim(o,(0,0,.85))
light("Key 5m white softbox",(4,-5,7),1200,5)
light("Fill 4m softbox",(-4,-2,4),800,4)
light("Top aft rim softbox",(-2,5,5),1350,4)

cam_data=bpy.data.cameras.new("Inspection orthographic lens")
cam=bpy.data.objects.new("Inspection orthographic lens",cam_data)
scene.collection.objects.link(cam)
scene.camera=cam
cam_data.type="ORTHO"
focus=(0,0,.86)
blend=out/"gemini_catamaran_master.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
assert blend.stat().st_size>10000
print("GEMINI_BLENDER_MASTER_OK",blend.stat().st_size,flush=True)

views=[
    ("front_3q",(6,-8,5.4),8.0),
    ("rear_3q",(-6,8,5.4),8.0),
    ("side",(-9,0,3.2),7.0),
    ("top",(0,0,12),8.0),
    ("front",(0,-11,3.0),5.4),
    ("rear",(0,11,3.0),5.4)
]
for name,position,scale in views:
    cam.location=position
    cam_data.ortho_scale=scale
    aim(cam,focus)
    png=out/("gemini_"+name+".png")
    scene.render.filepath=str(png)
    bpy.ops.render.render(write_still=True)
    assert png.is_file() and png.stat().st_size>10000
    print("GEMINI_BLENDER_PNG_OK",name,png.stat().st_size,flush=True)
print("GEMINI_BLENDER_ALL_OK",flush=True)
