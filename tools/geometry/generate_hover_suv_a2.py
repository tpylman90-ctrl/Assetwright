"""Assetwright Hover Racing SUV A2 — sculptural mesh study and GLB output.
Deterministic free Python geometry, based on approved Hover Race SUV Concept A1.
Nose -Y / Rear +Y / Z up, one mesh per editable assembly. Blender conversion-ready.
"""
import os,math,json,sys
import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator
from PIL import Image,ImageDraw,ImageFont
import vtk
from vtk.util.numpy_support import numpy_to_vtk

OUT=os.environ.get('ASSETWRIGHT_OUTPUT_DIR','generated/hover_suv_a2'); os.makedirs(OUT,exist_ok=True)
parts=[]
COLOR={
 'silver':(184,194,208,255),'pearl':(221,227,234,255),'crimson':(173,31,45,255),
 'dark':(40,49,64,255),'carbon':(20,27,37,255),'glass':(31,59,78,255),
 'cyan':(37,221,255,255),'redlight':(239,37,48,255),'trim':(99,112,127,255),
 'seat':(124,28,39,255),'cabin':(38,37,45,255)
}

def insert(name, vertices, faces, material):
    fs=[]
    for f in faces:
        if len(f)==3:fs.append(f)
        elif len(f)>3:
            for j in range(1,len(f)-1):fs.append((f[0],f[j],f[j+1]))
    mesh=trimesh.Trimesh(vertices=np.asarray(vertices,float),faces=np.asarray(fs,int),process=False)
    mesh.visual.face_colors=np.array(COLOR[material],dtype=np.uint8)
    mesh.metadata['name']=name
    parts.append((name,mesh,material))
    return mesh

def loft(name, rows,material, closed=False,caps=False):
    rows=np.asarray(rows,float)
    n=len(rows[0]); faces=[]
    for j in range(len(rows)-1):
        for i in range(n if closed else n-1):
            faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    if closed and caps:
        faces+=[tuple(range(n-1,-1,-1)),tuple(range((len(rows)-1)*n,len(rows)*n))]
    return insert(name,rows.reshape(-1,3),faces,material)

def strip(name,points,material):return loft(name,points,material)

def box(name,pos,size,material):
    m=trimesh.creation.box(extents=size);m.apply_translation(pos)
    m.visual.face_colors=np.array(COLOR[material],np.uint8)
    parts.append((name,m,material));return m

def tapered_tube(name, path, radii, material, sides=12):
    path=np.asarray(path,float);radii=np.atleast_1d(radii)
    if len(radii)==1:radii=np.full(len(path),radii.item())
    rings=[]
    for i,point in enumerate(path):
        v=path[min(len(path)-1,i+1)]-path[max(0,i-1)]
        v/=max(np.linalg.norm(v),1e-9)
        up=np.array([0,0,1.0]); u=np.cross(v,up)
        if np.linalg.norm(u)<1e-5:u=np.cross(v,[0,1,0])
        u/=np.linalg.norm(u);w=np.cross(v,u)
        rings.append([point+radii[i]*(u*np.cos(t)+w*np.sin(t)) for t in np.linspace(0,math.tau,sides,endpoint=False)])
    return loft(name,rings,material,closed=True,caps=True)

def smooth_curve(name,anchors,radius,mat):
    anchor=np.asarray(anchors,float);st=np.arange(len(anchor))
    ts=np.linspace(0,len(anchor)-1,(len(anchor)-1)*6+1)
    pts=np.stack([PchipInterpolator(st,anchor[:,k])(ts) for k in range(3)],axis=-1)
    return tapered_tube(name,pts,np.full(len(pts),radius),mat,8)

def super_ring(name,cx,cy,profile,mat,N=40,pow=3.7):
    t=np.linspace(0,2*math.pi,N,endpoint=False)
    ct=np.sign(np.cos(t))*np.abs(np.cos(t))**(2/pow)
    st=np.sign(np.sin(t))*np.abs(np.sin(t))**(2/pow)
    rows=[[(cx+rx*x,cy+ry*y,z) for x,y in zip(ct,st)] for z,rx,ry in profile]
    return loft(name,rows,mat,closed=True,caps=True)

