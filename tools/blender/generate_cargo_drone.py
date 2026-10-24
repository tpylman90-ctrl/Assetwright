"""Build a small, game-ready sci-fi cargo drone demo with Blender primitives.

Run:
  blender --background --factory-startup --python tools/blender/generate_cargo_drone.py -- --output-dir generated
"""
import argparse
import os
import sys

import bpy
from mathutils import Vector


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="generated")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def material(name, color, metallic=0.0, roughness=0.55, emission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        color_socket = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        strength_socket = bsdf.inputs.get("Emission Strength")
        if color_socket is not None:
            color_socket.default_value = (*color, 1.0)
        if strength_socket is not None:
            strength_socket.default_value = emission
    return mat


def bevelled_box(name, location, dimensions, mat, bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Soft machined edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def cylinder(name, location, radius, depth, mat, rotation=(0, 0, 0), vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth,
        location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def point_camera(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def build_scene(output_dir):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    alloy = material("Worn graphite alloy", (0.16, 0.22, 0.26), 0.72, 0.34)
    edge = material("Brushed titanium", (0.42, 0.53, 0.56), 0.78, 0.28)
    dark = material("Engine ceramic", (0.045, 0.075, 0.09), 0.45, 0.42)
    teal = material("Teal status light", (0.02, 0.82, 0.67), 0.18, 0.22, 2.0)
    orange = material("Safety orange", (1.0, 0.29, 0.055), 0.25, 0.38)

    # Main armored cargo shell: nose points toward -Y.
    bevelled_box("Cargo hull", (0, 0, 1.65), (1.48, 2.15, 0.72), alloy, 0.16)
    bevelled_box("Forward armored nose", (0, -0.92, 1.72), (1.22, 0.54, 0.62), edge, 0.12)
    bevelled_box("Top cargo hatch", (0, 0.18, 2.04), (0.82, 0.96, 0.12), edge, 0.045)
    bevelled_box("Hatch inset", (0, 0.18, 2.11), (0.56, 0.68, 0.025), dark, 0.015)

    # Twin side engines and their short reinforced pylons.
    for side, label in ((-1, "Port"), (1, "Starboard")):
        x = side * 1.17
        bevelled_box(label + " engine pylon", (side * 0.88, 0.02, 1.55), (0.72, 0.32, 0.3), edge, 0.07)
        cylinder(label + " engine nacelle", (x, 0.0, 1.58), 0.34, 1.22, dark, rotation=(1.5708, 0, 0))
        cylinder(label + " intake rim", (x, -0.625, 1.58), 0.29, 0.08, edge, rotation=(1.5708, 0, 0))
        cylinder(label + " intake core", (x, -0.674, 1.58), 0.19, 0.025, dark, rotation=(1.5708, 0, 0))
        cylinder(label + " rear exhaust", (x, 0.625, 1.58), 0.25, 0.07, edge, rotation=(1.5708, 0, 0))
        bevelled_box(label + " teal marker", (side * 1.17, -0.05, 1.94), (0.16, 0.32, 0.06), teal, 0.025)

    # Four simple landing legs, sized for a game prop silhouette.
    for side in (-1, 1):
        for fore in (-1, 1):
            x, y = side * 0.52, fore * 0.68
            leg = bevelled_box("Landing strut", (x, y, 0.88), (0.11, 0.12, 0.76), edge, 0.035)
            leg.rotation_euler[1] = side * -0.16
            bevelled_box("Landing foot", (x + side * 0.10, y, 0.49), (0.36, 0.24, 0.11), dark, 0.035)

    # Recessed side vents and small safety markings.
    for side in (-1, 1):
        for i in range(4):
            bevelled_box("Hull vent", (side * 0.752, 0.14 + i * 0.14, 1.66), (0.025, 0.075, 0.32), dark, 0.008)
    for x in (-0.43, 0.43):
        bevelled_box("Safety stripe", (x, -0.32, 2.12), (0.09, 0.42, 0.025), orange, 0.008)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.10, location=(side * 0.52, -0.96, 1.73))
        lamp = bpy.context.object
        lamp.name = "Forward teal running light"
        lamp.scale = (1.0, 0.55, 0.65)
        lamp.data.materials.append(teal)

    # Neutral studio floor and soft lighting are for the preview render only.
    floor_mat = material("Preview floor", (0.035, 0.055, 0.07), 0.15, 0.82)
    bevelled_box("Preview floor", (0, 0, 0.23), (200, 200, 0.2), floor_mat, 0)

    scene = bpy.context.scene
    try:\n        scene.render.engine = "BLENDER_EEVEE_NEXT"\n    except TypeError:\n        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.035, 0.05)

    bpy.ops.object.light_add(type="AREA", location=(3.8, -4.2, 6.5))
    key = bpy.context.object
    key.name = "Large soft key"
    key.data.energy = 850
    key.data.shape = "DISK"
    key.data.size = 5.0
    point_camera(key, (0, 0, 1.4))

    bpy.ops.object.light_add(type="AREA", location=(-4.0, 1.2, 3.8))
    fill = bpy.context.object
    fill.name = "Cool rim light"
    fill.data.energy = 650
    fill.data.color = (0.25, 0.72, 1.0)
    fill.data.size = 3.5
    point_camera(fill, (0, 0, 1.4))

    bpy.ops.object.camera_add(location=(4.3, -6.0, 3.8))
    camera = bpy.context.object
    camera.name = "Preview camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 5.8
    point_camera(camera, (0, 0, 1.3))
    scene.camera = camera

    os.makedirs(output_dir, exist_ok=True)
    preview_path = os.path.abspath(os.path.join(output_dir, "cargo_drone_preview.png"))
    glb_path = os.path.abspath(os.path.join(output_dir, "cargo_drone.glb"))
    scene.render.filepath = preview_path
    bpy.ops.render.render(write_still=True)

    # Keep only asset geometry in the exported GLB.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in scene.objects:
        if obj.type == "MESH" and obj.name != "Preview floor":
            obj.select_set(True)
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB")

    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) < 1024:
        raise RuntimeError("GLB export did not produce a valid sized file")
    print("Created {} ({} bytes) and {}".format(glb_path, os.path.getsize(glb_path), preview_path))


if __name__ == "__main__":
    args = arguments()
    build_scene(args.output_dir)
