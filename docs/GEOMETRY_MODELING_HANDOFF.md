# Assetwright Geometry Lab — Geometry-to-Modeling Handoff

## Goal

Use actual geometry evidence from detailed reference GLBs (e.g. Tripo Vantage) to
build original, editable models of comparable **form quality**. The target is
shape reasoning and controlled reconstruction, not copying irregular triangles,
or assuming that denser meshes automatically look more professional.

## Two data paths

### Android: one-tap export for a ChatGPT session

Open **Geometry Lab** in Assetwright, import a GLB, set the correct longitudinal
slice axis, then tap **EXPORT MODELING DATA • JSON FOR CHATGPT**.
This exports `assetwright_modeling_packet.json` through the Android document
picker and leaves the original GLB unchanged. The file includes:

- Source bounds/overall dimensions and vertex/triangle counts
- 15 measured stations with sample triangle-plane intersections and extents
- Vertex-envelope samples for side/top/end projections
- Curvature and crease histograms, and index-connected island count
- Optional approximate reference-to-candidate vertex-distance statistics
- Explicit limitations and suggested modeling order

Upload that JSON here with a reference image or the original GLB when
a closer shape reconstruction is needed. A ChatGPT assistant cannot automatically
see the contents of Android's local storage; the JSON or a GitHub scan artifact
must be shared through the conversation or an accessible connected repository.

### GitHub: full-resolution reference scan

Run the `Assetwright Geometry Lab - full geometry scan` workflow against a
repository GLB. Meshopt GLBs are decoded into a **new** temporary file; the
original source SHA-256 is recorded and verified. The workflow saves an
`assetwright-geometry-scan` artifact (retained for 21 days).

Important files inside:

- `modeling_blueprint.json`: measured 28-station radial profiles (48 bins
  each), 100-bin silhouette envelopes, broad/fine curvature diagnostics,
  candidate patch area/normal/centroid/bounds, and spatial complexity regions
- `ASSISTANT_GEOMETRY_BRIEF.md`: concise machine/human-readable interpretation
  instructions and warnings
- `construction_deltas.json` (only when `--compare` supplied): section-wise
  cross-section width/height differences, no automatic registration
- `sections.png`, `silhouettes.png`, and diagnostic colored GLBs: cross-check
  numeric evidence against visible shapes
- `geometry_report.json`: topology counts, boundaries, curvature, ray-probe
  availability, and original SHA-256

Artifacts are ephemeral; preserve needed JSON in your own workspace if you
plan to compare across long-term iterations. Since this is currently a public
repository, avoid committing private or licensed reference models without
permission.

## How the assistant should use the data

1. **Inspect first.** Preserve the reference and make a consistent 5-view
   image set plus the numerical geometry report.
2. **Identify primary forms.** Extract outline stations and side/top/end
   envelopes before adding vents, paint, or bolts.
3. **Plan continuous surfaces.** Use broad curvature and large patches to
   locate main hull curvature changes; rebuild controlled topology rather than
   lofting disconnected boxes.
4. **Locate engineered features.** Cross-check sharp-edge, normal orientation
   and concavity candidates with renders; do not treat every noisy Tripo
   triangle boundary as a real automotive panel.
5. **Construct hierarchy.** Main shell → canopy and roof → actual recessed
   features → secondary armor → propulsion and mechanical parts → fine details.
6. **Compare.** Render candidate from exactly matched cameras. Run measured
   shape-difference scans and section-by-section silhouette comparison.
7. **Iterate with evidence.** Correct largest silhouette/volume deviations,
   then surface continuity and mechanical depth, then smaller details.
8. **Export both.** Keep unmodified reference and newly constructed result as
   separate GLBs, and keep section graphs and before/after renders.

## Limits and safety

These measurements are **not** model weights and do not change the assistant's
base training. They are reusable evidence while accessible. They can guide
procedural code generation and objective validation, but not guarantee a
faithful or automatically retopologized reconstruction. The analyzer cannot
reliably identify semantic fenders, doors, or cockpit components without
additional geometric grouping and human inspection. Hole-aware contour
reconstruction, robust model registration and true CAD-grade surfaces are
future improvements.

Original geometry stays unchanged. All outputs are derived, separate files.
