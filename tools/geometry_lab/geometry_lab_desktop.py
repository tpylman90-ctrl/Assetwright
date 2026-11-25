#!/usr/bin/env python3
"""Assetwright Geometry Lab: reproducible, non-destructive geometry inspection.
Works on standard GLB (and OBJ/PLY/STL accepted by Trimesh). Meshopt GLBs can be
decoded first with unpack_meshopt.mjs. All derived meshes are copies.
"""
import argparse, hashlib, json, csv, math, os
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

def load(path):
    source=trimesh.load(str(path),force="scene",process=False)
    meshes=[]
    for name, item in source.dump(concatenate=False).items() if isinstance(source.dump(concatenate=False),dict) else enumerate(source.dump(concatenate=False)):
        if isinstance(item,trimesh.Trimesh) and len(item.faces)>0:
            meshes.append(item)
    if not meshes: raise ValueError("No triangle mesh found")
    return trimesh.util.concatenate(meshes)

def write_glb(mesh, values, name, out, palette="signed"):
    v=mesh.copy()
    x=np.asarray(values,dtype=float)
    x=np.nan_to_num(x)
    if palette=="signed":
        z=np.clip((x+1)/2,0,1)
        color=np.column_stack([60+195*z,95+125*(1-np.abs(x)),225-165*z,np.full(len(z),255)])
    elif palette=="category":
        color=np.array([[45+(int(i)*71)%200,75+(int(i)*107)%175,70+(int(i)*53)%185,255] for i in x],dtype=np.uint8)
    else:
        z=np.clip(x,0,1)
        color=np.column_stack([75+180*z,165-130*z,225-195*z,np.full(len(z),255)])
    v.visual=trimesh.visual.ColorVisuals(mesh=v,vertex_colors=np.asarray(np.clip(color,0,255),dtype=np.uint8))
    v.export(str(out/name))
    return str(name)

def plane_segments(vertices,faces,axis,p):
    a=vertices[faces]
    signed=a[:,:,axis]-p
    pts=[]
    for k in range(3):
        j=(k+1)%3
        d0=signed[:,k];d1=signed[:,j]
        yes=(d0*d1)<0
        t=np.zeros_like(d0)
        t[yes]=d0[yes]/(d0[yes]-d1[yes])
        x=a[:,k,:]+(a[:,j,:]-a[:,k,:])*t[:,None]
        pts.append((yes,x))
    coords=[]
    for i in range(3):
        for j in range(i+1,3):
            valid=pts[i][0] & pts[j][0]
            if np.any(valid):
                coords.append(np.stack((pts[i][1][valid],pts[j][1][valid]),axis=1))
    if not coords:return np.zeros((0,2,3))
    return np.concatenate(coords,axis=0)

def curvature(mesh,neighbors):
    xyz=mesh.vertices
    dist, idx=cKDTree(xyz).query(xyz,k=min(len(xyz),neighbors+1),workers=-1)
    neis=xyz[idx[:,1:]]
    norm=mesh.vertex_normals
    dif=neis-xyz[:,None,:]
    scale=np.linalg.norm(dif,axis=2).mean(axis=1).clip(1e-8)
    sign=np.einsum('vkd,vd->vk',dif,norm)
    value=np.median(sign,axis=1)/scale
    return np.clip(value,-1,1)

def topology(mesh,threshold_deg):
    faces=mesh.face_adjacency
    if len(faces):
        dots=np.einsum('ij,ij->i',mesh.face_normals[faces[:,0]],mesh.face_normals[faces[:,1]]).clip(-1,1)
        angles=np.rad2deg(np.arccos(dots))
    else:angles=np.empty(0)
    edges=mesh.face_adjacency_edges
    result=np.zeros(len(mesh.vertices),np.float32)
    np.maximum.at(result,edges[:,0],angles)
    np.maximum.at(result,edges[:,1],angles)
    graph=mesh.edges_unique
    edgesAll=np.sort(mesh.edges,axis=1)
    _,counts=np.unique(edgesAll,axis=0,return_counts=True)
    metrics={
        "adjacent_edges":int(len(angles)),
        "sharp_edges_at_threshold":int(np.count_nonzero(angles>=threshold_deg)),
        "boundary_edges":int(np.count_nonzero(counts==1)),
        "nonmanifold_edges":int(np.count_nonzero(counts>2)),
        "edge_angle_p50":float(np.median(angles)) if len(angles) else 0.,
        "edge_angle_p95":float(np.percentile(angles,95)) if len(angles) else 0.,
    }
    return result,angles,metrics

