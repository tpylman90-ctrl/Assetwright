#!/usr/bin/env python3
"""Assetwright Surface Patch + True Ray Depth Lab.

Non-destructive mesh analysis. Uses actual face adjacency and ray/triangle
intersections. Patch labels are geometric candidates, NOT named body panels.
Relief relative to an estimated rim is NOT guaranteed physical cavity depth.
Requires numpy, scipy, trimesh, matplotlib.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def load_model(path):
    obj=trimesh.load(str(path),force="scene",process=False)
    mesh=obj.to_geometry() if isinstance(obj,trimesh.Scene) else obj
    if not isinstance(mesh,trimesh.Trimesh) or len(mesh.faces)==0:
        raise ValueError("No triangle mesh available; decompress Meshopt GLB first.")
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("Non-finite vertex coordinates")
    return mesh


def surface_regions(mesh,angle=30):
    adjacent=mesh.face_adjacency
    degrees=np.rad2deg(mesh.face_adjacency_angles)
    safe=adjacent[degrees <= angle]
    n=len(mesh.faces)
    a=np.r_[safe[:,0],safe[:,1],np.arange(n)]
    b=np.r_[safe[:,1],safe[:,0],np.arange(n)]
    mat=coo_matrix((np.ones(len(a),dtype=np.uint8),(a,b)),shape=(n,n)).tocsr()
    count,labels=connected_components(mat,directed=False)
    areas=np.bincount(labels,weights=mesh.area_faces,minlength=count)
    sizes=np.bincount(labels,minlength=count)
    return labels,areas,sizes,np.argsort(areas)[::-1]


def patch_summary(mesh,labels,areas,sizes,order,limit=90):
    centers=mesh.triangles_center
    normals=mesh.face_normals
    face_areas=mesh.area_faces
    out=[]
    for label in order[:limit]:
        indices=np.flatnonzero(labels==label)
        if len(indices)==0 or areas[label]<=0:continue
        weighted=face_areas[indices]/face_areas[indices].sum()
        center=(centers[indices]*weighted[:,None]).sum(axis=0)
        normal=(normals[indices]*weighted[:,None]).sum(axis=0)
        normal/=max(np.linalg.norm(normal),1e-9)
        positions=mesh.vertices[np.unique(mesh.faces[indices].ravel())]
        out.append({
            "patch_id":int(label), "triangle_count":int(sizes[label]),
            "surface_area_source_units_squared":float(areas[label]),
            "center":center.tolist(), "mean_normal":normal.tolist(),
            "bounds":np.stack([positions.min(0),positions.max(0)]).tolist(),
            "semantic_label":"unknown",
            "caution":"Geometric connected region; not a confirmed hood, intake, or fender"
        })
    return out


def export_patch_glb(mesh,labels,areas,path,max_faces=1000000):
    # Separate derivative; never edit mesh or input. Face colors make patches
    # inspectable in generic Android GLB viewers.
    step=max(1,int(math.ceil(len(mesh.faces)/max_faces)))
    chosen=np.arange(0,len(mesh.faces),step)
    view=mesh.submesh([chosen],append=True,repair=False)
    labels_used=labels[chosen].astype(np.uint64)
    top=np.argsort(areas)[-35:]
    bright=np.isin(labels_used,top)
    colors=np.tile(np.array([78,85,96,255],dtype=np.uint8),(len(chosen),1))
    k=labels_used[bright]
    colors[bright,0]=(65+(k*79)%175).astype(np.uint8)
    colors[bright,1]=(85+(k*113)%155).astype(np.uint8)
    colors[bright,2]=(105+(k*57)%140).astype(np.uint8)
    view.visual=trimesh.visual.ColorVisuals(mesh=view,face_colors=colors)
    view.export(str(path))
    return {"source_faces":int(len(mesh.faces)),"included_faces":int(len(chosen)),
            "decimation":"full geometry retained for Vantage-scale meshes; face sampling only above maximum"}



def export_region_cutaway(mesh,labels,axis,roi,out):
    """Diagnostic face-centroid-selected region GLB; not Boolean clipping."""
    other=[d for d in range(3) if d!=axis]
    centers=mesh.triangles_center
    b=mesh.bounds
    lo=b[0,other]
    length=(b[1,other]-lo).clip(1e-9)
    u=(centers[:,other[0]]-lo[0])/length[0]
    v=(centers[:,other[1]]-lo[1])/length[1]
    chosen=np.flatnonzero((u>=roi[0])&(u<=roi[1])&(v>=roi[2])&(v<=roi[3]))
    if len(chosen)==0:
        return {"faces":0,"warning":"No faces inside projected scan ROI"}
    partial=mesh.submesh([chosen],append=True,repair=False)
    labels_chosen=labels[chosen].astype(np.uint64)
    colors=np.column_stack([
        70+(labels_chosen*79)%175,
        85+(labels_chosen*113)%155,
        105+(labels_chosen*57)%140,
        np.full(len(chosen),255)
    ]).astype(np.uint8)
    partial.visual=trimesh.visual.ColorVisuals(mesh=partial,face_colors=colors)
    partial.export(str(out))
    return {"faces":int(len(chosen)),"source_faces":int(len(mesh.faces)),
            "output":out.name,"warning":"Projected ROI face selection; not exact geometric clipping or semantic intake recognition"}


def true_axis_rays(mesh,axis=2,enter_side="positive",roi=(.08,.92,.1,.9),grid=(48,36)):
    """Measure exact ordered triangle intersections along axis-parallel rays.

    Projection-test acceleration is based on triangle 2D bounding boxes,
    followed by exact barycentric interpolation of the intersection point.
    """
    other=[d for d in range(3) if d!=axis]
    box=mesh.bounds
    minuv=box[0,other];width=(box[1,other]-minuv).clip(1e-10)
    nu,nv=grid
    u=np.linspace(roi[0],roi[1],nu)
    v=np.linspace(roi[2],roi[3],nv)
    U,V=np.meshgrid(u,v)
    query=np.stack([minuv[0]+U.ravel()*width[0],
                    minuv[1]+V.ravel()*width[1]],axis=1)
    triangles=mesh.vertices[mesh.faces]
    a=triangles[:,0][:,other]
    b=triangles[:,1][:,other]
    c=triangles[:,2][:,other]
    lower=np.minimum(np.minimum(a,b),c)
    upper=np.maximum(np.maximum(a,b),c)
    e=b-a
    f=c-a
    det=e[:,0]*f[:,1]-e[:,1]*f[:,0]
    good=np.abs(det)>1e-14
    recip=np.zeros_like(det)
    recip[good]=1./det[good]
    axis_a=triangles[:,0,axis]
    axis_b=triangles[:,1,axis]-axis_a
    axis_c=triangles[:,2,axis]-axis_a
    first=np.full(len(query),np.nan)
    second=np.full(len(query),np.nan)
    n_hits=np.zeros(len(query),dtype=np.int32)
    tol=max(1e-7,mesh.extents[axis]*1e-5)
    for idx,p in enumerate(query):
        candidates=np.flatnonzero(good&(lower[:,0]<=p[0])&
          (upper[:,0]>=p[0])&(lower[:,1]<=p[1])&(upper[:,1]>=p[1]))
        if len(candidates)==0:continue
        delta=p-a[candidates]
        w=(delta[:,0]*f[candidates,1]-delta[:,1]*f[candidates,0])*recip[candidates]
        t=(e[candidates,0]*delta[:,1]-e[candidates,1]*delta[:,0])*recip[candidates]
        inside=(w>=-1e-7)&(t>=-1e-7)&(w+t<=1+1e-7)
        ix=candidates[inside]
        hits=axis_a[ix]+w[inside]*axis_b[ix]+t[inside]*axis_c[ix]
        hits=np.sort(hits)
        if enter_side=="positive":hits=hits[::-1]
        if len(hits):
            hits=hits[np.r_[True,np.abs(np.diff(hits))>tol]]
            n_hits[idx]=len(hits)
            first[idx]=hits[0]
            if len(hits)>1:second[idx]=hits[1]
    # First-hit depths are always measured inward from the entry bounding plane.
    depth=(box[1,axis]-first) if enter_side=="positive" else (first-box[0,axis])
    gap=np.abs(first-second)
    good_depth=depth[np.isfinite(depth)]
    rim=float(np.percentile(good_depth,15)) if len(good_depth) else float("nan")
    relief=depth-rim
    return {
       "axis":axis,"enter_side":enter_side,"roi":list(roi),"grid":list(grid),
       "projection_axes":other,"first_hit_depth":depth.reshape(nv,nu),
       "first_second_gap":gap.reshape(nv,nu),
       "relative_relief":relief.reshape(nv,nu),
       "n_intersections":n_hits.reshape(nv,nu),"rim_baseline":rim,
       "hit_rays":int(np.count_nonzero(n_hits)),
       "multi_surface_rays":int(np.count_nonzero(n_hits>1)),
       "total_rays":int(len(query))}


def ray_exports(ray,out):
    d=ray["first_hit_depth"];g=ray["first_second_gap"]
    r=ray["relative_relief"];n=ray["n_intersections"]
    with (out/"raycast_samples.csv").open("w",newline="") as stream:
        writer=csv.writer(stream)
        writer.writerow(["v","u","first_hit_depth","first_second_hit_gap",
                         "relative_relief","intersection_count"])
        for i in range(d.shape[0]):
            for j in range(d.shape[1]):
                writer.writerow([i,j,d[i,j],g[i,j],r[i,j],n[i,j]])
    fig,axs=plt.subplots(1,3,figsize=(14,5),layout="constrained")
    for ax,x,title in zip(axs,[d,r,g],[
        "Actual first ray hit","Relief vs estimated local rim",
        "First-to-second surface separation"]):
        layer=ax.imshow(x,origin="lower",cmap="viridis",aspect="auto",interpolation="nearest")
        fig.colorbar(layer,ax=ax);ax.set_title(title)
        ax.set_xlabel("Scan U");ax.set_ylabel("Scan V")
    fig.savefig(out/"depth_ray_maps.png",dpi=150)
    plt.close(fig)
    def median(x):
        return float(np.nanmedian(x)) if np.isfinite(x).any() else None
    return {"rays_total":ray["total_rays"],"rays_hit":ray["hit_rays"],
            "multiple_layers":ray["multi_surface_rays"],
            "first_hit_depth_median":median(d),
            "first_to_second_gap_median":median(g),
            "local_relief_median":median(r),
            "local_rim_baseline":ray["rim_baseline"],
            "axis":ray["axis"],"enter_side":ray["enter_side"],
            "roi":ray["roi"],"grid":ray["grid"],
            "warning":"Relative relief uses estimated rim; not confirmed cavity depth."}


def analyze(source,out,axis=2,side="positive",roi=(.08,.92,.1,.90),grid=(48,36)):
    out.mkdir(parents=True,exist_ok=True)
    original_digest=hashlib.sha256(source.read_bytes()).hexdigest()
    mesh=load_model(source)
    report={"schema":"assetwright.surface_depth_scan.v1",
       "source":source.name,"source_sha256":original_digest,
       "input_preserved":True,"vertices":int(len(mesh.vertices)),
       "triangles":int(len(mesh.faces)),
       "bounds_source_units":mesh.bounds.tolist(),
       "unit_note":"GLB values may be normalized; do not assume metres.",
       "patches":{}}
    for angle in (15,30,45):
        labels,areas,sizes,order=surface_regions(mesh,angle)
        report["patches"][str(angle)]={
             "region_count":int(len(areas)),
             "over_0.1pct_total_area":int(np.count_nonzero(areas>=mesh.area*0.001)),
             "largest_regions":patch_summary(mesh,labels,areas,sizes,order)}
        if angle==30:
            report["derived_patch_glb"]=export_patch_glb(
                mesh,labels,areas,out/"surface_regions_30deg.glb")
            report["side_region_cutaway"]=export_region_cutaway(
                mesh,labels,axis,roi,out/"side_region_candidate_cutaway.glb")
    ray=true_axis_rays(mesh,axis=axis,enter_side=side,roi=roi,grid=grid)
    report["raycast"]=ray_exports(ray,out)
    report["method_notes"]=[
        "Patches are adjacent face groups separated by face-normal bends.",
        "Patches are NOT reliable semantic vehicle body-panel labels.",
        "Ray intersections are exact barycentric mesh-plane intersections.",
        "First/second hit separation may represent shell thickness, not intake depth.",
        "The difference from the 15th-percentile local rim is a relief proxy only.",
        "The source mesh was not edited, moved, remeshed or overwritten."]
    assert hashlib.sha256(source.read_bytes()).hexdigest()==original_digest
    (out/"surface_depth_report.json").write_text(json.dumps(report,indent=2))
    (out/"INTERPRETATION.md").write_text(
       "# Assetwright Surface + Depth Scan\n\n"
       "These outputs are measured geometry, **not** AI-guessed shape labels.\n"
       "Inspect \`surface_regions_30deg.glb\` on Android, then compare the depth map "
       "against visible intakes and structural layers. All coordinates are in "
       "source GLB units. The original file is preserved by SHA256.\n")
    return report


def synthetic_test(out):
    # Recessed panel with 0.4 source-unit offset between the outer rim and back wall.
    blocks=[]
    for x,y,z,sx,sy,sz in (
        (-.4,0,.4,.2,1,.035),(.4,0,.4,.2,1,.035),
        (0,.4,.4,.6,.2,.035),(0,-.4,.4,.6,.2,.035),
        (0,0,0,.6,.6,.035)):
        m=trimesh.creation.box(extents=(sx,sy,sz))
        m.apply_translation((x,y,z));blocks.append(m)
    mesh=trimesh.util.concatenate(blocks)
    ray=true_axis_rays(mesh,axis=2,enter_side="positive",roi=(0,1,0,1),grid=(41,41))
    center=float(ray["relative_relief"][20,20])
    rim=float(ray["relative_relief"][20,3])
    assert abs(center-.4)<.03,(center,rim)
    assert abs(rim)<.05,(center,rim)
    result={"status":"passed","known_recess_units":.4,
            "measured_relative_recess_units":center,"rim_relief_units":rim}
    out.mkdir(parents=True,exist_ok=True)
    (out/"synthetic_depth_test.json").write_text(json.dumps(result,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path)
    parser.add_argument("--out",type=Path,default=Path("surface-scan-results"))
    parser.add_argument("--ray-axis",choices=("x","y","z"),default="z")
    parser.add_argument("--enter-side",choices=("positive","negative"),default="positive")
    parser.add_argument("--roi",nargs=4,type=float,default=(.08,.92,.1,.9))
    parser.add_argument("--grid",nargs=2,type=int,default=(48,36))
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        print(json.dumps(synthetic_test(args.out),indent=2))
    else:
        if not args.input:parser.error("--input GLB is required except for --self-test")
        result=analyze(args.input,args.out,axis="xyz".index(args.ray_axis),
            side=args.enter_side,roi=tuple(args.roi),grid=tuple(args.grid))
        print(json.dumps({"status":"passed","triangles":result["triangles"],
           "regions_30deg":result["patches"]["30"]["region_count"],
           "rays_hit":result["raycast"]["rays_hit"]},indent=2))


if __name__=="__main__":
    main()