# === SECTION CONTROL MESH: long silhouette + integrated quarter haunches ===
S=np.array([
 (-3.60,.82,.64,1.10,1.18),(-3.44,1.22,.62,1.13,1.25),
 (-3.03,1.67,.61,1.24,1.36),(-2.53,1.77,.60,1.35,1.44),
 (-2.09,1.73,.62,1.35,1.44),(-1.53,1.65,.62,1.36,1.47),
 (-.83,1.66,.62,1.41,1.50),(-.21,1.72,.64,1.43,1.53),
 (.62,1.80,.64,1.48,1.57),(1.39,1.91,.63,1.52,1.59),
 (1.93,1.96,.63,1.55,1.60),(2.39,1.92,.62,1.49,1.55),
 (2.94,1.80,.64,1.40,1.46),(3.36,1.55,.67,1.31,1.35),
 (3.50,1.39,.68,1.22,1.27)])
yvals=np.linspace(S[0,0],S[-1,0],82)
spline=[PchipInterpolator(S[:,0],S[:,i]) for i in range(1,5)]
body_rows=[]
for y in yvals:
    w,bottom,sh,crown=(float(s(y)) for s in spline)
    # combine continuous curvature with broad integrated shoulder power bulges
    front=np.exp(-((y+2.50)/.64)**2);rear=np.exp(-((y-2.02)/.72)**2)
    w+=.075*front+.115*rear
    sh+=.035*front+.045*rear
    side_pts=[(0,bottom-.060),(.46*w,bottom-.055),(.78*w,bottom+.015),
        (.94*w,bottom+.105),(1.01*w,bottom+.22),(1.027*w,sh-.34),
        (1.03*w,sh-.20),(1.01*w,sh-.075),(.97*w,sh+.015),
        (.89*w,sh+.088),(.76*w,sh+.16),(.57*w,crown-.012),
        (.29*w,crown+.028),(0,crown+.045)]
    # counterclockwise full closed section from floor center to starboard shoulder to port
    perimeter=side_pts+ [(-x,z) for x,z in reversed(side_pts[1:-1])]
    body_rows.append([(x,y,z) for x,z in perimeter])
loft('A2 / lofted sculptural SUV master hull',body_rows,'silver',True,True)

# Correct paint ribbons follow the longitudinal surface. Two smooth embedded crimson bands.
for side in [-1,1]:
    rows=[]
    for y in np.linspace(-3.49,-1.36,28):
        w,b,sh,cr=[float(s(y)) for s in spline]
        t=(y+3.49)/2.13
        top=cr+.040
        # hood slopes with y from front corners to the windshield
        rows.append([(side*(.17+.065*t),y,top+.023),
                     (side*(.49+.14*t),y,top+.018)])
    loft('A2 / crimson hood stripe '+str(side),rows,'crimson')
    rows=[]
    for y in np.linspace(.75,3.12,34):
        w,b,sh,cr=[float(s(y)) for s in spline]
        z=sh+.105
        t=(y-.75)/2.37
        x=w*(.89-.12*t)
        rows.append([(side*(x-.18),y,z+.018),(side*(x+.03),y,z+.018)])
    loft('A2 / curved quarter racing graphics '+str(side),rows,'crimson')

# === SCULPTED GREENHOUSE (continuous splined roof and shaped glass) ===
# longitudinal roof profile; strong SUV cabin height rather than very flat roof
CAN=np.array([
 [-1.51,1.24,1.51],[-1.16,1.04,1.83],[-.65,.94,2.26],
 [-.39,.99,2.34],[.38,1.03,2.39],[1.25,1.02,2.36],
 [1.65,.99,2.28],[2.18,1.17,1.75],[2.40,1.22,1.55]])
