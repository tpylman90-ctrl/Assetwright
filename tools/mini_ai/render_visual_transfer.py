"""Render four views of original AssetWright native GLBs, with exact hash proof.

Blender: blender -b --factory-startup --disable-autoexec --python
  tools/mini_ai/render_visual_transfer.py -- <native-glb-dir> <output-dir>
No teacher meshes or generated external assets are involved.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import sys

def sha256(path:Path)->str:
    digest=hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda:file.read(65536),b""):
            digest.update(block)
    return digest.hexdigest()

def original_recipe(glb_path:Path,target:dict)->dict:
    from visual_transfer_student import PARAMS,normalize_parameters
    if target.get("schema")!="assetwright-generated-vehicle-target-v1":
        raise ValueError("Wrong generator target schema")
    if target.get("original_procedural_asset") is not True or target.get("expected_engine")!="android-native-MiniGeometry":
        raise ValueError("Rejecting non-native or untrusted source")
    if target.get("source_glb_sha256")!=sha256(glb_path):
        raise ValueError("GLB content hash does not match exact construction recipe")
    parameters=target.get("parameters")
    normalize_parameters(parameters)
    if target.get("case")!=glb_path.stem.split("__")[0]:
        raise ValueError("Mismatched source group")
    return {"sample_id":glb_path.stem,"source_group":target["case"],
            "source_glb_sha256":target["source_glb_sha256"],
            "original_procedural_asset":True,
            "expected_engine":"android-native-MiniGeometry",
            "prompt":target["prompt"],"parameters":{k:parameters[k] for k in PARAMS}}

def render(glb_dir:Path,out:Path)->dict:
    import bpy
    from mathutils import Vector
    from visual_transfer_student import MANIFEST
    glbs=sorted(glb_dir.glob("*.glb"))
    if not 1<=len(glbs)<=256:
        raise ValueError("Expected 1..256 original GLBs")
    out.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=224
    scene.render.resolution_y=224
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="SINGLE"
    scene.display.shading.single_color=(.67,.73,.78)
    scene.display.shading.show_cavity=True
    views={"front":(0,-2.8,.7),"side":(2.8,0,.7),
           "top":(.03,-.03,3),"three_quarter":(2.,-2.5,1.4)}
    records=[]
    for path in glbs:
        sidecar=path.with_suffix(".json")
        if not sidecar.is_file():
            raise ValueError("Missing native source sidecar for "+path.name)
        target=json.loads(sidecar.read_text())
        record=original_recipe(path,target)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        # Only our native GLB subset is allowed. Parse indexed triangle buffers
        # using our audited standard-library reader rather than Blender's glTF
        # importer, which can require numpy missing from free CI Blender images.
        from generated_glb_critic import _read_glb, _accessor
        gltf, binary, inspected_sha = _read_glb(path)
        if inspected_sha != record["source_glb_sha256"]:
            raise ValueError("Native mesh changed after provenance check")
        if any(any(key in node for key in ("matrix", "rotation", "scale", "translation"))
               for node in gltf.get("nodes", [])):
            raise ValueError("Unsupported transformed source node")
        for mesh_index, native_mesh in enumerate(gltf.get("meshes", [])):
            for part_index, primitive in enumerate(native_mesh.get("primitives", [])):
                positions = _accessor(gltf, binary,
                    primitive["attributes"]["POSITION"], "positions")
                indices = _accessor(gltf, binary, primitive["indices"], "indices")
                if len(indices) % 3:
                    raise ValueError("Nontriangular native primitive")
                faces = [tuple(indices[i:i+3]) for i in range(0, len(indices), 3)]
                mesh_data = bpy.data.meshes.new(f"AWNative_{mesh_index}_{part_index}")
                mesh_data.from_pydata(positions, [], faces)
                mesh_data.update()
                obj = bpy.data.objects.new(mesh_data.name, mesh_data)
                scene.collection.objects.link(obj)
        meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
        if not meshes: raise ValueError("No mesh in "+path.name)
        points=[o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
        mins=[min(v[i] for v in points) for i in range(3)]
        maxs=[max(v[i] for v in points) for i in range(3)]
        center=Vector([(a+b)/2 for a,b in zip(mins,maxs)])
        extent=max(b-a for a,b in zip(mins,maxs))
        if not math.isfinite(extent) or extent<.01:
            raise ValueError("Degenerate object bounds")
        camera_data=bpy.data.cameras.new("AssetWrightFixedReview")
        camera=bpy.data.objects.new("AssetWrightFixedReview",camera_data)
        scene.collection.objects.link(camera)
        camera.data.type="ORTHO"
        camera.data.ortho_scale=extent*1.75
        camera.data.clip_end=max(100,extent*10)
        scene.camera=camera
        record["view_sha256"]={}
        record["view_files"]={}
        for name,direction in views.items():
            camera.location=center+Vector(direction).normalized()*extent*2.5
            camera.rotation_euler=(center-camera.location).to_track_quat("-Z","Y").to_euler()
            filepath=out/(path.stem+"__"+name+".png")
            scene.render.filepath=str(filepath)
            bpy.ops.render.render(write_still=True)
            record["view_sha256"][name]=sha256(filepath)
            record["view_files"][name]=filepath.name
        records.append(record)
    output={"schema":MANIFEST,"source":"original android-native MiniGeometry exports",
            "evidence":"SHA-256 of each GLB and each render",
            "image_encoder_used":False,"examples":records}
    (out/"manifest.json").write_text(json.dumps(output,indent=2)+"\n")
    print("ASSETWRIGHT_MULTIVIEW_CREATED",len(records))
    return output

def main()->None:
    if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=2:
        raise ValueError("Expected -- <native-glb-dir> <output-dir>")
    args=sys.argv[sys.argv.index("--")+1:]
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    render(Path(args[0]),Path(args[1]))

if __name__=="__main__":
    main()
