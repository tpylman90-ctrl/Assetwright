"""Build a small, game-ready sci-fi cargo drone demo with Blender primitives.

Run:
  blender --background --factory-startup --python tools/blender/generate_cargo_drone.py -- --output-dir generated
"""
import argparse
import math
import os
import random
from array import array
import sys

import bpy
from mathutils import Vector


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="generated")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def scratched_albedo(name, color, size=512):
    """Create a small packed game texture with subtle metal grain and paint wear."""
    rng = random.Random(name)
    wear = bytearray(size * size)

    # Fine directional scratches and scattered chips; the restrained mask keeps
    # the finish readable at mobile viewing sizes.
    for _ in range(180):
        x = rng.randrange(size)
        y = rng.randrange(size)
        length = rng.randrange(5, 34)
        dx, dy = rng.choice(((1, 0), (1, 1), (1, -1), (0, 1)))
        for step in range(length):
            px = x + dx * step
            py = y + dy * step
            if 0 <= px < size and 0 <= py < size:
                wear[py * size + px] = 1
    for _ in range(900):
        x = rng.randrange(size)
        y = rng.randrange(size)
        wear[y * size + x] = 2

    pixels = array("f")
    for y in range(size):
        broad = 0.96 + 0.018 * math.sin(y * 0.12)
        for x in range(size):
            idx = y * size + x
            shade = broad + rng.uniform(-0.055, 0.045)
            if wear[idx] == 1:
                shade *= 0.68
            elif wear[idx] == 2:
                shade *= 1.12
            pixels.extend((
                min(1.0, max(0.0, color[0] * shade)),
                min(1.0, max(0.0, color[1] * shade)),
                min(1.0, max(0.0, color[2] * shade)),
                1.0,
            ))

    image = bpy.data.images.new(name + " Albedo", width=size, height=size, alpha=False)
    image.pixels.foreach_set(pixels)
    image.pack()
    return image


def material(name, color, metallic=0.0, roughness=0.55, emission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness

    albedo = nodes.new("ShaderNodeTexImage")
    albedo.name = name + " scratched albedo"
    albedo.image = scratched_albedo(name, color)
    albedo.interpolation = "Linear"
    links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])

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
            faces.append((a, d, c, b))

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


def unwrap_model_meshes(objects):
    """Give every exported mesh UVs so packed image materials survive GLB export."""
    for obj in objects:
        if obj.type != "MESH":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(island_margin=0.025)
        bpy.ops.object.mode_set(mode="OBJECT")