cy=np.linspace(CAN[0,0],CAN[-1,0],70)
interp=[PchipInterpolator(CAN[:,0],CAN[:,i]) for i in (1,2)]
roofrows=[]
for y in np.linspace(-.60,1.67,46):
    w,h=(float(s(y)) for s in interp)
    roofrows.append([(w*p,y,h+.012*(1-p*p)+.060*(1-p*p)) for p in np.linspace(-1,1,17)])
loft('A2 / gently arched bonded roof skin',roofrows,'pearl')

# windshield curved both across width and in fore-aft sweep
winds=[]
for y in np.linspace(-1.50,-.61,24):
    w,h=(float(s(y)) for s in interp)
    winds.append([(w*p,y-.035*(1-p*p),h+.061*(1-p*p)) for p in np.linspace(-1,1,17)])
loft('A2 / continuously curved front glazing',winds,'glass')

rear_glass=[]
for y in np.linspace(1.68,2.36,23):
    w,h=(float(s(y)) for s in interp)
    rear_glass.append([(w*p,y+.038*(1-p*p),h+.045*(1-p*p)) for p in np.linspace(-1,1,15)])
loft('A2 / swept rear hatch glass',rear_glass,'glass')

for side in [-1,1]:
    label='port' if side<0 else 'starboard'
    # curved side glass represented as actual subdivided surface panels; no massive triangles
    for title,start,end in [('front door',-1.08,.20),('rear door',.28,1.59)]:
        y_samples=np.linspace(start,end,22)
        rows=[]
        for y in y_samples:
            wr,hr=(float(s(y)) for s in interp)
            lower=1.55+.05*(y+1)
            rows.append([(side*(wr+.12+.055*math.sin(math.pi*(y-start)/(end-start))),y,lower),
                         (side*wr,y,hr-.065)])
        loft('A2 / '+label+' '+title+' tinted glazing',rows,'glass')
    # shaped A,B,C structural pillars and thicker painted window beltline
    smooth_curve('A2 / '+label+' A pillar',[(side*1.21,-1.50,1.49),
           (side*1.06,-1.12,1.82),(side*.94,-.63,2.29)],.045,'carbon')
    smooth_curve('A2 / '+label+' B pillar',[(side*1.22,.23,1.57),
           (side*1.13,.27,1.99),(side*1.01,.25,2.37)],.050,'carbon')
    smooth_curve('A2 / '+label+' C pillar',[(side*1.28,1.95,1.52),
           (side*1.16,1.75,1.96),(side*.99,1.65,2.29)],.078,'silver')
    smooth_curve('A2 / '+label+' roof side rail',[(side*.97,-.63,2.32),
           (side*1.03,.21,2.38),(side*1.02,1.25,2.37),
           (side*.99,1.65,2.30)],.058,'carbon')
    smooth_curve('A2 / '+label+' lower window sill',[(side*1.20,-1.48,1.48),
           (side*1.29,-.28,1.56),(side*1.33,1.12,1.63),
           (side*1.27,2.05,1.56)],.045,'carbon')

