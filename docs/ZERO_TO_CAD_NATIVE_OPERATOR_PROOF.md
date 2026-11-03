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
