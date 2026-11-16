"""Sci-fi hovercraft — user-supplied Trimesh V2 source.
Y up, Z forward. This is intentionally a direct reproduction of the user's mesh
generator; export is performed in its working directory.
"""
import numpy as np
import trimesh
from trimesh.transformations import euler_matrix, translation_matrix


def xform(mesh, center=(0, 0, 0), rot_deg=(0, 0, 0)):
    rx, ry, rz = np.radians(rot_deg)
    mat = translation_matrix(center) @ euler_matrix(rx, ry, rz, axes="sxyz")
    mesh.apply_transform(mat)
    return mesh


def make_box(center, size, rot_deg=(0, 0, 0)):
    m = trimesh.creation.box(extents=size)
    return xform(m, center, rot_deg)


def make_cyl(center, radius, height, sections=24, rot_deg=(0, 0, 0)):
    m = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    return xform(m, center, rot_deg)


def make_frustum(center, r_back, r_front, length, sections=32):
    angles = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    cos_a, sin_a = np.cos(angles), np.sin(angles)
    z0, z1 = -length * 0.5, length * 0.5
    v_back = np.column_stack([r_back * cos_a, r_back * sin_a, np.full(sections, z0)])
    v_front = np.column_stack([r_front * cos_a, r_front * sin_a, np.full(sections, z1)])
    c_back = np.array([[0.0, 0.0, z0]])
    c_front = np.array([[0.0, 0.0, z1]])
    verts = np.vstack([v_back, v_front, c_back, c_front])
    idx_cb = 2 * sections
    idx_cf = 2 * sections + 1
    faces = []
    for i in range(sections):
        ni = (i + 1) % sections
        faces.append([i, ni, sections + ni])
        faces.append([i, sections + ni, sections + i])
        faces.append([idx_cb, ni, i])
        faces.append([idx_cf, sections + i, sections + ni])
    m = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    m.fix_normals()
    return xform(m, center)


def make_wedge_wing(pts_top, pts_bot):
    verts = np.array(pts_top + pts_bot, dtype=float)
    faces = np.array([
        [0, 1, 2], [0, 2, 3],
        [4, 6, 5], [4, 7, 6],
        [0, 4, 5], [0, 5, 1],
        [1, 5, 6], [1, 6, 2],
        [2, 6, 7], [2, 7, 3],
        [3, 7, 4], [3, 4, 0],
    ])
    m = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    m.fix_normals()
    return m


def mirror_and_merge(parts):
    combined = trimesh.util.concatenate(parts)
    mir_verts = combined.vertices.copy()
    mir_verts[:, 0] *= -1.0
    mir_faces = combined.faces[:, ::-1]
    mirrored = trimesh.Trimesh(vertices=mir_verts, faces=mir_faces, process=False)
    full = trimesh.util.concatenate([combined, mirrored])
    full.merge_vertices()
    full.fix_normals()
    return full


# 1. MAIN ARMORED HULL WITH TRUE RECESSED SIDE BAY (+Y UP, +Z FWD)
stations = [
    (-2.34,  0.34,  0.48,  0.54,  0.56,  0.50,  0.30,  0.30,  0.44,  0.46,   0.68,   0.70,  0.80,  0.88),
    (-1.90,  0.56,  0.76,  0.84,  0.86,  0.76,  0.48,  0.22,  0.42,  0.44,   0.70,   0.72,  0.88,  0.96),
    (-0.86,  0.64,  0.92,  0.98,  0.98,  0.86,  0.56,  0.18,  0.42,  0.44,   0.70,   0.72,  0.92,  1.00),
    (-0.80,  0.64,  0.92,  0.77,  0.98,  0.86,  0.56,  0.18,  0.42,  0.44,   0.70,   0.72,  0.92,  1.00),
    ( 0.40,  0.66,  0.94,  0.77,  1.00,  0.90,  0.58,  0.18,  0.42,  0.44,   0.70,   0.72,  0.92,  1.00),
    ( 0.46,  0.66,  0.94,  1.02,  1.02,  0.90,  0.58,  0.18,  0.42,  0.44,   0.70,   0.72,  0.92,  1.00),
    ( 1.35,  0.66,  0.96,  1.05,  1.04,  0.94,  0.62,  0.20,  0.42,  0.44,   0.68,   0.70,  0.88,  0.95),
    ( 2.12,  0.54,  0.78,  0.84,  0.84,  0.76,  0.50,  0.25,  0.40,  0.42,   0.60,   0.62,  0.74,  0.80),
    ( 2.34,  0.40,  0.58,  0.62,  0.62,  0.56,  0.38,  0.28,  0.38,  0.40,   0.54,   0.56,  0.66,  0.72),
]