# === BODY-FORMED AERO SIDE GILLS and SHOULDER FLOW ===
for side in [-1,1]:
    label='port' if side<0 else 'starboard'
    # shaped concave rocker is a recessed dark blade; crest/edge flows continuously
    strip('A2 / '+label+' forged rocker shadow',[
       [(side*1.53,y,.69),(side*1.70,y,.73),(side*1.77,y,.83)]
       for y in np.linspace(-1.89,2.60,30)],'carbon')
    strip('A2 / '+label+' structural lower rocker',[
       [(side*1.46,y,.63),(side*1.67,y,.63),(side*1.75,y,.70)]
       for y in np.linspace(-1.97,2.72,30)],'dark')
    # functional mid-door side plenum with indented (not floating) pocket
    strip('A2 / '+label+' side air intake',[
       [(side*(1.61+ .02*math.sin(t*math.pi)),y,.94),
        (side*(1.69+ .04*math.sin(t*math.pi)),y,1.105)]
       for t,y in [(t,-1.25+1.28*t) for t in np.linspace(0,1,24)]], 'carbon')
    smooth_curve('A2 / '+label+' intake sharp upper lip',[
       (side*1.61,-1.30,1.105),(side*1.70,-.72,1.16),
       (side*1.75,-.12,1.16)],.032,'silver')
    # blend a long rear shoulder crease and thin red accent into car body
    smooth_curve('A2 / '+label+' rear haunch crest',[(side*1.62,.53,1.48),
        (side*1.88,1.52,1.62),(side*1.92,2.19,1.56),
        (side*1.66,2.95,1.41)],.029,'pearl')
    # side marker covers and wing mirrors
    box('A2 / '+label+' mirror base',(side*1.31,-1.12,1.66),(.20,.27,.14),'carbon')
    super_ring('A2 / '+label+' streamlined mirror pod',side*1.42,-1.09,
        [(1.61,.18,.23),(1.66,.22,.25),(1.71,.19,.22)],'dark',24,4)

# === FOUR LARGE PROTECTED HOVER ASSEMBLIES; dark sculpted arch, armored pod and emission ===
for side in [-1,1]:
  for y,kind in [(-2.51,'front'),(2.09,'rear')]:
    x=side*1.47;tag=('port' if side<0 else 'starboard')+' '+kind
    # dark recess giving clear arch separation from shell
    super_ring('A2 / '+tag+' inset arch well',x,y,
               [(.69,.54,.70),(.78,.61,.75),(1.05,.64,.75)],'carbon',40,4.8)
    # upper shell hugs SUV body and continuously decreases around pod
    super_ring('A2 / '+tag+' raised ceramic fender cap',x,y,
               [(1.03,.56,.72),(1.10,.63,.76),(1.18,.60,.73),
                (1.22,.52,.62),(1.23,.30,.34)],'silver',40,4.0)
    # heavy multi-layered black hover unit like reference, no wheels
    super_ring('A2 / '+tag+' lower armored foot',x,y,
               [(.27,.37,.52),(.33,.51,.67),(.53,.55,.69),
                (.70,.55,.69),(.80,.50,.62)],'dark',40,4.5)
    super_ring('A2 / '+tag+' levitation field ring',x,y,
               [(.235,.24,.40),(.260,.41,.59),(.298,.46,.64),
                (.331,.43,.60)],'cyan',40,3.7)
    super_ring('A2 / '+tag+' central coil dark well',x,y,
               [(.188,.19,.35),(.231,.25,.42)],'carbon',36,3.4)
    super_ring('A2 / '+tag+' inset blue core',x,y,
               [(.179,.13,.26),(.195,.17,.31),(.220,.17,.31)],'cyan',32,3.2)
    # vertical armor slats on outboard shell to read like duct vents
    for k in range(-2,3):
        yc=y+k*.18
        box('A2 / '+tag+' cooling vanes '+str(k),
            (side*1.98,yc,.72),(.035,.10,.27),'carbon')

# === FRONT FASCIA: recessed black void with layered grille and aerodynamic lower splitter ===
# front frame is split by color but flush with sculpted nose
box('A2 / multi-layer dark front radiator mouth',(0,-3.575,.97),(1.42,.16,.31),'carbon')
box('A2 / aerodynamic lower chin',(0,-3.64,.69),(1.70,.23,.13),'dark')
for z in [.85,.94,1.02]:box('A2 / grille horizontal strake z%.2f'%z,(0,-3.67,z),(1.31,.04,.022),'trim')
for side in [-1,1]:
    tag='L' if side<0 else 'R'
    # heads follow front swept fender; thin and angled
    strip('A2 / '+tag+' wraparound cyan headlight',[
         [(side*.56,-3.51,1.24),(side*1.17,-3.38,1.255)],
         [(side*.56,-3.51,1.295),(side*1.17,-3.38,1.310)]],'cyan')
    box('A2 / '+tag+' lower driving lamp',(side*1.36,-3.29,.83),(.30,.06,.09),'cyan')
    # rear lamp clusters mould across outer shoulders
    strip('A2 / '+tag+' continuous rear light',[
       [(side*.32,3.47,1.38),(side*1.43,3.33,1.39)],
       [(side*.32,3.47,1.46),(side*1.43,3.33,1.47)]],'redlight')
    super_ring('A2 / '+tag+' inset rear diffuser',side*.82,3.44,
        [(.65,.45,.12),(.80,.47,.12)],'carbon',32,4)
