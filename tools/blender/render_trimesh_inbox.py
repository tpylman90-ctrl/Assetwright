"""Import the exact Trimesh-built GLB into Blender 4.5.3 and render six views.
Converts glTF Y-up to Blender Z-up using Blender's normal glTF importer;
original +Z forward becomes Blender -Y forward.
"""
import json
from pathlib import Path
import bpy
from mathutils import Vector

root = Path.cwd()
out = root / "generated/trimesh_v2"
src = out / "scifi_hovercraft_clay.glb"
assert src.is_file() and src.stat().st_size > 10000, "Trimesh output missing"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(src))
parts = sorted((o for o in bpy.data.objects if o.type=="MESH"),key=lambda o:o.name)
assert len(parts)==8, [o.name for o in parts]
expected = ["01_Main_Hull","02_Intakes_And_Louvers","03_Canopy_Glass",
            "04_Canopy_Frame_And_Scoop","05_Side_Manifold","06_Hover_Pods",
            "07_Winglets_And_Fins","08_Rear_Thruster"]
assert all(any(o.name.startswith(name) for o in parts) for name in expected), [o.name for o in parts]
corners=[o.matrix_world @ Vector(c) for o in parts for c in o.bound_box]
mins=[round(min(c[i] for c in corners),4) for i in range(3)]
maxs=[round(max(c[i] for c in corners),4) for i in range(3)]
tris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in parts)
assert tris>1000, tris
assert mins[2]>=-.05 and maxs[2]>1.0, (mins,maxs)
report={
  "source":"tools/blender/inbox/hovercraft_trimesh_v2.py",
  "pipeline":"Trimesh 4.11.1 -> glTF GLB -> Blender 4.5.3 importer -> Blender GLB export + Cycles renders",
  "blender_version":bpy.app.version_string,
  "mesh_groups":len(parts),
  "mesh_names":[o.name for o in parts],
  "triangle_count":tris,
  "bounds_min_blender_xyz":mins,
  "bounds_max_blender_xyz":maxs,
  "user_axes":"Y up, Z forward",
  "blender_axes":"Z up, -Y forward after glTF Y-up conversion",
  "notes":"Original source geometry is unmodified; geometry is intentionally un-beveled and un-subdivided."
}
(out/"geometry_audit.json").write_text(json.dumps(report,indent=2))
print("TRIMESH_TO_BLENDER_IMPORT_OK",json.dumps(report),flush=True)

# Blender-generated GLB built from the imported source.
bpy.ops.object.select_all(action="DESELECT")
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.export_scene.gltf(filepath=str(out/"scifi_hovercraft_blender_v2.glb"),
    export_format="GLB",use_selection=True,export_apply=True,export_yup=True)
assert (out/"scifi_hovercraft_blender_v2.glb").stat().st_size>10000
print("TRIMESH_TO_BLENDER_EXPORT_OK",flush=True)

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=28
scene.cycles.use_denoising=True
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=960
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=False
world=bpy.data.worlds.new("Neutral gray inspection studio")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.22,.24,.26,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.65
scene.world=world

def aim(obj,point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat("-Z","Y").to_euler()
def light(name,loc,power,size):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power
    data.shape="DISK"
    data.size=size
    ob=bpy.data.objects.new(name,data)
    scene.collection.objects.link(ob)
    ob.location=loc
    aim(ob,(0,0,.85))
light("Large softbox", (4,-5,7),1100,5)
light("Fill softbox", (-4,-1,4),850,4)
light("Rear rim light", (-2,5,5),1300,4)
camera_data=bpy.data.cameras.new("Review ortho camera")
camera=bpy.data.objects.new("Review ortho camera",camera_data)
scene.collection.objects.link(camera)
scene.camera=camera
camera_data.type="ORTHO"
aimpoint=(0,-.1,.81)

# Keep the editable project with all eight mesh parts as imported.
blend=out/"scifi_hovercraft_trimesh_v2_master.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
assert blend.stat().st_size>10000
print("TRIMESH_TO_BLENDER_MASTER_OK",flush=True)

views=[
    ("front_3q",(6,-8,5.4),7),
    ("rear_3q",(-6,8,5.4),7),
    ("side",(-9,0,3.1),6.25),
    ("top",(0,0,12),6.7),
    ("front",(0,-11,3),5),
    ("rear",(0,11,3),5),
]
for name,loc,scale in views:
    camera.location=loc
    camera_data.ortho_scale=scale
    aim(camera,aimpoint)
    p=out/("scifi_hovercraft_"+name+".png")
    scene.render.filepath=str(p)
    bpy.ops.render.render(write_still=True)
    assert p.is_file() and p.stat().st_size>15000,name
    print("TRIMESH_TO_BLENDER_PNG_OK",name,p.stat().st_size,flush=True)
print("TRIMESH_TO_BLENDER_ALL_OK",flush=True)
