"""Execute code inbox inside Blender, export native geometry and camera views."""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

REPO = Path.cwd()
SOURCE = REPO / "tools/blender/inbox/current.py"
OUTPUT = REPO / "generated/code_to_blender"
OUTPUT.mkdir(parents=True, exist_ok=True)

# Exact user-authored construction code executes inside the real Blender process.
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"),
     {"__name__": "__main__", "__file__": str(SOURCE)})

parts = sorted((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: o.name)
assert len(parts) == 8, "Expected eight original mesh groups, got %s" % len(parts)
assert [o.name[:2] for o in parts] == ["01","02","03","04","05","06","07","08"]
depsgraph = bpy.context.evaluated_depsgraph_get()
bounds = []
tris = 0
for ob in parts:
    evaluated = ob.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
    assert mesh and len(mesh.polygons) > 0, "Empty evaluated mesh: " + ob.name
    tris += sum(len(poly.vertices) - 2 for poly in mesh.polygons)
    bounds.extend(tuple(ob.matrix_world @ v.co) for v in mesh.vertices)
    bpy.data.meshes.remove(mesh)

mins = [round(min(v[i] for v in bounds), 4) for i in range(3)]
maxs = [round(max(v[i] for v in bounds), 4) for i in range(3)]
assert tris > 500 and maxs[0] > 1.0 and mins[0] < -1.0
report = {
    "source": str(SOURCE.relative_to(REPO)),
    "blender_version": bpy.app.version_string,
    "part_count": len(parts),
    "part_names": [o.name for o in parts],
    "evaluated_triangles": tris,
    "bounds_min_xyz": mins,
    "bounds_max_xyz": maxs,
    "front_direction": "+Y",
    "notes": "Original supplied bmesh code; mirror and bevel evaluated in exported GLB."
}
(OUTPUT / "scifi_hovercraft_audit.json").write_text(json.dumps(report, indent=2))
print("CODE_TO_BLENDER_GEOMETRY_OK", json.dumps(report), flush=True)

# Export ONLY user geometry, not cameras/lights. Apply original bevel and mirror.
bpy.ops.object.select_all(action="DESELECT")
for ob in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
glb = OUTPUT / "scifi_hovercraft_blender.glb"
bpy.ops.export_scene.gltf(
    filepath=str(glb),
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_yup=True
)
assert glb.stat().st_size > 10000, "GLB not exported"
print("CODE_TO_BLENDER_GLB_OK", glb.stat().st_size, flush=True)

# Non-destructive studio lights and camera. Geometry and modifiers remain editable.
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = 960
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

world = bpy.data.worlds.new("Studio neutral world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.26,.28,.30,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .65
scene.world = world

def aim(ob, point):
    ob.rotation_euler = (Vector(point)-ob.location).to_track_quat("-Z", "Y").to_euler()

def area(name, at, power, size, target=(0,0,.75)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = power
    d.shape = "DISK"
    d.size = size
    ob = bpy.data.objects.new(name, d)
    scene.collection.objects.link(ob)
    ob.location = at
    aim(ob, target)

area("Key softbox", (3.4, 4.5, 6.0), 1100, 5)
area("Fill softbox", (-4.5, 1.0, 3.5), 800, 4)
area("Rim softbox", (-1.0, -5.0, 5.0), 1300, 4)

camdata = bpy.data.cameras.new("Inspection Orthographic Camera")
camera = bpy.data.objects.new("Inspection Orthographic Camera", camdata)
scene.collection.objects.link(camera)
scene.camera = camera
camdata.type = "ORTHO"
target = (0, -.06, .82)

views = [
    ("front_3q", (6, 8, 5.2), 7.0),
    ("rear_3q", (-6, -8, 5.2), 7.0),
    ("left_side", (-9, 0, 3.0), 6.1),
    ("top", (0, 0, 13), 6.6),
    ("front", (0, 11, 3.0), 4.9),
    ("rear", (0, -11, 3.0), 4.9)
]
# Save editable Blender master with original eight objects and procedural modifiers.
master = OUTPUT / "scifi_hovercraft_master.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(master))
assert master.stat().st_size > 10000
print("CODE_TO_BLENDER_MASTER_OK", master.stat().st_size, flush=True)

for name, position, scale in views:
    camera.location = position
    camdata.ortho_scale = scale
    aim(camera, target)
    png = OUTPUT / ("scifi_hovercraft_" + name + ".png")
    scene.render.filepath = str(png)
    bpy.ops.render.render(write_still=True)
    assert png.stat().st_size > 15000, "Empty render: " + name
    print("CODE_TO_BLENDER_VIEW_OK", name, png.stat().st_size, flush=True)
print("CODE_TO_BLENDER_ALL_OK", flush=True)