rings = []
for st in stations:
    z, xb, xs, xbay, xsh, xt, xd, yb, ys, y0, y1, ysh, yt, yd = st
    rings.append([
        [0.0,  yb,  z],
        [xb,   yb,  z],
        [xs,   ys,  z],
        [xbay, y0,  z],
        [xbay, y1,  z],
        [xsh,  ysh, z],
        [xt,   yt,  z],
        [xd,   yd,  z],
        [0.0,  yd,  z],
    ])

rings = np.array(rings, dtype=float)
n_rings, n_pts, _ = rings.shape
hull_verts = rings.reshape(-1, 3)
hull_faces = []
for r in range(n_rings - 1):
    for p in range(n_pts - 1):
        i00 = r * n_pts + p
        i01 = r * n_pts + (p + 1)
        i10 = (r + 1) * n_pts + p
        i11 = (r + 1) * n_pts + (p + 1)
        hull_faces.append([i00, i01, i11])
        hull_faces.append([i00, i11, i10])

for p in range(1, n_pts - 1):
    hull_faces.append([0, p + 1, p])
    base = (n_rings - 1) * n_pts
    hull_faces.append([base, base + p, base + p + 1])

hull_loft = trimesh.Trimesh(vertices=hull_verts, faces=np.array(hull_faces), process=False)
hull_loft.fix_normals()

hull_parts = [
    hull_loft,
    make_box(center=(0.11, 0.49, 2.28), size=(0.22, 0.40, 0.34), rot_deg=(6, 0, 0)),
    make_box(center=(0.24, 0.94, 1.25), size=(0.48, 0.14, 1.50), rot_deg=(4, 0, 0)),
    make_box(center=(0.46, 0.65, 2.24), size=(0.42, 0.07, 0.32), rot_deg=(8, -10, 0)),
    make_box(center=(0.46, 0.31, 2.24), size=(0.42, 0.07, 0.32), rot_deg=(-4, -10, 0)),
    make_box(center=(0.66, 0.48, 2.22), size=(0.08, 0.38, 0.34), rot_deg=(0, -10, 0)),
]
mesh_01_hull = mirror_and_merge(hull_parts)

# 2. TWIN FRONT INTAKES AND CHEEK LOUVERS
vent_parts = [make_box(center=(0.45, 0.48, 2.16), size=(0.36, 0.28, 0.06), rot_deg=(4, -10, 0))]
for i in range(5):
    y_slat = 0.36 + i * 0.058
    vent_parts.append(make_box(center=(0.45, y_slat, 2.26), size=(0.34, 0.022, 0.12), rot_deg=(12, -10, 0)))
for i in range(6):
    y_slat = 0.34 + i * 0.052
    vent_parts.append(make_box(center=(0.76, y_slat, 1.88), size=(0.14, 0.020, 0.40), rot_deg=(6, -24, -12)))
for i in range(4):
    vent_parts.append(make_box(center=(0.18, 1.02, 1.28 + i * 0.055), size=(0.30, 0.030, 0.025), rot_deg=(18, 0, 0)))
