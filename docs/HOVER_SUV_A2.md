# Hover Race SUV A2 — surface-rebuild review

The A1 review showed a recognizably SUV-shaped vehicle but severely faceted bodywork, block-like cockpit parts, disconnected-looking fenders and an oversized rectangular rear spoiler.

**A2 is a geometry study, not a final vehicle.** The geometry is generated with a deterministic, open Python surface-loft generator, and exports to GLB for import and refinement in Blender/Godot. It is not evidence that the source was sculpted in Blender.

## Key changes

- Interpolated longitudinal vehicle body with 82 continuous cross sections based on shape control stations, preserving the broad front fender and rising rear haunch.
- Increased shape density without indiscriminate triangulation; independent control over fender bulges and sill taper.
- Curved front and rear glass, roof, side glass, A/B/C structural pillars and molded door belt line.
- Recessed rocker and side intake; rear haunch shoulders flow across the side profile.
- Four angular, layered hover boots. Upper fender caps are tucked closer to the vehicle rather than floating at the outermost edge.
- A slimmer roof-spoiler surface, redesigned front/rear fascia and separate fitted cockpit blockout.
- Four actual-geometry offscreen views: front three-quarter, rear three-quarter, strict side, and top.

## Reproduction

```bash
python -m pip install numpy scipy trimesh Pillow vtk
ASSETWRIGHT_OUTPUT_DIR=generated/hover_suv_a2 \
  python tools/geometry/generate_hover_suv_a2.py
```

The [GitHub Actions workflow](../.github/workflows/hover-suv-a2.yml) builds the same export and produces a short-lived artifact for review.

## Validated local study

- 20,088 actual exported GLB triangles across 107 independent mesh assemblies.
- GLB re-import and triangle count checked through trimesh.
- The GLB has not yet been verified in Godot, and the CI workflow has not been confirmed successful.
- This mesh is **neither UV-baked nor rigged**. Glazing is presented as tinted opaque in the GLB prototype. High-quality reflection-line checks and genuine fitted Class-A style panels remain future work.
- Additional visual review is essential: the form is improved but still reads softer and more rounded than the supplied A1 SUV reference, especially around the hover pods.

### Reference

The approved concept board is preserved at Assetwright Library `/Assetwright/References/Hover_Race_SUV_Concept_A1.png`.

This A2 source is separate from A1 and does not overwrite or change Parallax/Mantis or SceneForge.