def vertex_edge_direction(mesh):
    v=mesh.vertices
    es=mesh.edges_unique
    delta=np.abs(v[es[:,0]]-v[es[:,1]])
    dom=np.argmax(delta,axis=1)
    score=np.zeros((len(v),3),float)
    for k in range(3):
        hit=dom==k
        np.add.at(score,es[hit,0],np.eye(3)[k])
        np.add.at(score,es[hit,1],np.eye(3)[k])
    return score.argmax(axis=1)

def components_and_patches(mesh,angles,threshold):
    n=len(mesh.faces)
    fa=mesh.face_adjacency
    keep=fa[angles<threshold] if len(fa) else np.empty((0,2),dtype=int)
    rows=np.r_[keep[:,0],keep[:,1],np.arange(n)]
    cols=np.r_[keep[:,1],keep[:,0],np.arange(n)]
    graph=coo_matrix((np.ones(len(rows)),(rows,cols)),shape=(n,n)).tocsr()
    n_comp,labels=connected_components(graph,directed=False)
    sizes=np.bincount(labels)
    return labels,sizes

def vertex_labels(mesh,face_labels):
    labels=np.zeros(len(mesh.vertices),np.int32)
    if len(mesh.faces):
        labels[mesh.faces.ravel()]=np.repeat(face_labels,3)
    return labels

def profiles(mesh,out,axis=0,count=12):
    v=np.asarray(mesh.vertices);f=np.asarray(mesh.faces)
    axis=int(axis);coords=[k for k in range(3) if k!=axis]
    lo=v[:,axis].min();hi=v[:,axis].max()
    station_list=[]
    with open(out/"section_measurements.csv","w",newline="") as fp:
        w=csv.writer(fp)
        w.writerow(["station","axis","position_source_units","segment_count","width_axis","height_axis","section_width","section_height"])
        for i,q in enumerate(np.linspace(0.04,0.96,count)):
            pos=lo+q*(hi-lo)
            seg=plane_segments(v,f,axis,pos)
            p=seg.reshape(-1,3)
            ext=p[:,coords].ptp(axis=0) if False else (np.ptp(p[:,coords],axis=0) if len(p) else np.zeros(2))
            w.writerow([i,axis,round(pos,7),len(seg),coords[0],coords[1],float(ext[0]),float(ext[1])])
            station_list.append((pos,seg))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(3,4,figsize=(16,11),layout="constrained")
    for ix,(pos,segments) in enumerate(station_list):
        a=axs.flat[ix]
        if len(segments):
            from matplotlib.collections import LineCollection
            a.add_collection(LineCollection(segments[:,:,coords],linewidths=.5,colors="navy"))
            a.autoscale()
        a.set_aspect("equal","box");a.set_title(f"{ix+1}: {pos:.3f}");a.grid(alpha=.15)
    fig.savefig(out/"sections.png",dpi=145);plt.close(fig)
    # A rough outer-envelope loft, deliberately separate from original geometry.
    loops=[]
    for pos,segments in station_list:
        p=segments.reshape(-1,3)
        if len(p)<10:continue
        center=np.mean(p[:,coords],axis=0)
        delta=p[:,coords]-center
        theta=np.arctan2(delta[:,1],delta[:,0])
        radii=np.linalg.norm(delta,axis=1)
        ring=[]
        for a in np.linspace(-math.pi,math.pi,65)[:-1]:
            diff=np.abs((theta-a+math.pi)%(2*math.pi)-math.pi)
            eligible=diff<0.17
            if np.any(eligible):
                k=np.argmax(radii*eligible)
            else:k=np.argmin(diff)
            point=np.zeros(3)
            point[axis]=pos
            point[coords]=p[k,coords]
            ring.append(point)
        loops.append(ring)
    if len(loops)>=3:
        n=len(loops[0])
        verts=np.array(loops,dtype=float).reshape(-1,3)
        tris=[]
        for r in range(len(loops)-1):
            for j in range(n):
                a=r*n+j;b=r*n+(j+1)%n;c=(r+1)*n+j;d=(r+1)*n+(j+1)%n
                tris.extend([[a,b,c],[b,d,c]])
        approx=trimesh.Trimesh(vertices=verts,faces=tris,process=False)
        approx.export(out/"surface_envelope_GUIDE_ONLY.glb")
    return station_list