def point_camera(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def build_scene(output_dir):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    alloy = material("Worn graphite alloy", (0.30, 0.32, 0.34), 0.72, 0.34)
    edge = material("Brushed titanium", (0.60, 0.63, 0.65), 0.78, 0.28)
    dark = material("Engine ceramic", (0.065, 0.095, 0.11), 0.45, 0.42)
    teal = material("Teal status light", (0.02, 0.82, 0.67), 0.18, 0.22, 2.0)
    orange = material("Safety orange", (1.0, 0.34, 0.075), 0.25, 0.38)
    panel = material("Deep teal armor panels", (0.12, 0.16, 0.18), 0.62, 0.31)
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

    # Twin armored engine pods with recessed intake grilles and visible mounts.
    for side, label in ((-1, "Port"), (1, "Starboard")):
        x = side * 1.36
        bevelled_box(label + " engine mount pylon", (side * 0.91, 0.02, 1.56), (0.72, 0.38, 0.34), edge, 0.08)
        cylinder(label + " articulated drive collar", (side * 1.03, 0.02, 1.59), 0.22, 0.24, dark, rotation=(0, 1.5708, 0), vertices=32)
        cylinder(label + " outer drive ring", (side * 1.15, 0.02, 1.59), 0.24, 0.08, warm_metal, rotation=(0, 1.5708, 0), vertices=32)
        bevelled_box(label + " armored engine pod", (x, 0.0, 1.62), (0.70, 1.34, 0.78), alloy, 0.12)
        bevelled_box(label + " intake bezel", (x, -0.68, 1.62), (0.48, 0.055, 0.55), edge, 0.06)
        bevelled_box(label + " recessed intake", (x, -0.716, 1.62), (0.38, 0.03, 0.44), dark, 0.045)
        for blade_index in range(6):
            z = 1.44 + blade_index * 0.072
            bevelled_box(label + " intake louver", (x, -0.738, z), (0.32, 0.035, 0.026), edge, 0.009)
        bevelled_box(label + " top warning stripe", (x, -0.30, 2.015), (0.69, 0.095, 0.025), orange, 0.012)
        bevelled_box(label + " outer service panel", (side * 1.715, 0.10, 1.62), (0.045, 0.72, 0.50), panel, 0.055)
        for y in (-0.21, 0.41):
            for z in (1.43, 1.81):
                fastener(label + " nacelle bolt", (side * 1.747, y, z), warm_metal, rotation=(0, 1.5708, 0), radius=0.024, depth=0.018)
        for vent_index in range(4):
            bevelled_box(label + " side exhaust vent", (side * 1.75, -0.02 + vent_index * 0.10, 1.59), (0.025, 0.055, 0.30), dark, 0.009)
        cylinder(label + " rear exhaust throat", (x, 0.68, 1.62), 0.235, 0.13, dark, rotation=(1.5708, 0, 0), vertices=40)
        cylinder(label + " rear exhaust core", (x, 0.755, 1.62), 0.145, 0.045, warm_metal, rotation=(1.5708, 0, 0), vertices=32)
        bevelled_box(label + " teal status marker", (side * 1.36, -0.12, 2.055), (0.13, 0.27, 0.045), teal, 0.02)

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

    # Front armor layout: bolted central plate, vent stacks, and cyan running lights.
    bevelled_box("Nose sensor bezel", (0, -1.235, 1.72), (1.02, 0.065, 0.46), dark, 0.065)
    bevelled_box("Nose armor faceplate", (0, -1.278, 1.72), (0.88, 0.035, 0.36), edge, 0.045)
    bevelled_box("Central service hatch", (0, -1.302, 1.72), (0.55, 0.025, 0.30), alloy, 0.025)
    bevelled_box("Service hatch inset", (0, -1.319, 1.72), (0.38, 0.012, 0.19), panel, 0.012)
    bevelled_box("Identification plate", (0, -1.329, 1.84), (0.26, 0.012, 0.045), dark, 0.008)
    for x in (-0.52, 0.52):
        bevelled_box("Vertical teal running light", (x, -1.29, 1.73), (0.045, 0.025, 0.23), teal, 0.018)
        vent_x = x * 0.72
        bevelled_box("Forward vent recess", (vent_x, -1.285, 1.66), (0.105, 0.025, 0.28), dark, 0.018)
        for index in range(4):
            bevelled_box("Forward vent slat", (vent_x, -1.303, 1.56 + index * 0.065), (0.073, 0.018, 0.018), edge, 0.006)
    for x in (-0.40, 0.40):
        for z in (1.57, 1.87):
            fastener("Nose plate bolt", (x, -1.31, z), warm_metal, rotation=(1.5708, 0, 0), radius=0.021, depth=0.015)


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

    # Raised exhaust rings and recessed center nozzles on the pod backs.
    for side, label in ((-1, "Port"), (1, "Starboard")):
        x = side * 1.36
        torus(label + " exhaust retaining ring", (x, 0.77, 1.62), 0.205, 0.028, edge, rotation=(1.5708, 0, 0), major_segments=40, minor_segments=10)
        torus(label + " exhaust copper seal", (x, 0.79, 1.62), 0.158, 0.012, orange, rotation=(1.5708, 0, 0), major_segments=36, minor_segments=8)


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
            cylinder("Landing gear pivot", (x + side * -0.06, y, 1.10), 0.075, 0.13, edge, rotation=(0, 1.5708, 0), vertices=32)
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
    floor_mat = material("Preview floor", (0.38, 0.39, 0.40), 0.08, 0.92)
    bevelled_box("Preview floor", (0, 0, 0.23), (200, 200, 0.2), floor_mat, 0)

    scene = bpy.context.scene
    # Workbench renders reliably on a headless CPU-only GitHub runner.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.cavity_ridge_factor = 1.25
    scene.display.shading.cavity_valley_factor = 1.0
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.38, 0.39, 0.40)
    scene.display.shading.studiolight_intensity = 1.25
    scene.display.shading.shadow_intensity = 0.35
    scene.display.shading.show_specular_highlight = True
    scene.display.shading.show_shadows = True
    scene.display.shading.color_type = "TEXTURE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
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
    camera.data.ortho_scale = 7.0
    point_camera(camera, (0, 0, 1.3))
    scene.camera = camera

    os.makedirs(output_dir, exist_ok=True)
    preview_path = os.path.abspath(os.path.join(output_dir, "cargo_drone_preview.png"))
    glb_path = os.path.abspath(os.path.join(output_dir, "cargo_drone.glb"))
    os.makedirs(output_dir, exist_ok=True)
    unwrap_model_meshes([obj for obj in scene.objects if obj.type == "MESH"])

    # Match the reference's useful front, side, rear, and top inspection views.
    tile_width, tile_height = 768, 512
    scene.render.resolution_x = tile_width
    scene.render.resolution_y = tile_height
    scene.render.resolution_percentage = 100
    view_specs = [
        ("front", (0, -10, 2.7), (0, 0, 1.25)),
        ("side", (10, 0, 2.7), (0, 0, 1.25)),
        ("rear", (0, 10, 2.7), (0, 0, 1.25)),
        ("top", (0, 0, 10), (0, 0, 1.25)),
    ]
    view_paths = []
    view_images = []
    for view_name, location, target in view_specs:
        camera.location = location
        camera.data.ortho_scale = 4.8
        point_camera(camera, target)
        scene.camera = camera
        view_path = os.path.abspath(os.path.join(output_dir, "cargo_drone_" + view_name + ".png"))
        scene.render.filepath = view_path
        bpy.ops.render.render(write_still=True)
        view_paths.append(view_path)
        view_images.append(bpy.data.images.load(view_path, check_existing=False))

    sheet = bpy.data.images.new(
        "Cargo drone four-view inspection sheet",
        width=tile_width * 2,
        height=tile_height * 2,
        alpha=False
    )
    sheet_pixels = array("f", [0.0]) * (tile_width * tile_height * 4 * 4)
    placements = ((0, tile_height), (tile_width, tile_height), (0, 0), (tile_width, 0))
    for source_image, (tile_x, tile_y) in zip(view_images, placements):
        source_pixels = array("f", [0.0]) * (tile_width * tile_height * 4)
        source_image.pixels.foreach_get(source_pixels)
        for row in range(tile_height):
            src_start = row * tile_width * 4
            dst_start = ((tile_y + row) * tile_width * 2 + tile_x) * 4
            sheet_pixels[dst_start:dst_start + tile_width * 4] = source_pixels[src_start:src_start + tile_width * 4]
    sheet.pixels.foreach_set(sheet_pixels)
    sheet.filepath_raw = preview_path
    sheet.file_format = "PNG"
    sheet.save()
    for source_image, view_path in zip(view_images, view_paths):
        bpy.data.images.remove(source_image)
        os.remove(view_path)
    scene.render.resolution_x = tile_width * 2
    scene.render.resolution_y = tile_height * 2
    scene.render.resolution_percentage = 100

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
