# Parallax / 01

An original two-seat hover coupe designed by Forge without a concept sheet or reference image. This is a separate Assetwright experiment; the Mantis generator and saved Mantis v10 package remain independent.

## Design

Porcelain titanium shoulders flow around a continuous smoked sapphire cockpit. Four vertical lift ducts pass through the body and belly. Curved stator fans, violet field rings, recessed side intakes, swept split tail fins and two flattened oval rear drive ports supply functional depth. A midnight petrol keel and narrow ice-white/amber lighting frame the clean shell. The cabin contains two fitted seats, a driver yoke and a compact dashboard.

The main body uses quad control surfaces, selective subdivision and Boolean apertures. Separate glazing, seals, machinery and trim remain editable. Portable glTF PBR factors carry color, roughness, metallic, alpha and emission. UVs are smart-projected; high-to-low normal and AO baking are not implemented.

## Build and review

Run the **Parallax 01 original hover coupe** GitHub Actions workflow or push a change to `tools/blender/generate_parallax.py`. The hosted Blender build writes an editable `.blend`, full-detail GLB, two LOD GLBs, a collision GLB, eight model renders and a JSON record. Artifacts are retained for three days; user-facing review releases are saved separately.

Local fast shape review:

```sh
blender --background --factory-startup --python-exit-code 1 \
  --python tools/blender/generate_parallax.py \
  -- --output-dir generated/parallax-shape --shape-check
```

The full build caps LOD0 at 120,000 triangles, LOD1 at 45,000 and LOD2 at 20,000. It evaluates modifiers before reducing LODs. Exported GLB counts must match the record. Studio geometry is excluded. Front three-quarter, front, side, rear three-quarter, rear, top, cockpit and chase views show the actual procedural mesh.

Blender coordinates are nose −Y, rear +Y and up +Z. This is a static asset: Godot driving, LOD-transition behavior, animations and high-to-low baking have not been validated. The JSON record preserves the original prompt and negative prompt; it is not an automatic ML training run.
