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


## V2: sculptural side-body pass

The first model's frontal and three-quarter shapes were approved, but the strict side view
read as a largely featureless capsule. The V2 generator addresses that by changing the
actual load-bearing shoulder geometry rather than relying on a collection of added rods:

- **Continuous formed rocker trench:** Sixteen-point shoulder control sections cut a
  concave lower relief into both flanks; a dark recessed strip reads in side elevation.
  The outer lip carries a separately sculpted, swept composite undercut aero blade.
- **Deeper fitted side intakes:** A long tapered, closed Boolean cutter replaces the
  old rectangular side air pocket. Each opening has a dark recessed plenum, angled
  splitters, a formed eyebrow and a fitted lower sill, with a violet field core inside.
- **Loaded rear quarter:** Revised longitudinal control sections widen the aft shoulder
  around the rear lift machinery and raise the lower tail for a more dynamic taper.
  A local crest and a fitted rear-haunch fairing create shoulder-to-tail flow.
- **More purposeful side lighting:** The narrow violet filament tracks the sculpted
  rocker lip rather than tracing a straight line on the broad side wall.

This pass preserves the original four through-body lift ducts, twin rear drives,
two-seat canopy and clean porcelain/petrol material language. It deliberately puts
silhouette and surface quality ahead of tiny fasteners.

**Validation pending:** A successful source commit is not evidence that the Blender
workflow passed or that the new side profile is attractive. Check the newly generated
side, hero three-quarter, top and rear three-quarter renders, then inspect whether the
recesses are open and the aft haunch blends properly. Geometry, LOD, export and Godot
readiness must be verified from the new workflow outputs.
