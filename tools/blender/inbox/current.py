"""Source geometry supplied by the user for the Sci-Fi Hovercraft.
Run through tools/blender/render_inbox.py in real Blender.
Positive Y = front, negative Y = rear. Units = Blender meters.
"""
import bpy
import bmesh
import math
from mathutils import Vector, Euler

# 1. SCENE SETUP
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    bpy.data.meshes.remove(mesh, do_unlink=True)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat, do_unlink=True)

col = bpy.data.collections.new("SciFi_Hovercraft")
bpy.context.scene.collection.children.link(col)
clay_mat = bpy.data.materials.new(name="Clay_Gray")
clay_mat.use_nodes = True
bsdf = clay_mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.52, 0.53, 0.54, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.62

def finalize_object(name, bm, mirror_x=True, bevel_width=0.014, bevel_segs=2):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.data.materials.append(clay_mat)
    if mirror_x:
        mod_m = obj.modifiers.new(name="Mirror", type='MIRROR')
        mod_m.use_axis = (True, False, False)
        mod_m.use_clip = True
        mod_m.merge_threshold = 0.001
    if bevel_width > 0:
        mod_b = obj.modifiers.new(name="Bevel", type='BEVEL')
        mod_b.width = bevel_width
        mod_b.segments = bevel_segs
        mod_b.limit_method = 'ANGLE'
        mod_b.angle_limit = math.radians(28)
    return obj

def add_box(bm, center, size, rot_deg=(0, 0, 0)):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    verts = ret["verts"]
    mat_rot = Euler([math.radians(a) for a in rot_deg], 'XYZ').to_matrix().to_4x4()
    for v in verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
        v.co = mat_rot @ v.co
        v.co += Vector(center)
    return verts

def add_cyl(bm, center, radius1, radius2, depth, segs=24, rot_deg=(0, 0, 0)):
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
        segments=segs, radius1=radius1, radius2=radius2, depth=depth)
    verts = ret["verts"]
    mat_rot = Euler([math.radians(a) for a in rot_deg], 'XYZ').to_matrix().to_4x4()
    for v in verts:
        v.co = mat_rot @ v.co
        v.co += Vector(center)
    return verts

# 2. MAIN ARMORED HULL
stations = [
    (-2.32, 0.34, 0.56, 0.50, 0.30, 0.30, 0.54, 0.80, 0.88),
    (-1.90, 0.56, 0.86, 0.76, 0.48, 0.22, 0.52, 0.88, 0.96),
    (-1.05, 0.64, 0.98, 0.86, 0.56, 0.18, 0.50, 0.92, 1.00),
    ( 0.35, 0.66, 1.02, 0.90, 0.58, 0.18, 0.50, 0.92, 1.00),
    ( 1.35, 0.66, 1.06, 0.94, 0.62, 0.20, 0.50, 0.88, 0.95),
    ( 2.15, 0.54, 0.88, 0.78, 0.52, 0.25, 0.48, 0.74, 0.80),
    ( 2.38, 0.42, 0.68, 0.60, 0.40, 0.28, 0.46, 0.66, 0.72),
]
bm_hull = bmesh.new()
rings = []
for y, xb, xm, xt, xd, zb, zm, zt, zd in stations:
    pts = [(0.0, y, zb), (xb, y, zb), (xm, y, zm),
           (xt, y, zt), (xd, y, zd), (0.0, y, zd)]
    rings.append([bm_hull.verts.new(p) for p in pts])
for i in range(len(rings) - 1):
    r0, r1 = rings[i], rings[i + 1]
    for k in range(len(r0) - 1):
        bm_hull.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
bm_hull.faces.new(list(reversed(rings[0])))
bm_hull.faces.new(rings[-1])
add_box(bm_hull, center=(0.12, 2.34, 0.49), size=(0.24, 0.34, 0.42), rot_deg=(-8, 0, 0))
add_box(bm_hull, center=(0.24, 1.25, 0.94), size=(0.48, 1.55, 0.14), rot_deg=(-4, 0, 0))
finalize_object("01_Main_Hull", bm_hull, mirror_x=True, bevel_width=0.018, bevel_segs=2)

# 3. TWIN FRONT INTAKES, SIDE GILLS & HOOD LOUVERS
bm_vents = bmesh.new()
add_box(bm_vents, center=(0.50, 2.26, 0.48), size=(0.44, 0.28, 0.36), rot_deg=(-6, 0, -10))
for i in range(5):
    z_slat = 0.36 + i * 0.06
    add_box(bm_vents, center=(0.50, 2.34, z_slat), size=(0.36, 0.14, 0.022), rot_deg=(-12, 0, -10))
