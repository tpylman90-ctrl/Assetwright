"""GEMINI CATAMARAN HOVERCRAFT — geometry supplied by user.
User message ends mid-line inside the energy section; all sections through
dual canopies reproduce the provided geometry. The final glow meshes,
material assignment and export are minimal assistant-authored completion.
Coordinate system: X span, Y up, Z forward. Pure NumPy + Trimesh.
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

def make_tube(center, r_inner, r_outer, height, sections=32, rot_deg=(0, 0, 0)):
    angles = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    ca, sa = np.cos(angles), np.sin(angles)
    z0, z1 = -height * 0.5, height * 0.5
    vo_b = np.column_stack([r_outer * ca, r_outer * sa, np.full(sections, z0)])
    vo_t = np.column_stack([r_outer * ca, r_outer * sa, np.full(sections, z1)])
    vi_b = np.column_stack([r_inner * ca, r_inner * sa, np.full(sections, z0)])
    vi_t = np.column_stack([r_inner * ca, r_inner * sa, np.full(sections, z1)])
    verts = np.vstack([vo_b, vo_t, vi_b, vi_t])
    n = sections
    faces = []
    for i in range(n):
        ni = (i + 1) % n
        faces.append([i, ni, n + ni])
        faces.append([i, n + ni, n + i])
        faces.append([2 * n + i, 3 * n + ni, 2 * n + ni])
        faces.append([2 * n + i, 3 * n + i, 3 * n + ni])
        faces.append([n + i, n + ni, 3 * n + ni])
        faces.append([n + i, 3 * n + ni, 3 * n + i])
        faces.append([i, 2 * n + ni, ni])
        faces.append([i, 2 * n + i, 2 * n + ni])
    m = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    m.fix_normals()
    return xform(m, center, rot_deg)

def make_frustum(center, r_back, r_front, length, sections=32, rot_deg=(0, 0, 0)):
    angles = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    ca, sa = np.cos(angles), np.sin(angles)
    z0, z1 = -length * 0.5, length * 0.5
    vb = np.column_stack([r_back * ca, r_back * sa, np.full(sections, z0)])
    vf = np.column_stack([r_front * ca, r_front * sa, np.full(sections, z1)])
    cb = np.array([[0.0, 0.0, z0]])
    cf = np.array([[0.0, 0.0, z1]])
    verts = np.vstack([vb, vf, cb, cf])
    icb, icf = 2 * sections, 2 * sections + 1
    faces = []
    for i in range(sections):
        ni = (i + 1) % sections
        faces.append([i, ni, sections + ni])
        faces.append([i, sections + ni, sections + i])
        faces.append([icb, ni, i])
        faces.append([icf, sections + i, sections + ni])
    m = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    m.fix_normals()
    return xform(m, center, rot_deg)

def make_strut(p0, p1, radius, sections=14):
    p0 = np.array(p0, dtype=float)
    p1 = np.array(p1, dtype=float)
    vec = p1 - p0
    length = np.linalg.norm(vec)
    if length < 1e-6:
        return make_box(p0, (radius, radius, radius))
    m = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    z_axis = np.array([0.0, 0.0, 1.0])
    direction = vec / length
    dot = np.clip(np.dot(z_axis, direction), -1.0, 1.0)
    if dot < -0.9999:
        rot = euler_matrix(np.pi, 0.0, 0.0)
    elif dot > 0.9999:
        rot = np.eye(4)
    else:
        axis = np.cross(z_axis, direction)
        axis /= np.linalg.norm(axis)
        angle = np.arccos(dot)
        rot = trimesh.transformations.rotation_matrix(angle, axis)
    mat = translation_matrix((p0 + p1) * 0.5) @ rot
    m.apply_transform(mat)
    return m

def make_bent_pipe(points, radius, sections=14):
    segs = []
    for i in range(len(points) - 1):
        segs.append(make_strut(points[i], points[i + 1], radius, sections=sections))
        if 0 < i < len(points) - 1:
            joint = trimesh.creation.icosphere(subdivisions=1, radius=radius * 1.08)
            joint.apply_translation(points[i])
            segs.append(joint)
    return trimesh.util.concatenate(segs)

def make_prism(pts_top, pts_bot):
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

def mirror_x(parts):
    combined = trimesh.util.concatenate(parts)
    mv = combined.vertices.copy()
    mv[:, 0] *= -1.0
    mf = combined.faces[:, ::-1]
    mir = trimesh.Trimesh(vertices=mv, faces=mf, process=False)
    out = trimesh.util.concatenate([combined, mir])
    out.merge_vertices()
    out.fix_normals()
    return out

# 1. TWIN CATAMARAN ARMOR HULLS + CENTRAL QUANTUM BRIDGE
sponson_stations = [
    (-2.25,  0.34, 0.30, 0.38, 0.80, 0.86, 0.86, 0.86, 0.78, 0.28, 0.38, 0.40, 0.64, 0.66, 0.76, 0.80),
    (-1.75,  0.26, 0.24, 0.34, 0.86, 0.96, 0.96, 0.96, 0.84, 0.22, 0.36, 0.38, 0.66, 0.68, 0.80, 0.86),
    (-0.90,  0.24, 0.22, 0.32, 0.88, 0.98, 0.98, 0.98, 0.86, 0.18, 0.34, 0.36, 0.66, 0.68, 0.82, 0.88),
    (-0.82,  0.24, 0.30, 0.32, 0.88, 0.98, 0.75, 0.98, 0.86, 0.18, 0.34, 0.36, 0.66, 0.68, 0.82, 0.88),
    ( 0.25,  0.24, 0.32, 0.32, 0.88, 0.98, 0.74, 0.98, 0.86, 0.18, 0.34, 0.36, 0.66, 0.68, 0.82, 0.88),
    ( 1.15,  0.24, 0.30, 0.32, 0.88, 0.98, 0.75, 0.98, 0.86, 0.18, 0.34, 0.36, 0.66, 0.68, 0.80, 0.86),
    ( 1.24,  0.24, 0.22, 0.32, 0.88, 0.98, 0.98, 0.98, 0.86, 0.18, 0.34, 0.36, 0.66, 0.68, 0.78, 0.84),
    ( 1.95,  0.30, 0.28, 0.36, 0.82, 0.90, 0.90, 0.90, 0.80, 0.20, 0.32, 0.34, 0.58, 0.60, 0.68, 0.72),
    ( 2.65,  0.38, 0.36, 0.42, 0.74, 0.80, 0.80, 0.80, 0.72, 0.23, 0.32, 0.34, 0.50, 0.52, 0.58, 0.61),
    ( 2.88,  0.42, 0.40, 0.45, 0.70, 0.75, 0.75, 0.75, 0.68, 0.25, 0.32, 0.34, 0.46, 0.48, 0.53, 0.55),
]
rings = []
for st in sponson_stations:
    (z, xib, xim, xit, xob, xosk, xobay, xosh, xot,
     yb, ysk, ybay0, ybay1, ysh, yt, ycrw) = st
    xc = 0.5 * (xib + xob)
    rings.append([
        [xc,yb,z], [xob,yb,z], [xosk,ysk,z],
        [xobay,ybay0,z], [xobay,ybay1,z], [xosh,ysh,z],
        [xot,yt,z], [xc,ycrw,z], [xit,yt,z],
        [xim,0.50,z], [xib,yb,z]
    ])
rings = np.array(rings, dtype=float)
nr, np_ring, _ = rings.shape
sponson_verts = rings.reshape(-1, 3)
sponson_faces = []
for r in range(nr-1):
    for p in range(np_ring):
        pn = (p+1) % np_ring
        i00 = r*np_ring+p
        i01 = r*np_ring+pn
        i10 = (r+1)*np_ring+p
        i11 = (r+1)*np_ring+pn
        sponson_faces.append([i00,i01,i11])
        sponson_faces.append([i00,i11,i10])
for p in range(1,np_ring-1):
    sponson_faces.append([0,p+1,p])
    b=(nr-1)*np_ring
    sponson_faces.append([b,b+p,b+p+1])
sponson_mesh = trimesh.Trimesh(vertices=sponson_verts, faces=np.array(sponson_faces), process=False)
sponson_mesh.fix_normals()

hull_parts = [
    sponson_mesh,
    make_box(center=(0.14,0.44,0.25),size=(0.28,0.14,2.15)),
    make_box(center=(0.14,0.54,-0.55),size=(0.28,0.12,0.65),rot_deg=(8,0,0)),
    make_box(center=(0.14,0.53,1.05),size=(0.28,0.12,0.65),rot_deg=(-8,0,0)),
    make_box(center=(0.86,0.66,1.48),size=(0.24,0.14,0.72),rot_deg=(0,0,-14)),
    make_box(center=(0.88,0.66,-1.35),size=(0.24,0.14,0.72),rot_deg=(0,0,-14)),
    make_box(center=(0.58,0.88,-1.15),size=(0.44,0.22,1.15),rot_deg=(6,0,0)),
]
mesh_01_pearl_hull = mirror_x(hull_parts)

# 2. COSMIC NAVY AERO COWLS, CANARDS, V-TAILS & POD SHROUDS
navy_parts = [
    make_box(center=(0.56,0.54,2.86),size=(0.34,0.055,0.24),rot_deg=(6,0,0)),
    make_box(center=(0.56,0.27,2.86),size=(0.34,0.055,0.24),rot_deg=(-4,0,0)),
    make_box(center=(0.72,0.405,2.84),size=(0.06,0.28,0.26),rot_deg=(0,-6,0)),
    make_box(center=(0.40,0.405,2.84),size=(0.06,0.28,0.26),rot_deg=(0,6,0)),
    make_box(center=(0.56,0.22,2.94),size=(0.38,0.025,0.22),rot_deg=(2,0,0)),
    make_prism(
        pts_top=[[0.78,0.38,2.48],[0.78,0.38,2.15],[1.22,0.33,1.96],[1.22,0.33,2.14]],
        pts_bot=[[0.78,0.35,2.48],[0.78,0.35,2.15],[1.22,0.31,1.96],[1.22,0.31,2.14]],
    ),
    make_box(center=(0.57,0.71,1.82),size=(0.30,0.04,1.25),rot_deg=(7,0,0)),
    make_box(center=(0.12,0.50,1.38),size=(0.24,0.08,0.45),rot_deg=(12,0,0)),
    make_box(center=(0.88,0.19,0.15),size=(0.12,0.04,2.35)),
    make_prism(
        pts_top=[[0.68,0.86,-1.45],[0.68,0.86,-2.28],[0.94,1.48,-2.52],[0.94,1.48,-2.14]],
        pts_bot=[[0.74,0.86,-1.45],[0.74,0.86,-2.28],[0.98,1.48,-2.52],[0.98,1.48,-2.14]],
    ),
    make_box(center=(0.46,1.36,-2.32),size=(0.92,0.035,0.30),rot_deg=(-8,0,0)),
    make_box(center=(0.98,1.05,-2.18),size=(0.26,0.022,0.24),rot_deg=(-4,-12,-8)),
    make_box(center=(1.04,1.24,-2.28),size=(0.24,0.022,0.22),rot_deg=(-4,-12,-8)),
]
for xp,zp in [(1.38,1.48),(1.44,-1.35)]:
    navy_parts.append(make_cyl(center=(xp,0.35,zp),radius=0.39,height=0.06,sections=28))
    for ang_deg in (35,145,215,325):
        rad=np.radians(ang_deg)
        sx=xp+0.385*np.cos(rad)
        sz=zp+0.385*np.sin(rad)
        navy_parts.append(make_box(center=(sx,0.19,sz),size=(0.07,0.24,0.19),rot_deg=(0,-ang_deg,0)))
mesh_02_navy_aero = mirror_x(navy_parts)

# 3. ANODIZED VIOLET / INDIGO GEMINI ACCENT TRIM
violet_parts = [
    make_box(center=(0.94,0.67,0.16),size=(0.05,0.035,1.98)),
    make_box(center=(0.94,0.35,0.16),size=(0.05,0.035,1.98)),
    make_box(center=(0.82,0.85,0.15),size=(0.045,0.04,1.42),rot_deg=(2,0,0)),
    make_box(center=(0.34,0.85,0.15),size=(0.045,0.04,1.42),rot_deg=(2,0,0)),
    make_box(center=(0.58,0.99,-1.15),size=(0.14,0.035,1.05),rot_deg=(6,0,0)),
    make_box(center=(0.46,1.38,-2.46),size=(0.92,0.025,0.07),rot_deg=(-16,0,0)),
    make_box(center=(0.045,0.56,1.36),size=(0.024,0.022,0.22),rot_deg=(12,0,0)),
    make_box(center=(0.06,0.58,1.46),size=(0.12,0.022,0.028),rot_deg=(12,0,0)),
    make_box(center=(0.06,0.54,1.26),size=(0.12,0.022,0.028),rot_deg=(12,0,0)),
]
mesh_03_violet_trim = mirror_x(violet_parts)

# 4. BRUSHED TITANIUM CHASSIS, SUSPENSION, MANIFOLDS & THRUSTERS
ti_parts=[make_box(center=(0.56,0.405,2.75),size=(0.28,0.22,0.04))]
for i in range(6):
    y_vane=0.31+i*0.038
    ti_parts.append(make_box(center=(0.56,y_vane,2.85),size=(0.27,0.014,0.14),rot_deg=(14,0,0)))
ti_parts.extend([
    make_box(center=(0.58,1.15,0.15),size=(0.035,0.03,1.28)),
    make_box(center=(0.58,1.04,0.68),size=(0.42,0.03,0.035),rot_deg=(28,0,0)),
    make_box(center=(0.58,1.19,-0.42),size=(0.22,0.09,0.24)),
    make_cyl(center=(0.53,1.19,-0.29),radius=0.026,height=0.05,sections=16),
    make_cyl(center=(0.63,1.19,-0.29),radius=0.026,height=0.05,sections=16),
    make_box(center=(0.76,0.51,0.16),size=(0.04,0.28,1.94)),
    make_box(center=(0.83,0.63,0.16),size=(0.10,0.025,1.92)),
    make_box(center=(0.83,0.39,0.16),size=(0.10,0.025,1.92)),
])
for i in range(6):
    z_m=-0.62+i*0.28
    ti_parts.append(make_cyl(center=(0.82,0.51,z_m),radius=0.052,height=0.22,sections=18,rot_deg=(90,0,-8)))
    ti_parts.append(make_cyl(center=(0.825,0.51,z_m),radius=0.062,height=0.055,sections=18,rot_deg=(90,0,-8)))
pod_mounts=[(1.38,1.48,0.86,1.66,1.30),(1.44,-1.35,0.88,-1.17,-1.53)]
for xp,zp,xh,zf,zr in pod_mounts:
    ti_parts.append(make_strut([xh,0.58,zf],[xp-0.12,0.38,zp+0.06],radius=0.024))
    ti_parts.append(make_strut([xh,0.58,zr],[xp-0.12,0.38,zp-0.06],radius=0.024))
    ti_parts.append(make_strut([xh,0.28,zf],[xp-0.16,0.20,zp+0.07],radius=0.028))
    ti_parts.append(make_strut([xh,0.28,zr],[xp-0.16,0.20,zp-0.07],radius=0.028))
    ti_parts.append(make_strut([xh-0.02,0.64,zp],[xp-0.14,0.22,zp],radius=0.032))
    ti_parts.append(make_cyl(center=(xp,0.19,zp),radius=0.29,height=0.28,sections=28,rot_deg=(90,0,0)))
    ti_parts.append(make_tube(center=(xp,0.022,zp),r_inner=0.25,r_outer=0.37,height=0.044,sections=32,rot_deg=(90,0,0)))
tx,ty=0.58,0.52
ti_parts.append(make_frustum(center=(tx,ty,-2.36),r_back=0.27,r_front=0.30,length=0.24,sections=32))
ti_parts.append(make_frustum(center=(tx,ty,-2.58),r_back=0.24,r_front=0.26,length=0.22,sections=32))
for i in range(16):
    ang=2*np.pi*i/16.0
    px=tx+0.235*np.cos(ang)
    py=ty+0.235*np.sin(ang)
    deg=np.degrees(ang)
    ti_parts.append(make_box(center=(px,py,-2.82),size=(0.075,0.024,0.30),rot_deg=(0,0,deg+90)))
mesh_04_titanium=mirror_x(ti_parts)

# 5. COPPER ELECTROMAGNETIC STATOR COILS & RECESSED BUSBARS
copper_parts=[]
for xp,zp in [(1.38,1.48),(1.44,-1.35)]:
    for i in range(14):
        ang=2*np.pi*i/14.0
        cx=xp+0.335*np.cos(ang)
        cz=zp+0.335*np.sin(ang)
        copper_parts.append(make_cyl(center=(cx,0.19,cz),radius=0.036,height=0.23,sections=14,rot_deg=(90,0,0)))
copper_parts.append(make_bent_pipe([
    [0.80,0.60,-0.72],[0.88,0.60,-0.55],[0.88,0.42,-0.10],
    [0.88,0.42,0.55],[0.88,0.59,0.92],[0.80,0.59,1.08]
],radius=0.017))
copper_parts.append(make_bent_pipe([
    [0.79,0.43,-0.68],[0.87,0.43,-0.35],[0.87,0.58,0.22],
    [0.87,0.58,0.85],[0.79,0.44,1.05]
],radius=0.015))
copper_parts.append(make_bent_pipe([[0.18,0.52,-0.75],[0.18,0.52,1.05]],radius=0.016))
mesh_05_copper=mirror_x(copper_parts)

# 6. ASYMMETRIC DUAL COCKPIT INTERIORS (PILOT + AI CORE)
pilot_seat=trimesh.util.concatenate([
    make_box(center=(0.58,0.84,0.10),size=(0.30,0.08,0.34)),
    make_box(center=(0.58,0.96,-0.06),size=(0.28,0.26,0.07),rot_deg=(-18,0,0)),
    make_box(center=(0.58,0.92,0.46),size=(0.22,0.05,0.08),rot_deg=(20,0,0)),
])
ai_core_parts=[make_cyl(center=(-0.58,0.94,0.12),radius=0.14,height=0.26,sections=24,rot_deg=(90,0,0))]
for k in range(5):
    ai_core_parts.append(make_cyl(center=(-0.58,0.85+k*0.045,0.12),radius=0.165,height=0.016,sections=24,rot_deg=(90,0,0)))
bridge_heatsinks=[]
for k in range(12):
    bridge_heatsinks.append(make_box(center=(0.0,0.53,-0.35+k*0.11),size=(0.24,0.05,0.025)))
mesh_06_interiors=trimesh.util.concatenate([pilot_seat]+ai_core_parts+bridge_heatsinks)

# 7. TRANSLUCENT TINTED DUAL CANOPIES
sph=trimesh.creation.icosphere(subdivisions=3,radius=1.0)
sv=sph.vertices.copy()
sv[:,1]=np.maximum(0.0,sv[:,1])
taper=1.0-0.16*sv[:,2]
sv[:,0]*=0.25*taper
sv[:,1]*=0.30
sv[:,2]*=0.72
sv+=np.array([0.58,0.85,0.14])
sph.vertices=sv
c_tri=sph.triangles_center
canopy_right=sph.submesh([c_tri[:,1]>0.852],append=True)
mesh_07_canopy_glass=mirror_x([canopy_right])

# 8. EMISSIVE GEMINI CYAN ENERGY RINGS & PLASMA THRUSTER CORES
# SUPPLIED SECTION THROUGH FIRST ENERGY STRIP. Remaining pieces below supplied by assistant.
glow_parts=[
    make_frustum(center=(0.58,0.52,-2.76),r_back=0.16,r_front=0.06,length=0.28,sections=24),
    make_tube(center=(0.58,0.52,-2.88),r_inner=0.17,r_outer=0.20,height=0.04,sections=28),
    make_box(center=(0.79,0.51,0.16),size=(0.025,0.022,1.82)),
    # Source message ends at: make_box(center=(0.06, 0
    make_box(center=(0.06,0.58,0.26),size=(0.022,0.022,1.88)),
]
# Added to complete energy-ring visualization; not present in the truncated user code.
for xp,zp in [(1.38,1.48),(1.44,-1.35)]:
    glow_parts.append(make_tube(center=(xp,0.030,zp),r_inner=0.37,r_outer=0.39,height=0.018,sections=32,rot_deg=(90,0,0)))
mesh_08_glow=mirror_x(glow_parts)

# 9. EXPORT PBR GLB (assistant-completed because user code was truncated)
def material(name,rgb,metal,rough,alpha=1.0,emissive=None):
    kwargs=dict(name=name,baseColorFactor=[int(255*x) for x in rgb]+[int(255*alpha)],
                metallicFactor=metal,roughnessFactor=rough,alphaMode="BLEND" if alpha<1 else "OPAQUE",
                doubleSided=alpha<1)
    if emissive is not None:
        kwargs["emissiveFactor"]=emissive
    return trimesh.visual.material.PBRMaterial(**kwargs)

palette=[
    ("01_Pearl_Armor",mesh_01_pearl_hull,material("Pearl ceramic",(.86,.88,.91),.36,.30)),
    ("02_Cosmic_Navy_Aero",mesh_02_navy_aero,material("Cosmic navy",(.037,.064,.14),.68,.28)),
    ("03_Violet_Anodized",mesh_03_violet_trim,material("Violet indigo",(.27,.12,.60),.75,.25)),
    ("04_Brushed_Titanium",mesh_04_titanium,material("Titanium",(.39,.47,.53),.85,.34)),
    ("05_Copper_Stators",mesh_05_copper,material("Copper",(.69,.29,.12),.82,.30)),
    ("06_Cockpit_Interiors",mesh_06_interiors,material("Dark cockpit",(.055,.07,.10),.25,.60)),
    ("07_Tinted_Canopies",mesh_07_canopy_glass,material("Cyan smoked glass",(.10,.34,.40),.18,.13,.58)),
    ("08_Cyan_Emission",mesh_08_glow,material("Gemini cyan emission",(.015,.63,.82),.24,.20,1.0,(0.06,.82,1.0))),
]
scene=trimesh.Scene()
for name,mesh,mat in palette:
    mesh.visual=trimesh.visual.TextureVisuals(material=mat)
    scene.add_geometry(mesh,node_name=name,geom_name=name)
scene.export("gemini_catamaran_trimesh.glb")
print("GEMINI_TRIMESH_GENERATION_OK",len(scene.geometry),sum(len(g.faces) for g in scene.geometry.values()),scene.bounds,flush=True)