for i in range(3):
    vent_parts.append(make_box(center=(0.14, 0.98, 1.72 + i * 0.050), size=(0.22, 0.025, 0.022), rot_deg=(18, 0, 0)))
for i in range(6):
    vent_parts.append(make_box(center=(0.50, 0.97, 0.65 + i * 0.110), size=(0.10, 0.045, 0.045), rot_deg=(0, 0, -22)))
mesh_02_vents = mirror_and_merge(vent_parts)

# 3. COCKPIT CANOPY GLASS
sph = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
v = sph.vertices.copy()
v[:, 1] = np.maximum(0.0, v[:, 1])
taper = 1.0 - 0.18 * v[:, 2]
v[:, 0] *= 0.50 * taper
v[:, 1] *= 0.45
v[:, 2] *= 0.80
v += np.array([0.0, 0.96, -0.06])
sph.vertices = v
c = sph.triangles_center
keep = (c[:, 1] > 0.962) & (c[:, 0] >= -1e-4)
canopy_half = sph.submesh([keep], append=True)
mesh_03_canopy = mirror_and_merge([canopy_half])

# 4. CANOPY STRUCTURAL FRAME & DORSAL SCOOP
frame_parts = [
    make_box(center=(0.50, 0.97, -0.06), size=(0.065, 0.055, 1.48), rot_deg=(0, 4, 0)),
    make_box(center=(0.18, 1.23, -1.04), size=(0.36, 0.34, 0.62), rot_deg=(12, 0, 0)),
    make_box(center=(0.14, 1.35, -0.74), size=(0.28, 0.14, 0.14), rot_deg=(0, 0, 0)),
]
for i in range(14):
    a0 = np.pi * (i / 14.0)
    a1 = np.pi * ((i + 1) / 14.0)
    ym = 0.96 + 0.455 * np.sin((a0 + a1) * 0.5)
    zm = -0.06 + 0.81 * np.cos((a0 + a1) * 0.5)
    pitch = -np.degrees(np.arctan2(
        0.455 * (np.sin(a1) - np.sin(a0)),
        0.81 * (np.cos(a1) - np.cos(a0))
    ))
    frame_parts.append(make_box(center=(0.02, ym, zm), size=(0.04, 0.035, 0.16), rot_deg=(pitch, 0, 0)))
for i in range(10):
    ang = (np.pi * 0.5) * (i / 9.0)
    xm = 0.505 * np.cos(ang)
    ym = 0.96 + 0.455 * np.sin(ang)
    roll = np.degrees(ang)
    frame_parts.append(make_box(center=(xm, ym, -0.04), size=(0.035, 0.11, 0.055), rot_deg=(0, 0, roll)))
mesh_04_frame = mirror_and_merge(frame_parts)

# 5. RECESSED SIDE ENGINE MANIFOLD PIPES & SKIRT VENTS
side_parts = [
    make_box(center=(0.79, 0.57, -0.20), size=(0.05, 0.23, 1.12)),
    make_box(center=(0.84, 0.68, -0.20), size=(0.11, 0.03, 1.12)),
    make_box(center=(0.84, 0.46, -0.20), size=(0.11, 0.03, 1.12)),
]
for i in range(5):
    z_pipe = -0.56 + i * 0.18
    side_parts.append(make_cyl(center=(0.835, 0.57, z_pipe), radius=0.064, height=0.22, sections=20, rot_deg=(90, 0, -10)))
    side_parts.append(make_cyl(center=(0.840, 0.57, z_pipe), radius=0.072, height=0.055, sections=20, rot_deg=(90, 0, -10)))
for i in range(8):
    side_parts.append(make_box(center=(0.84, 0.34, -0.68 + i * 0.13), size=(0.06, 0.065, 0.055), rot_deg=(0, 0, -14)))
mesh_05_manifold = mirror_and_merge(side_parts)