for i in range(6):
    z_slat = 0.34 + i * 0.055
    add_box(bm_vents, center=(0.86, 1.94, z_slat), size=(0.22, 0.46, 0.02), rot_deg=(-6, 14, -24))
for i in range(4):
    add_box(bm_vents, center=(0.18, 1.28 + i * 0.055, 1.02), size=(0.30, 0.025, 0.03), rot_deg=(-18, 0, 0))
for i in range(3):
    add_box(bm_vents, center=(0.14, 1.72 + i * 0.05, 0.98), size=(0.22, 0.022, 0.025), rot_deg=(-18, 0, 0))
for i in range(6):
    add_box(bm_vents, center=(0.50, 0.65 + i * 0.11, 0.97), size=(0.10, 0.045, 0.05), rot_deg=(0, 25, 0))
finalize_object("02_Intakes_And_Louvers", bm_vents, mirror_x=True, bevel_width=0.005, bevel_segs=1)

# 4. COCKPIT CANOPY & DORSAL INTAKE SCOOP
bm_glass = bmesh.new()
ret_sph = bmesh.ops.create_uvsphere(bm_glass, u_segments=32, v_segments=16, radius=1.0)
for v in list(bm_glass.verts):
    if v.co.z < -0.02:
        bm_glass.verts.remove(v)
    else:
        v.co.z = max(0.0, v.co.z)
        taper = 1.0 - 0.18 * v.co.y
        v.co.x *= 0.52 * taper
        v.co.y *= 0.82
        v.co.z *= 0.46
        v.co += Vector((0.0, -0.10, 0.96))
for v in list(bm_glass.verts):
    if v.co.x < -0.001:
        bm_glass.verts.remove(v)
finalize_object("03_Canopy_Glass", bm_glass, mirror_x=True, bevel_width=0.0, bevel_segs=1)

bm_frame = bmesh.new()
for i in range(14):
    ang0 = math.pi * (i / 14.0)
    ang1 = math.pi * ((i + 1) / 14.0)
    ym = -0.10 + 0.83 * math.cos((ang0 + ang1) * 0.5)
    zm = 0.96 + 0.465 * math.sin((ang0 + ang1) * 0.5)
    pitch = math.degrees(math.atan2(
        0.465 * (math.sin(ang1) - math.sin(ang0)),
        0.83 * (math.cos(ang1) - math.cos(ang0))
    ))
    add_box(bm_frame, center=(0.02, ym, zm), size=(0.04, 0.16, 0.035), rot_deg=(pitch, 0, 0))
for i in range(10):
    ang = (math.pi * 0.5) * (i / 9.0)
    xm = 0.525 * math.cos(ang)
    zm = 0.96 + 0.465 * math.sin(ang)
    roll = -math.degrees(ang)
    add_box(bm_frame, center=(xm, -0.08, zm), size=(0.035, 0.055, 0.11), rot_deg=(0, roll, 0))
add_box(bm_frame, center=(0.52, -0.10, 0.97), size=(0.07, 1.52, 0.06), rot_deg=(0, 0, -4))
add_box(bm_frame, center=(0.18, -1.08, 1.24), size=(0.36, 0.62, 0.34), rot_deg=(-12, 0, 0))
add_box(bm_frame, center=(0.14, -0.78, 1.36), size=(0.28, 0.14, 0.14), rot_deg=(0, 0, 0))
finalize_object("04_Canopy_Frame_And_Scoop", bm_frame, mirror_x=True, bevel_width=0.008, bevel_segs=2)

# 5. SIDE ENGINE MANIFOLD PIPES & LOWER SKIRT VENTS
bm_side = bmesh.new()
add_box(bm_side, center=(0.94, -0.22, 0.58), size=(0.14, 1.06, 0.28), rot_deg=(0, -8, 0))
for i in range(5):
    y_pipe = -0.58 + i * 0.18
    add_cyl(bm_side, center=(0.98, y_pipe, 0.58), radius1=0.072, radius2=0.072, depth=0.24, segs=20, rot_deg=(0, 12, 0))
    add_cyl(bm_side, center=(0.99, y_pipe, 0.58), radius1=0.080, radius2=0.080, depth=0.06, segs=20, rot_deg=(0, 12, 0))
for i in range(8):
    add_box(bm_side, center=(0.86, -0.68 + i * 0.13, 0.34), size=(0.08, 0.055, 0.07), rot_deg=(0, 15, 0))