box('A2 / rear fascia molded dark diffuser',(0,3.52,.76),(2.64,.16,.21),'carbon')
box('A2 / rear recessed hatch',(0,3.49,1.21),(2.55,.06,.24),'dark')

# rear roof aero: thin molded swept wing fitted to roof, no giant slab
strip('A2 / formed light rear hatch spoiler',[
    [(-1.08,1.72,2.285),(0,1.74,2.36),(1.08,1.72,2.285)],
    [(-1.14,2.07,2.285),(0,2.11,2.36),(1.14,2.07,2.285)],
    [(-1.13,2.19,2.275),(0,2.21,2.31),(1.13,2.19,2.275)]], 'dark')
for side in [-1,1]:
    smooth_curve('A2 / roof spoiler endplate '+str(side),[
       (side*1.04,1.69,2.28),(side*1.15,2.09,2.29),
       (side*1.11,2.23,2.24)],.040,'crimson')

# === INTERIOR physically in cabin with no exterior-floating dashboard ===
box('A2 / cabin floor',(0,.50,1.13),(2.15,2.50,.085),'cabin')
box('A2 / bonded dashboard beneath windscreen',(0,-1.22,1.56),(2.18,.32,.18),'dark')
box('A2 / center tunnel',(0,.43,1.32),(.31,1.76,.15),'carbon')
for side in [-1,1]:
    x=side*.52;tag='driver' if side<0 else 'passenger'
    super_ring('A2 / '+tag+' seat lower shell',x,.52,
        [(1.24,.38,.42),(1.32,.39,.44),(1.38,.33,.40)],'seat',26,4)
    strip('A2 / '+tag+' shaped seatback',[
      [(x-.36,.83,1.40),(x,.83,1.38),(x+.36,.83,1.40)],
      [(x-.33,1.10,1.91),(x,1.08,1.94),(x+.33,1.10,1.91)]], 'seat')
    super_ring('A2 / '+tag+' head bolster',x,1.12,
        [(1.90,.23,.12),(2.03,.21,.12),(2.08,.15,.10)],'cabin',24,3)

# Export GLB and render through VTK offscreen GPU-independent pipeline
scene=trimesh.Scene()
for name,m,material in parts:scene.add_geometry(m,node_name=name)
filepath=os.path.join(OUT,'assetwright_hover_suv_a2_surface_pass.glb')
scene.export(filepath)
tris=sum(len(m.faces) for _,m,_ in parts)
assert 0<tris<120000, tris
print('GLB ready',os.path.getsize(filepath),'bytes',tris,'triangles',len(parts),'submeshes',flush=True)

# simple studio renderer

def vtk_mesh(mesh):
    pd=vtk.vtkPolyData();pts=vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(mesh.vertices,dtype=np.float32),deep=True))
    pd.SetPoints(pts)
    cells=vtk.vtkCellArray()
    for face in mesh.faces:
        cells.InsertNextCell(3)
        for v in face:cells.InsertCellPoint(int(v))
    pd.SetPolys(cells)
    normals=vtk.vtkPolyDataNormals();normals.SetInputData(pd);normals.ConsistencyOn()
    normals.AutoOrientNormalsOff();normals.SplittingOff();normals.Update()
    return normals.GetOutput()