# 6. FOUR CORNER HOVER PODS
pod_parts = []
for z_pod in (1.32, -1.38):
    pod_parts.append(make_box(center=(0.86, 0.25, z_pod), size=(0.42, 0.16, 0.92)))
    pod_parts.append(make_box(center=(0.86, 0.14, z_pod), size=(0.36, 0.09, 0.78)))
    pod_parts.append(make_box(center=(0.86, 0.05, z_pod), size=(0.44, 0.10, 0.86)))
mesh_06_pods = mirror_and_merge(pod_parts)

# 7. FOUR SWEPT WINGLETS & V-TAIL STABILIZERS
wing_parts = []
for z_w, x_w, y_w, span in [(1.18, 0.98, 0.48, 0.62), (-1.42, 0.88, 0.54, 0.58)]:
    wing_parts.append(make_cyl(center=(x_w, y_w + 0.02, z_w), radius=0.060, height=0.44, sections=18))
    top = [
        [x_w,        y_w + 0.024, z_w + 0.18],
        [x_w,        y_w + 0.024, z_w - 0.20],
        [x_w + span, y_w - 0.045, z_w - 0.34],
        [x_w + span, y_w - 0.045, z_w - 0.12],
    ]
    bot = [
        [x_w,        y_w - 0.024, z_w + 0.18],
        [x_w,        y_w - 0.024, z_w - 0.20],
        [x_w + span, y_w - 0.075, z_w - 0.34],
        [x_w + span, y_w - 0.075, z_w - 0.12],
    ]
    wing_parts.append(make_wedge_wing(top, bot))
fx, fy, fz = 0.44, 0.94, -1.62
fh, cant = 0.68, 0.24
fin_left = [
    [fx - 0.028,        fy,      fz + 0.34],
    [fx - 0.028,        fy,      fz - 0.34],
    [fx + cant - 0.016, fy + fh, fz - 0.56],
    [fx + cant - 0.016, fy + fh, fz - 0.24],
]
fin_right = [
    [fx + 0.028,        fy,      fz + 0.34],
    [fx + 0.028,        fy,      fz - 0.34],
    [fx + cant + 0.016, fy + fh, fz - 0.56],
    [fx + cant + 0.016, fy + fh, fz - 0.24],
]
wing_parts.append(make_wedge_wing(fin_left, fin_right))
mesh_07_wings = mirror_and_merge(wing_parts)

# 8. REAR STEPPED THRUSTER NOZZLE
thruster_parts = [
    make_frustum(center=(0.0, 0.58, -2.38), r_back=0.35, r_front=0.38, length=0.22, sections=32),
    make_frustum(center=(0.0, 0.58, -2.53), r_back=0.29, r_front=0.32, length=0.18, sections=32),
    make_frustum(center=(0.0, 0.58, -2.63), r_back=0.22, r_front=0.22, length=0.08, sections=32),
]
mesh_08_thruster = trimesh.util.concatenate(thruster_parts)

# 9. EXPORT CLAY GLB
clay_mat = trimesh.visual.material.PBRMaterial(
    name="Clay_Gray",
    baseColorFactor=[0.62, 0.63, 0.65, 1.0],
    metallicFactor=0.05,
    roughnessFactor=0.65,
)
scene = trimesh.Scene()
named_meshes = [
    ("01_Main_Hull", mesh_01_hull),
    ("02_Intakes_And_Louvers", mesh_02_vents),
    ("03_Canopy_Glass", mesh_03_canopy),
    ("04_Canopy_Frame_And_Scoop", mesh_04_frame),
    ("05_Side_Manifold", mesh_05_manifold),
    ("06_Hover_Pods", mesh_06_pods),
    ("07_Winglets_And_Fins", mesh_07_wings),
    ("08_Rear_Thruster", mesh_08_thruster),
]
for name, m in named_meshes:
    m.visual = trimesh.visual.TextureVisuals(material=clay_mat)
    scene.add_geometry(m, node_name=name, geom_name=name)

scene.export("scifi_hovercraft_clay.glb")
print("Exported scifi_hovercraft_clay.glb:", scene.bounds)