finalize_object("05_Side_Manifold", bm_side, mirror_x=True, bevel_width=0.006, bevel_segs=2)

# 6. FOUR CORNER HOVER PODS
bm_pods = bmesh.new()
for y_pod in (1.32, -1.38):
    add_box(bm_pods, center=(0.86, y_pod, 0.28), size=(0.44, 0.92, 0.16))
    add_box(bm_pods, center=(0.86, y_pod, 0.17), size=(0.38, 0.78, 0.10))
    add_box(bm_pods, center=(0.86, y_pod, 0.08), size=(0.46, 0.86, 0.11))
finalize_object("06_Hover_Pods", bm_pods, mirror_x=True, bevel_width=0.025, bevel_segs=3)

# 7. FOUR SWEPT WINGLETS & V-TAIL STABILIZERS
bm_wings = bmesh.new()
for y_w, x_w, z_w, span in [(1.18, 1.02, 0.48, 0.64), (-1.42, 0.92, 0.54, 0.60)]:
    add_cyl(bm_wings, center=(x_w, y_w, z_w + 0.02), radius1=0.065, radius2=0.055, depth=0.44, segs=18, rot_deg=(90, 0, 0))
    v0 = bm_wings.verts.new((x_w,        y_w + 0.18, z_w + 0.025))
    v1 = bm_wings.verts.new((x_w,        y_w - 0.20, z_w + 0.025))
    v2 = bm_wings.verts.new((x_w + span, y_w - 0.34, z_w - 0.045))
    v3 = bm_wings.verts.new((x_w + span, y_w - 0.12, z_w - 0.045))
    v4 = bm_wings.verts.new((x_w,        y_w + 0.18, z_w - 0.025))
    v5 = bm_wings.verts.new((x_w,        y_w - 0.20, z_w - 0.025))
    v6 = bm_wings.verts.new((x_w + span, y_w - 0.34, z_w - 0.075))
    v7 = bm_wings.verts.new((x_w + span, y_w - 0.12, z_w - 0.075))
    bm_wings.faces.new((v0, v1, v2, v3))
    bm_wings.faces.new((v7, v6, v5, v4))
    bm_wings.faces.new((v0, v3, v7, v4))
    bm_wings.faces.new((v1, v5, v6, v2))
    bm_wings.faces.new((v3, v2, v6, v7))
fx, fy, fz = 0.44, -1.62, 0.94
fh, cant = 0.68, 0.24
f_verts = [
    bm_wings.verts.new((fx - 0.03, fy + 0.34, fz)),
    bm_wings.verts.new((fx - 0.03, fy - 0.34, fz)),
    bm_wings.verts.new((fx + cant - 0.018, fy - 0.56, fz + fh)),
    bm_wings.verts.new((fx + cant - 0.018, fy - 0.24, fz + fh)),
    bm_wings.verts.new((fx + 0.03, fy + 0.34, fz)),
    bm_wings.verts.new((fx + 0.03, fy - 0.34, fz)),
    bm_wings.verts.new((fx + cant + 0.018, fy - 0.56, fz + fh)),
    bm_wings.verts.new((fx + cant + 0.018, fy - 0.24, fz + fh)),
]
bm_wings.faces.new((f_verts[0], f_verts[1], f_verts[2], f_verts[3]))
bm_wings.faces.new((f_verts[7], f_verts[6], f_verts[5], f_verts[4]))
bm_wings.faces.new((f_verts[0], f_verts[3], f_verts[7], f_verts[4]))
bm_wings.faces.new((f_verts[1], f_verts[5], f_verts[6], f_verts[2]))
bm_wings.faces.new((f_verts[3], f_verts[2], f_verts[6], f_verts[7]))
finalize_object("07_Winglets_And_Fins", bm_wings, mirror_x=True, bevel_width=0.008, bevel_segs=2)

# 8. REAR STEPPED THRUSTER NOZZLE
bm_thruster = bmesh.new()
add_cyl(bm_thruster, center=(0.0, -2.38, 0.58), radius1=0.38, radius2=0.35, depth=0.22, segs=32, rot_deg=(90, 0, 0))
add_cyl(bm_thruster, center=(0.0, -2.52, 0.58), radius1=0.32, radius2=0.29, depth=0.18, segs=32, rot_deg=(90, 0, 0))
add_cyl(bm_thruster, center=(0.0, -2.62, 0.58), radius1=0.22, radius2=0.22, depth=0.08, segs=32, rot_deg=(90, 0, 0))
finalize_object("08_Rear_Thruster", bm_thruster, mirror_x=False, bevel_width=0.01, bevel_segs=2)
