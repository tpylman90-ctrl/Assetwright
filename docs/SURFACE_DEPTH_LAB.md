# Assetwright Surface Patch & True Ray Depth Lab (v0.2)

## Purpose

Measure and explain how a high-detail GLB's visible surfaces are organized,
where adjacent faces form smooth transitions versus hard creases, and where
orthographic rays intersect multiple layers. Use the evidence to reconstruct
one engineered assembly at a time.

**The input GLB is never modified.** Separate derivative GLBs are intended
for inspection, not game-ready reconstruction.

## Run on GitHub

Open Actions → **Assetwright Geometry Lab - full geometry scan** → Run workflow.
Provide `source_glb` (a GLB already committed to the repository) or leave
empty for the synthetic smoke test. The workflow now runs:
- Original slicer/curvature/feature tools
- `surface_depth_lab.py` on supplied GLB
- A synthetic cavity-depth regression test, which must measure a 0.40-unit
  known setback within ±0.03 units

The workflow produces an artifact `assetwright-geometry-scan` containing:
`surface_depth/surface_regions_30deg.glb`,
`surface_depth/side_region_candidate_cutaway.glb`,
`surface_depth/depth_ray_maps.png`,
`surface_depth/raycast_samples.csv`, and
`surface_depth/surface_depth_report.json`.
Outputs are independent of and never overwrite the original model.

## Run locally

```bash
python -m pip install numpy scipy trimesh matplotlib
python tools/geometry_lab/surface_depth_lab.py --input original.glb \
  --out surface-scan --ray-axis z --enter-side positive \
  --roi 0.08 0.92 0.1 0.9 --grid 48 36
python tools/geometry_lab/surface_depth_lab.py --self-test --out self-test
```

For a compressed GLB, first run the separate Meshopt decoder
`tools/geometry_lab/unpack_meshopt.mjs` to make an uncompressed diagnostic copy.

## What measurements mean

**Patch segmentation:** Three region-growing scans at dihedral thresholds
15°, 30°, and 45°. Adjacency is based on face indexing, not semantic parts.
Surface regions are candidates, not verified bumpers, intakes or doors.
Segmentations can produce many tiny regions on reconstructed meshes.

**True first-hit ray depth:** From the + or - face of the selected bounding
axis, the scanner computes exact intersections with the source triangles.
This is not a vertex or depth-envelope approximation.

**First-to-second surface separation:** The distance between the first and
second distinct ray hits. This may be the shell thickness or an internal
layer, not necessarily an intake cavity.

**Local relative relief:** First-hit depth minus the local 15th-percentile
near-surface baseline. It can indicate an inset region only if the scan
includes a reliable adjacent rim, and it is measured in GLB coordinate units.

**Side-region GLB:** Triangles selected by their projected face centroid
within the ROI, not a Boolean cut or verified semantic segmentation.
The colored patch GLB retains the original triangles for Vantage-sized
meshes. Neither GLB is a replacement for the source.

## Android inspection

Download the derived `surface_regions_30deg.glb` or
`side_region_candidate_cutaway.glb`, import into Assetwright Geometry Lab
v0.7.3+, and select **10. Imported colored patch GLB** to visualize the
`COLOR_0` annotation in the native diagnostic wireframe.

An external 3D GLB viewer can also show the same color-coded geometry.
The phone's Geometry Lab still does not perform this full raycast/segmentation
analysis itself; its native controls are inspection and lightweight diagnostics.

## Using the data to build better models

1. Keep the original untouched, and inspect its five camera views.
2. Focus on one ROI (such as a side intake) and inspect the patch-boundary GLB.
3. Locate the actual outer rim and backing surface visually.
4. Scan that localized region, record its ray depths and profile sections.
5. Rebuild a separate clean quad/spline/body panel with real recess geometry.
6. Check the edited part against the source with identical camera framing
   and quantitative shape-distance analysis.
7. Iterate; do not confuse triangle count or raw patch count with fidelity.

**Cautions:** Raycast sampling misses features between rays and may observe
unintended internal geometry. Meshopt decompression is separate from editing.
GLB units can be normalized. Signed distance, robust ICP registration,
automatic semantic part naming and CAD-quality patch reconstruction remain
future work.
