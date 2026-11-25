# Assetwright Geometry Lab — Android v0.7.0

Geometry Lab is a separate **native Android activity** in Assetwright, launched from the home screen using **OPEN GEOMETRY LAB • IMPORT GLB**. The existing on-device Mini AI generator and training UI are preserved.

## What runs on the phone

1. **Slicer** — actual triangle/plane intersections. Change X/Y/Z and fraction, export the segments as CSV.
2. **Curvature** — signed graph-Laplacian bending indicator over the mesh's original triangulation, displayed by color. Not CAD principal/Gaussian curvature.
3. **Edge flow / creases** — candidate sharp edges measured from adjacent triangle face-normal angles; displayed as per-vertex severity.
4. **Layer separator** — connected component island coloring. Not automatic semantic labels and does not currently export physically separated objects.
5. **Shape difference** — load a second GLB, overlay registered-by-bounds sampled vertices, and report approximate normalized two-way nearest-vertex discrepancy. Not a precise Hausdorff distance or ICP alignment.
6. **Surface reconstruction** — sampled cross-sectional contours and measured envelope guides available for export; not a production-quality quad retopology system.
7. **Recess/depth inspector** — vertical maximum/minimum geometry-envelope map. It is a useful thickness proxy but **not yet actual cavity raycasting**, so cannot prove how deep an open intake goes.
8. **Silhouettes** — front, top and side 2D projection envelopes in a single view.
9. **Feature detector** — heuristic candidate ridges, concave valleys, abrupt edges and mesh islands, without learned semantic segmentation.

The app exports a section/profile CSV, full per-vertex geometry CSV, PNG inspection images and a diagnostics report. All imports are read-only via Android's document picker; saved analysis files are separate documents.

## Current limits (important)

- The native engine handles **uncompressed binary glTF 2.0 triangle meshes** with embedded binary data. A maximum of 650,000 combined vertices and 3 million indices protects phone memory.
- `EXT_meshopt_compression` and `KHR_draco_mesh_compression` need conversion to uncompressed GLB before native import. Vantage from Tripo uses Meshopt. Use the Python/Node Geometry Lab tool on desktop or GitHub to decode it without altering the original.
- The current parser combines mesh primitives but does not yet apply parent/node transform matrices or GPU skinning/morph weights. Geometry with non-identity node transforms may appear incorrectly aligned.
- Connected mesh islands use vertex-index connectivity and may treat UV-split or duplicated seam vertices as disconnected. They are not a reliable semantic part count.
- Heavy high-density scans run asynchronously; previews decimate drawing only and do **not** modify geometry.
- Reference alignment is bounding-box normalization, not best-fit rigid registration. Verify model orientation manually before using distance measurements.
- Mesh quality, contours, and curvature do not automatically produce production-grade 3D models. The original-vs-edited workflow still requires a separate explicit edit pass.

## Build

The existing `.github/workflows/android.yml` continues building the main application. The dedicated `.github/workflows/geometry-lab-apk.yml` builds and tests Android v0.7.0, uploads a debug APK, and publishes a direct GitHub Release APK, choosing the persistent signed release when signing secrets are configured.

No user data is sent off device by the native Geometry Lab.

## Next advanced geometry milestones

Implement genuine cavity raycasting/BVH; connected semantic patch grouping with normal/curvature-aware adjacency; retopologized smooth surface fitting; robust shape registration (ICP) and signed nearest-surface distances; native Meshopt GLB decompression; high-quality GLB vertex-color analysis export; and Android 3D solid-shaded preview. These are not represented as completed in v0.7.0.