renderer=vtk.vtkRenderer();renderer.SetBackground(.035,.043,.067);renderer.SetBackground2(.09,.12,.17);renderer.GradientBackgroundOn()
for name,mesh,material in parts:
    actor=vtk.vtkActor();mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(vtk_mesh(mesh))
    actor.SetMapper(mapper)
    r,g,b,a=COLOR[material];p=actor.GetProperty();p.SetColor(r/255,g/255,b/255)
    p.SetInterpolationToPhong();p.SetAmbient(.20)
    p.SetDiffuse(.70);p.SetSpecular(.27 if material not in ('glass','carbon') else .42)
    p.SetSpecularPower(32 if material not in ('glass','carbon') else 50)
    if material in ('cyan','redlight'):
        p.SetAmbient(1.0);p.SetDiffuse(.12);p.SetSpecular(.05)
    renderer.AddActor(actor)

# Neutral seamless background keeps geometric silhouette unambiguous.
for position,power,color in [((-7,-6,11),.90,(1,1,1)),((9,6,8),.62,(.69,.84,1)),((0,9,11),.45,(1,.75,.68))]:
    light=vtk.vtkLight();light.SetLightTypeToSceneLight();light.SetPosition(position)
    light.SetFocalPoint(0,0,1);light.SetIntensity(power);light.SetColor(*color)
    renderer.AddLight(light)
window=vtk.vtkRenderWindow();window.SetOffScreenRendering(True);window.SetSize(1180,750)
window.SetMultiSamples(8);window.AddRenderer(renderer)
renderer.SetUseDepthPeeling(False)

views={
 'front_3q':(8,-11,6.0),
 'rear_3q':(8,11,6.0),
 'side':(12,-.01,3.6),
 'top':(0,-.001,14),
}
paths=[]
for name,eye in views.items():
    camera=renderer.GetActiveCamera();camera.ParallelProjectionOn()
    camera.SetPosition(*eye);camera.SetFocalPoint(0,0,1.24)
    camera.SetViewUp(0,0,1) if name!='top' else camera.SetViewUp(0,1,0)
    camera.SetParallelScale(4.15 if name!='side' else 3.65)
    renderer.ResetCameraClippingRange()
    window.Render()
    filt=vtk.vtkWindowToImageFilter();filt.SetInput(window);filt.SetInputBufferTypeToRGB();filt.ReadFrontBufferOff();filt.Update()
    out=os.path.join(OUT,'assetwright_hover_suv_a2_'+name+'.png')
    writer=vtk.vtkPNGWriter();writer.SetFileName(out);writer.SetInputConnection(filt.GetOutputPort());writer.Write();paths.append((name,out))
    print('Rendered:',name,flush=True)

sheet=Image.new('RGB',(2360,1580),(21,27,37));draw=ImageDraw.Draw(sheet)
for i,(name,path) in enumerate(paths):
    tile=Image.open(path).convert('RGB');x=i%2*1180;y=i//2*790
    sheet.paste(tile,(x,y+40))
    draw.text((x+25,y+13),name.upper().replace('_','  '),fill=(238,242,248))
sheetpath=os.path.join(OUT,'assetwright_hover_suv_a2_review_sheet.png');sheet.save(sheetpath)
metadata={'asset':'Hover Race SUV','revision':'A2 shape & surfacing',
 'reference':'/Assetwright/References/Hover_Race_SUV_Concept_A1.png',
 'geometry_triangles':tris,'mesh_assemblies':len(parts),
 'status':'offscreen-rendered GLB, not yet validated with Blender nor Godot',
 'techniques':['PCHIP 82-section continuous master shell','integrated front and rear haunches','arched spline roof','multi-section glass','rounded-square hover assemblies','reduced spoiler profile']}
with open(os.path.join(OUT,'assetwright_hover_suv_a2_record.json'),'w') as f:json.dump(metadata,f,indent=2)
print('ALL COMPLETE',json.dumps(metadata))