def silhouettes(mesh,out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,3,figsize=(15,5),layout="constrained")
    v=mesh.vertices
    for ax,(a,b,title) in zip(axs,[(0,1,"SIDE X-Y"),(0,2,"TOP X-Z"),(2,1,"END Z-Y")]):
        sample=v[::max(1,len(v)//50000)]
        ax.scatter(sample[:,a],sample[:,b],s=.12,alpha=.15,color="gray",rasterized=True)
        bins=np.linspace(v[:,a].min(),v[:,a].max(),160)
        low=np.full(len(bins)-1,np.inf);high=np.full(len(bins)-1,-np.inf)
        ii=np.clip(np.digitize(v[:,a],bins)-1,0,len(low)-1)
        np.minimum.at(low,ii,v[:,b]);np.maximum.at(high,ii,v[:,b])
        good=np.isfinite(low)
        c=(bins[:-1]+bins[1:])*.5
        ax.plot(c[good],low[good],color="tab:blue",linewidth=1)
        ax.plot(c[good],high[good],color="tab:red",linewidth=1)
        ax.set_title(title);ax.set_aspect("equal","box")
    fig.savefig(out/"silhouettes.png",dpi=145);plt.close(fig)

def depth_rays(mesh,out,up_axis=1,grid=20):
    # Exact ray/triangle intersections where the available ray backend supports it.
    up=int(up_axis)
    coords=[x for x in range(3) if x!=up]
    b=mesh.bounds
    sample=np.meshgrid(np.linspace(b[0,coords[0]],b[1,coords[0]],grid),
                       np.linspace(b[0,coords[1]],b[1,coords[1]],grid))
    origins=np.zeros((grid*grid,3),float)
    origins[:,coords[0]]=sample[0].ravel();origins[:,coords[1]]=sample[1].ravel()
    origins[:,up]=b[1,up]+max(mesh.extents)*.1
    direction=np.zeros(3);direction[up]=-1
    dirs=np.tile(direction,(len(origins),1))
    rows=[]
    try:
        points,rays,triangles=mesh.ray.intersects_location(origins,dirs,multiple_hits=True)
        grouped={}
        for point,ix in zip(points,rays): grouped.setdefault(int(ix),[]).append(float(point[up]))
        for i,origin in enumerate(origins):
            hits=sorted(grouped.get(i,[]),reverse=True)
            depth=(hits[0]-hits[1]) if len(hits)>1 else float("nan")
            rows.append((i,origin[coords[0]],origin[coords[1]],len(hits),depth))
        note="Real triangle-ray intersections; first/second-hit gaps need interpretation."
    except Exception as e:
        # Honest fallback: vertex envelope only; never claim it is ray depth.
        note="RAY BACKEND UNAVAILABLE: "+str(e)
        gridxy=np.linspace(0,1,grid)
        for ix in range(grid*grid):rows.append((ix,float(sample[0].ravel()[ix]),float(sample[1].ravel()[ix]),0,float("nan")))
    with open(out/"ray_depth.csv","w",newline="") as fp:
        w=csv.writer(fp);w.writerow(["ray","coord_a","coord_b","hits","first_to_second_surface_distance"]);w.writerows(rows)
    return note

def compare_shapes(a,b,out):
    points_a=trimesh.sample.sample_surface(a,12000)[0]
    points_b=trimesh.sample.sample_surface(b,12000)[0]
    def normal(x,model):
        ext=model.extents.clip(1e-8)
        return (x-model.bounds[0])/ext
    na=normal(points_a,a);nb=normal(points_b,b)
    d1=cKDTree(nb).query(na)[0];d2=cKDTree(na).query(nb)[0]
    result={"samples_each":12000,"aligned_by":"independent normalized axis-aligned bounding boxes",
            "a_to_b_mean":float(d1.mean()),"b_to_a_mean":float(d2.mean()),
            "a_to_b_p95":float(np.quantile(d1,.95)),"b_to_a_p95":float(np.quantile(d2,.95)),
            "limitations":"Sampled nearest surface points, no ICP, alignment visually required"}
    (out/"shape_comparison.json").write_text(json.dumps(result,indent=2))
    return result

def analyze(source,out,reference=None,axis=0,up=1,crease=35):
    out.mkdir(parents=True,exist_ok=True)
    original=source.read_bytes()
    sha=hashlib.sha256(original).hexdigest()
    mesh=load(source)
    vertices=mesh.vertices
    report={"source_file":source.name,"original_sha256":sha,
            "original_preserved":True,"vertices":int(len(vertices)),"triangles":int(len(mesh.faces)),
            "bounds_source_units":np.asarray(mesh.bounds).tolist(),"axis_length":axis,"axis_up":up}
    broad=curvature(mesh,64);fine=curvature(mesh,16)
    write_glb(mesh,broad,"01_curvature_broad.glb",out)
    write_glb(mesh,fine,"02_curvature_fine.glb",out)
    sharp,angles,stats=topology(mesh,crease)
    report["topology"]=stats
    write_glb(mesh,np.clip(sharp/90,0,1),"03_edge_severity.glb",out,"positive")
    orient=vertex_edge_direction(mesh)
    write_glb(mesh,orient,"04_edge_direction.glb",out,"category")
    patch_labels,patch_sizes=components_and_patches(mesh,angles,crease)
    report["surface_patches"]={"patch_count":int(len(patch_sizes)),
                "largest_patch_faces":int(max(patch_sizes)) if len(patch_sizes) else 0,
                "small_patches":int(sum(patch_sizes<10))}
    write_glb(mesh,vertex_labels(mesh,patch_labels),"05_patches.glb",out,"category")
    feature=np.where(sharp>crease,2,np.where(fine>0.12,1,np.where(fine<-.12,3,0)))
    write_glb(mesh,feature,"06_feature_candidates.glb",out,"category")
    report["feature_candidates"]={"sharp_vertex_count":int(np.sum(feature==2)),
        "ridge_vertex_count":int(np.sum(feature==1)),
        "valley_vertex_count":int(np.sum(feature==3))}
    profiles(mesh,out,axis)
    silhouettes(mesh,out)
    report["depth_raycast"]=depth_rays(mesh,out,up)
    if reference:
        ref=load(reference);report["shape_comparison"]=compare_shapes(mesh,ref,out)
    # Structured cross-sections, surface patch descriptors and measured construction
    # deltas for a human modeler or assistant to consume directly (not AI training).
    from modeling_blueprint import build_modeling_packet
    packet = build_modeling_packet(
        mesh=mesh, out=out, original_sha256=sha, source_name=source.name,
        length_axis=axis, up_axis=up, curvature_broad=broad,
        curvature_fine=fine, sharpness=sharp, patch_labels=patch_labels,
        crease_threshold=crease,
        reference_mesh=ref if reference else None,
    )
    report["assistant_modeling_data"] = packet
    report["notes"]=["No input model edits","Features are candidates, not semantic labels",
        "Sections and envelope loft are approximate construction guides",
        "Curvature is a k-nearest-neighbor bending indicator, not CAD curvature"]
    assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
    (out/"geometry_report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({"status":"complete","source":str(source),"out":str(out),"sha256":sha,
         "vertices":report["vertices"],"faces":report["triangles"]},indent=2))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path)
    parser.add_argument("--compare",type=Path)
    parser.add_argument("--out",type=Path,default=Path("geometry-output"))
    parser.add_argument("--length-axis",choices=["x","y","z"],default="x")
    parser.add_argument("--up-axis",choices=["x","y","z"],default="y")
    parser.add_argument("--crease",type=float,default=35)
    parser.add_argument("--demo",action="store_true")
    args=parser.parse_args()
    if args.demo:
        args.out.mkdir(parents=True,exist_ok=True)
        m=trimesh.creation.icosphere(subdivisions=3)
        f=args.out/"demo_untouched.glb";m.export(f);args.input=f
    if not args.input: parser.error("Provide --input or --demo")
    analyze(args.input,args.out,args.compare,["x","y","z"].index(args.length_axis),
            ["x","y","z"].index(args.up_axis),args.crease)
if __name__=="__main__":main()
