# Forge Cycle 10 — actual CC0 text/mesh pairs and role-label review

## Levels of evidence

A large descriptive corpus on its own does not teach procedural modeling.
Assetwright tracks three distinct levels:

1. **Description only:** A publisher caption refers to a cataloged object.
   It does not prove the actual mesh has been inspected.
2. **Verified text/mesh pair:** A Poly Haven source-object ID matches a
   Blender-inspected CC0 mesh with the exact source SHA-256 and measured
   geometry features.
3. **Reviewed component role:** A specific mesh component has an approved
   semantic role, supported by source-matched render or author evidence.

## GitHub training pipeline

Every new Forge study can inspect up to 24 new CC0 models. The source
download remains bounded to 32 MiB per model and downloaded binaries
remain temporary. The pipeline rebuilds the publisher-caption catalog
and joins it with actual inspected geometry by exact ID and file hash.

Artifacts:
- `grounded_pairs/pairs.json`: CC0 captions and actual Blender descriptors
- `grounded_pairs/coverage.json`: verified pair and graph coverage
- `grounded_pairs/review_queue.json`: weak source-name proposals only
- `grounded_pairs/review_report.json`: unverified review tasks
- `caption_mesh_prior/evaluation.json`: model evaluation or refusal
- `caption_mesh_prior/validated_prior.json`: only if 32+ unique examples
  and independent whole-source holdout outperform the baseline by 3%

## Manual role review

The optional review manifest uses schema
`assetwright-reviewed-component-roles-v1`. Every assertion must include
exact source object ID, source model SHA-256, graph component ID,
canonical part role, declared review method, reviewer, and distinct
review-evidence file SHA-256.

An evidence hash is an auditable declaration, not by itself proof
that a review happened. Imported names such as "Engine.001" or
"Wheel.002" are only *weak suggestions*. Generic geometry fragments
and overlapping bounding boxes are not semantic joints.

No third-party part-name proposal automatically becomes a training
label. No description-only Objaverse record silently becomes a mesh
example. Metadata and generated Cap3D captions preserve their separate
ODC-By attribution.

## Verified Cycle 15 results

GitHub Actions run 41365409242 passed 73 offline tests. Of 12 newly
selected official CC0 models, Blender inspected 11 successfully. After
source-hash deduplication, the cumulative dataset contains 35 matched
publisher-description/actual-mesh examples; 31 have multi-part geometry
graphs and 11 recent pairs have full-model three-view Blender previews.

The first actual-caption-to-Blender-geometry descriptor model passed
its 26-model training / 9-model independent holdout test:

- Mean squared error baseline: 0.04035088
- Mean squared error trained: 0.03215817
- Relative improvement: 20.304%

This model learns only eight coarse numeric source-mesh measurements.
It does **not** yet learn editable body topology, true mechanical joining,
or realistic arbitrary text-to-mesh generation. It is not deployed to Android.

One source-name-derived semantic proposal appeared: a highlighted
"body" node on the CC0 water manhole cover. Visual inspection revealed
that the highlighted piece was a perimeter ring. As a transferable
vehicle construction label, "body" was rejected, with the original mesh
hash and preview image SHA-256 recorded in
`training/reviews/role_dispositions.json`. Future queues exclude that
exact false-positive node and preserve the remaining unverified candidates.
No third-party semantic component labels have yet been approved.

The detailed study and PNG previews are retained under the GitHub Actions
artifact named `forge-cc0-shape-study` for run 41365409242.

## Remaining work

Source-specific multiview rendering and actual evidence-based labeling
must precede any released part-role model. The current stage measures
eight coarse geometry features; it cannot yet reconstruct free-form
contours, topology or an editable assembly operation from arbitrary text.

The Android application remains unchanged during this research cycle.
