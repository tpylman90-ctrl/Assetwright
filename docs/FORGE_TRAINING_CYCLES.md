# Forge-run Assetwright research and training cycles

This is the workflow for: "Forge, train Assetwright again using free 3D assets."
The user needs only to ask in a ChatGPT conversation with GitHub connected.

## How it operates

1. Forge reviews the current Assetwright repository and last study evidence.
2. Forge commits a new numbered request to
   `training/requests/forge_cycle.json` in the public Assetwright repo.
3. GitHub Actions **Forge CC0 Asset Study** starts automatically on that
   request (or can be manually dispatched with `workflow_dispatch`).
4. The action uses **Poly Haven's official public API** with an identifying
   User-Agent. It selects at most 8 mechanical/vehicle-related CC0 models,
   examines metadata and extracts normalized geometry descriptors from
   supported, explicitly linked Blender/FBX/OBJ/GLB/ZIP source files.
5. The compact report is uploaded as the `forge-cc0-shape-study` Actions
   artifact. No downloaded GLB is committed into GitHub. No credentials.
6. Forge can examine the report during the same conversation, improve
   modeling techniques, add tests, and publish separately validated
   Forge lessons. No unreviewed geometry is deployed to Android.
7. Android users who enabled Forge Lessons receive new validated recipes.
   Mesh-engine changes still require a new APK.

## Important distinction

**The automated asset-study job is source ingestion and shape study only.**
It does NOT train Android AI weights, learn full mesh topology, infer editable
construction operations from arbitrary models, or claim neural training.
Those are separate extraction, labeling, model-training and evaluation steps.

Forge is not a persistent background process. A running GitHub Action cannot
automatically invoke ChatGPT to continue its work after the chat ends.
The user can request a new interactive training cycle whenever desired.

## Sources, licensing and privacy

- Source: https://polyhaven.com and https://api.polyhaven.com
- Assets: CC0 — https://polyhaven.com/license
- API terms: https://github.com/Poly-Haven/Public-API/blob/master/ToS.md
- Live API use requires identifiable requests and visible "Powered by Poly
  Haven" credit. These reports record the credit and source links.
- The website is not scraped; this process uses its documented API.
- Compact structure statistics are retained in the report; third-party
  mesh binaries stay in temporary runner directories.
- Limits: 8 selected model records, 12 MiB per GLB, 12-minute runner timeout.
- Not every Poly Haven model is a vehicle. Semantic suitability needs
  independent review; unrelated object geometry is not silently injected
  into the hover-vehicle predictor.

## Cycle 2 — real geometry feature extraction and shape-prior fitting

The updated research workflow supports Blender-native .blend projects, .fbx,
.obj, .glb, and ZIP archives containing one of those formats. It uses the
official Poly Haven file listing, never invents download URLs, enforces a
32 MiB per-download cap and bounded archive extraction, and processes each
model in temporary GitHub runner storage with Blender scripts disabled.

The Blender process measures eight **dimensionless** descriptors:

- Sorted bounding-box axis ratios (orientation invariant)
- Relative mesh-object count
- Triangle-count fraction
- Vertices-per-triangle ratio
- Largest mesh component's triangle share
- Surface area normalized by object dimensions
- Median triangle area normalized by object dimensions

These features are geometric measurements. They do not preserve an entire
mesh, identify wheels or doors reliably, or represent the actual modeling
steps used by the source artist. Model names and raw scene data aren't
included in the derived descriptor.

A separate pure-Python geometric learner fits two geometry prototypes
(k-means centroids) against those features, reserves a source-disjoint
validation set, and compares held-out reconstruction distance against a
one-centroid baseline. The study publishes a training report and compact
candidate prior when at least four distinct models are valid.

A candidate prior is promoted to a **validated study artifact** only when
its held-out error doesn't exceed the baseline. It is **not** promoted to
Android, because broad real-world object geometry cannot yet be mapped
reliably onto the vehicle builder's six controllable parameters or new
construction operations.

The next stage is labeling reliable component types and their spatial
relationships, then training a semantic part-layout/operation predictor.
Only after that predictor passes meaningful vehicle-specific validation
should its output format be connected to Android.

### Recorded model-study outputs

GitHub Actions uploads only derived JSON reports:
`report.json`, `evaluation.json`, optionally
`candidate_prior.json` and `validated_prior.json`.
Third-party source mesh files and textures remain in temporary runner
directories and are never committed or shipped with the Android APK.

## Cycle 4 — component relationships (experimental)

The Blender study now extracts an **anonymous component proximity graph**
alongside the eight whole-object measurements. It inspects mesh-object
boundaries and also splits sufficiently large disconnected vertex islands
within merged Blender meshes. For each source scene, the graph represents
up to 24 geometric subcomponents, their normalized bounding-size/position
descriptors, and up to 200 pairs. Each pair records
relative size, center distance, AABB gap and whether bounding boxes overlap,
are nearby or are separated. Names, raw vertices, textures and the source
Blender files are not retained.

**These are geometric observations, not verified physical attachment
labels.** An AABB overlap does not prove two actual meshes touch, and a
single Blender mesh object can contain multiple disconnected parts.
The original vehicle's construction order is unknown.

A separately tested **component-layout prior** learns two prototypes from
those graph summaries. It requires at least four distinct multi-part models,
holds out **entire source models** rather than individual part edges, and
compares its reconstruction error against a one-profile baseline.
If there is insufficient data or worse validation performance, the model is
not promoted. This is not a neural network or a semantic part identifier.

Only derived CC0 geometry summaries are cached between training runs.
Data is deduplicated by actual source-file SHA-256, so repeating a cycle on
the same downloaded files does not falsely increase training sample count.
The latest per-cycle report, cumulative descriptor dataset, overall shape
prior and spatial-layout prior are downloadable GitHub Action artifacts.

**What remains before Android deployment:** human-verified component-role
labels, spatial attachment targets, a learnable operation representation,
and tests confirming generated mesh connectivity and visual improvements.
The training feed containing approved six-dimensional vehicle recipes is
separate and remains untouched by this experimental part-layout prior.

## How to repeat

Ask Forge: **"Run another Assetwright training cycle. Focus on vehicle body
panels, engine attachments and hard-surface topology."**

Forge increments the request's `cycle` value, sets the focus and commits.
The GitHub workflow collects material for review without manual downloading.

Results: https://github.com/tpylman90-ctrl/Assetwright/actions/workflows/forge-asset-study.yml

A real recurring schedule would be separate, with an explicit automation
or GitHub schedule trigger. A scheduled job could collect data unattended,
but would not cause the ChatGPT assistant to autonomously keep editing code.
