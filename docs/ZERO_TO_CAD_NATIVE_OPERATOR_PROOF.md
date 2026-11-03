# CAD lessons to original native GLB topology — research bridge

## Purpose
AssetWright learns from Zero-to-CAD's construction operation sequences and
from DINOv2 Small's image features, but **only AssetWright's own Kotlin
MiniGeometry/GlbWriter constructs and exports finished geometry**.

This work introduces one intentionally small, measurable, off-by-default
modeling primitive: a **closed rear-hull circular blind socket**, available
only to one-central-engine vehicles.

## Why this is a real geometry change
The new MeshBuilder loft uses the *same original body mesh part* for its outer
shell, stern annulus, recessed interior rim, inner well wall, and blind end.
These share triangle indices and a continuous surface; they are not layered
decorative floating polygons. The socket can be inspected in the original
GLB position/index buffers and tested for manifold edges, degenerate faces,
and normal orientation. The actual engine housing is **still a distinct
intersecting part** and must not be described as Boolean welded to the hull.

The user's normal Android generator remains unchanged, because
VehicleDesignControls.rearSocketDepth defaults to zero. The control is
ignored for multiple-engine configurations.

## Honest learned knowledge transfer
1. The independently held-out accepted **Zero-to-CAD grammar** provides a
   numeric prior for the "circle -> cutBlind" modeling concept.
2. The independently evaluated **AssetWright-owned visual-distillation
   student** predicts a 24-D DINOv2-derived visual signature based on
   a short CAD operation sequence. The actual DINOv2 teacher is not
   required at student inference time.
3. A **reviewed allowlist adapter** maps this particular circular blind-cut
   concept onto a native rear socket control. It refuses unverified
   checkpoints and arbitrary CadQuery operations. The depth of 1.0 is a
   declared controlled experiment, **not a learned geometric measurement**.
4. NativeCadOperationBridge.kt applies the typed, bounded construction
   command; MiniGeometry.kt builds all vertices. No downloaded Python code,
   third-party mesh, or teacher-produced model is used to make the GLB.
5. The exported original native baseline and experimental GLB are independently
   audited by tools/mini_ai/native_socket_audit.py.

This is the first limited **learning-to-executable-primitive bridge**.
It does not yet constitute arbitrary text-to-CAD program synthesis,
image-conditioned parameter selection, or realistic joined engine surfacing.

## Verification
Two separate workflows prove different things:

- Android APK: native Kotlin unit tests, unchanged defaults, the 40 existing
  GLB benchmarks, and a two-GLB connected socket experiment evaluated by
  an independent Python topology critic. Artifacts are review-only.
- Zero-to-CAD Construction Teacher: original dataset splits -> validated
  learned grammar/visual student -> bounded native operation proposal ->
  controlled JVM native GLB export -> independent actual topology audit.
  This second stage must pass before claiming a teacher-informed construction
  round trip.

Any failure is a rejected research operation, not permission to bypass the
independent validator. No research checkpoint is automatically deployed or
trained on unreviewed outputs.

## Later work
Replace fixed reviewed operation mappings with an independently evaluated
learned planner over a larger native operation vocabulary; train parameter
prediction from verifiable geometry; produce real shareable preview renders;
build smooth surface continuation and real shared engine/body topology;
evaluate new object families before enabling the student in Android.


## First verified native construction round trip — November 3, 2026

- [Android and native GLB audit run 41673266985](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41673266985) **succeeded**, including normal Kotlin tests, 40 existing original GLB benchmark fixtures, 2 experimental native GLBs, the new hull topology audit, Android debug build and signed-release build.
- [Teacher-to-native construction run 41673267167](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41673267167) **succeeded** across three jobs: input provenance tests; 96 Zero-to-CAD training programs / 40 official held-out examples and frozen DINOv2 feature teaching; and independently tested original native GLB construction from the restricted research proposal.
- The accepted research grammar assigned the cutBlind source operation **0.0409238** conditional probability after the model's example context, versus an unconditional **0.0215962**. The accepted visual student produced a **24-dimensional signature**. These research model outputs do **not** autonomously choose a recess depth or define the polygon positions.
- The native mapper, explicitly allowlisted for one central-engine vehicle, proposed recess_rear_socket at a fixed, controlled **depth 1.0**. Kotlin NativeCadOperationBridge and MiniGeometry created the original geometry.
- Independent GLB vertex/index audit passed all **nine** defined topology/structural checks. The original hull grew from **316 to 380 triangles** and gained **16 interior well vertices** (baseline **0**), keeping **13 total mesh components** with no hull boundary edges, overused edges, degenerate triangles, or inverted winding.
- The native baseline SHA-256 was ad8316e6394d3afffdfab14c810cc5da136c9cfc3c14f4a43de8836999870497; the socket SHA-256 was 4df6ac2bdc4d80ea8e3ad79f428858e58a3c2faa702b0ed4347efc35c43806dd. Both match the earlier standalone Android geometry audit, verifying that the research bridge did not substitute any outside-generated mesh.
- Original GLB comparison ZIP and the research proposal are retained as GitHub Actions artifacts while retention permits, not as permanently stored approved training examples.

**Research verdict:** restricted CAD lesson -> native typed operation -> connected original mesh -> independent GLB check is verified. Arbitrary text-to-CAD, learned surface-contour parameters, a visually approved vehicle, and true engine-to-hull welding are **not** verified. The trained research checkpoints remain outside the Android production generation path.
