"""Build a small, game-ready sci-fi cargo drone demo with Blender primitives.

Run:
  blender --background --factory-startup --python tools/blender/generate_cargo_drone.py -- --output-dir generated
"""
import argparse
import math
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


def cylinder(name, location, radius, depth, mat, rotation=(0, 0, 0), vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth,
        location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj




def torus(name, location, major_radius, minor_radius, mat, rotation=(0, 0, 0), major_segments=32, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=location,
        rotation=rotation,
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def fastener(name, location, mat, rotation=(0, 0, 0), radius=0.028, depth=0.018):
    obj = cylinder(name, location, radius, depth, mat, rotation=rotation, vertices=16)
    return obj


def lofted_hull(name, sections, mat, bevel=0.035):
    """Create a tapered hard-surface body from chamfered cross sections.

    Each section is (y, half_width, half_height, center_z). The eight-sided
    profile keeps the hull angular while a small multi-segment bevel softens
    the edges for a polished game-asset finish.
    """
    vertices = []
    faces = []
    chamfer_ratio = 0.24
    for y, half_width, half_height, center_z in sections:
        cut = min(half_width, half_height) * chamfer_ratio
        ring = [
            (-half_width + cut, -half_height),
            (half_width - cut, -half_height),
            (half_width, -half_height + cut),
            (half_width, half_height - cut),
            (half_width - cut, half_height),
            (-half_width + cut, half_height),
            (-half_width, half_height - cut),
            (-half_width, -half_height + cut),
        ]
        vertices.extend((x, y, center_z + z) for x, z in ring)

    section_count = len(sections)
    side_count = 8
    faces.append(tuple(range(side_count)))
    faces.append(tuple(reversed(range((section_count - 1) * side_count, section_count * side_count))))
    for section in range(section_count - 1):
        for edge_index in range(side_count):
            a = section * side_count + edge_index
            b = section * side_count + (edge_index + 1) % side_count
            c = (section + 1) * side_count + (edge_index + 1) % side_count
            d = (section + 1) * side_count + edge_index
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new(name + " precision mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    edge_bevel = obj.modifiers.new("Three segment edge fillets", "BEVEL")
    edge_bevel.width = bevel
    edge_bevel.segments = 3
    obj.modifiers.new("Weighted machined normals", "WEIGHTED_NORMAL")
    return obj


def point_camera(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def build_scene(output_dir):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    alloy = material("Worn graphite alloy", (0.22, 0.29, 0.33), 0.72, 0.34)
    edge = material("Brushed titanium", (0.56, 0.66, 0.68), 0.78, 0.28)
    dark = material("Engine ceramic", (0.065, 0.095, 0.11), 0.45, 0.42)
    teal = material("Teal status light", (0.02, 0.82, 0.67), 0.18, 0.22, 2.0)
    orange = material("Safety orange", (1.0, 0.34, 0.075), 0.25, 0.38)
    panel = material("Deep teal armor panels", (0.075, 0.19, 0.21), 0.62, 0.31)
    warm_metal = material("Warm titanium hardware", (0.48, 0.29, 0.14), 0.74, 0.3)

    # Tapered, chamfered cargo shell: nose points toward -Y.
    lofted_hull("Cargo hull", [
        (-1.05, 0.56, 0.23, 1.65),
        (-0.82, 0.70, 0.34, 1.65),
        (0.62, 0.72, 0.34, 1.65),
        (1.05, 0.57, 0.24, 1.65),
    ], alloy, 0.035)
    lofted_hull("Forward armored cowl", [
        (-1.24, 0.40, 0.18, 1.72),
        (-1.03, 0.56, 0.28, 1.72),
        (-0.72, 0.58, 0.29, 1.72),
    ], edge, 0.028)
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


    # Layered armor and cargo-service hardware lift the hull beyond a plain blockout.
    for side, label in ((-1, "Port"), (1, "Starboard")):
        bevelled_box(label + " side armor plate", (side * 0.765, 0.12, 1.69), (0.075, 0.74, 0.43), panel, 0.045)
        bevelled_box(label + " armor inset", (side * 0.811, 0.12, 1.69), (0.018, 0.44, 0.22), alloy, 0.025)
        for y in (-0.18, 0.42):
            for z in (1.52, 1.86):
                fastener(label + " armor bolt", (side * 0.826, y, z), warm_metal, rotation=(0, 1.5708, 0), radius=0.026, depth=0.018)

    # Replace the flat nose with a layered sensor face and protected optical array.
    bevelled_box("Nose sensor bezel", (0, -1.215, 1.72), (0.92, 0.065, 0.39), dark, 0.085)
    bevelled_box("Nose sensor faceplate", (0, -1.255, 1.72), (0.78, 0.035, 0.27), edge, 0.055)
    for x, radius in ((-0.24, 0.075), (0, 0.105), (0.24, 0.075)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=(x, -1.28, 1.72))
        optic = bpy.context.object
        optic.name = "Optical navigation sensor"
        optic.scale = (1.0, 0.35, 1.0)
        optic.data.materials.append(teal if x == 0 else dark)
    for side in (-1, 1):
        bevelled_box("Nose bumper", (side * 0.49, -1.18, 1.52), (0.12, 0.12, 0.13), orange, 0.035)

    # Fine perimeter trim, locking dogs, and fasteners around the cargo hatch.
    for x in (-0.47, 0.47):
        bevelled_box("Hatch side rail", (x, 0.18, 2.09), (0.055, 1.07, 0.07), edge, 0.025)
    for y in (-0.38, 0.74):
        bevelled_box("Hatch end rail", (0, y, 2.09), (0.96, 0.055, 0.07), edge, 0.025)
    for x in (-0.48, 0.48):
        for y in (-0.33, 0.67):
            fastener("Hatch captive fastener", (x, y, 2.125), warm_metal, radius=0.024, depth=0.018)
    for x in (-0.52, 0.52):
        bevelled_box("Dorsal service panel", (x, 0.12, 2.035), (0.28, 0.60, 0.045), panel, 0.035)
        for y in (-0.10, 0.34):
            fastener("Service panel screw", (x, y, 2.065), edge, radius=0.018, depth=0.014)

    # Engine intakes gain a machined rim, recessed fan, and central hub.
    for side, label in ((-1, "Port"), (1, "Starboard")):
        x, y, z = side * 1.17, -0.685, 1.58
        torus(label + " intake machined lip", (x, y, z), 0.255, 0.035, warm_metal, rotation=(1.5708, 0, 0), major_segments=40, minor_segments=10)
        cylinder(label + " intake hub", (x, y - 0.012, z), 0.075, 0.045, edge, rotation=(1.5708, 0, 0), vertices=24)
        for blade_index in range(8):
            angle = blade_index * 0.785398
            blade = bevelled_box(
                label + " intake rotor blade",
                (x + 0.145 * math.cos(angle), y - 0.027, z + 0.145 * math.sin(angle)),
                (0.17, 0.025, 0.035), edge, 0.012
            )
            blade.rotation_euler[1] = -angle
        # Rear nozzle rings and recessed hot section.
        rear_y = 0.69
        torus(label + " exhaust nozzle lip", (x, rear_y, z), 0.22, 0.035, edge, rotation=(1.5708, 0, 0), major_segments=40, minor_segments=10)
        cylinder(label + " exhaust throat", (x, rear_y + 0.018, z), 0.16, 0.045, dark, rotation=(1.5708, 0, 0), vertices=32)

    # Under-belly cargo cradle, guide rails, and tie-down points.
    bevelled_box("Underslung cargo pod", (0, 0.22, 1.14), (0.78, 0.96, 0.25), panel, 0.085)
    bevelled_box("Cargo pod lower armor", (0, 0.22, 1.005), (0.64, 0.76, 0.075), alloy, 0.035)
    for side in (-1, 1):
        bevelled_box("Cargo cradle rail", (side * 0.48, 0.22, 1.25), (0.075, 1.10, 0.095), edge, 0.025)
        for y in (-0.12, 0.55):
            torus("Cargo tie-down loop", (side * 0.48, y, 1.31), 0.055, 0.012, warm_metal, rotation=(1.5708, 0, 0), major_segments=20, minor_segments=6)

    # Landing gear receives visible knee hubs, hydraulic sleeves, and treaded feet.
    for side in (-1, 1):
        for fore in (-1, 1):
            x, y = side * 0.52, fore * 0.68
            cylinder("Landing gear pivot", (x + side * -0.06, y, 1.10), 0.105, 0.16, warm_metal, rotation=(0, 1.5708, 0), vertices=24)
            bevelled_box("Landing piston sleeve", (x + side * 0.06, y, 0.91), (0.065, 0.07, 0.42), dark, 0.025)
            foot_x = x + side * 0.10
            for stripe in (-0.075, 0, 0.075):
                bevelled_box("Landing foot tread", (foot_x + stripe, y - 0.01, 0.55), (0.035, 0.18, 0.018), edge, 0.008)

    # Add small hull access covers and maintenance lights to break up broad surfaces.
    for side in (-1, 1):
        for y in (-0.55, 0.58):
            bevelled_box("Side access cover", (side * 0.77, y, 1.38), (0.035, 0.30, 0.12), dark, 0.025)
        for y in (-0.70, 0.70):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.055, location=(side * 0.82, y, 1.96))
            lamp = bpy.context.object
            lamp.name = "Hull maintenance indicator"
            lamp.scale = (0.5, 1.0, 0.6)
            lamp.data.materials.append(teal)

    # Neutral studio floor and soft lighting are for the preview render only.
    floor_mat = material("Preview floor", (0.035, 0.055, 0.07), 0.15, 0.82)
    bevelled_box("Preview floor", (0, 0, 0.23), (200, 200, 0.2), floor_mat, 0)

    scene = bpy.context.scene
    # Workbench renders reliably on a headless CPU-only GitHub runner.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.cavity_ridge_factor = 1.25
    scene.display.shading.cavity_valley_factor = 0.8
    scene.display.shading.show_shadows = True
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.07, 0.09, 0.12)

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
