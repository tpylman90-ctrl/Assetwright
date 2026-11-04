# Advanced Native Geometry Learning — Large V1 Research Batch

## Why this experiment

Previous work proved that our Mini AI can recognize five simple native
forms (20/20 heldout examples), but those shapes came from one procedural
generator and that study did not learn construction strengths. Vehicle V2
also demonstrated that triangle count and accurate existing controls do
not imply visually convincing bodywork.

This new *separate research system* teaches **actual response to operations**:
how cross sections, centers, angles, and visible local surfaces change under
a bounded continuous control. The Android default model and all accepted
older checkpoints are unchanged.

## Six original native construction operations

The Kotlin AdvancedFormLab produces real closed, source-owned indexed GLBs:

1. SECTION_LOFT — dual smoothly weighted longitudinal cross-section changes
   to emulate distributed shoulder/haunch volumes.
2. TANGENT_SWEEP — curved path with a derived local transverse frame, not
   a simplistic translated copy of a cylinder.
3. SECTION_TWIST — angularly rotating elliptical cross-section about a
   centerline without generating detached overlays.
4. SUPERELLIPSE_PROFILE — rounded/corner-full cross-sections with controlled
   exponent; **not** a three-dimensional edge fillet.
5. LOWER_RECESS — smoothly feathered underside sidewall undercut within
   the same connected indexed shell; **not** a through-hole Boolean.
6. RIBBED_FAIRING — controlled repeated longitudinal ridges/valleys with
   a smooth axial envelope.

All operations generate geometry in AssetWright Kotlin. No external
pretrained image-to-3D or CAD model supplies final vertices.

## Increased source batch

912 independently source-hashed **original** Kotlin GLBs:

| Source partition | Families | Strengths/family | Operations | GLBs |
|---|---:|---:|---:|---:|
| Training | 12 | 10 | 6 | 720 |
| Dimension holdout | 4 | 4 (interleaved) | 6 | 96 |
| Aspect-ratio shift | 4 | 4 (interleaved) | 6 | 96 |

All families and strengths are disjoint across partitions. These are
**synthetic, internal research partitions** and NOT independent scanned
objects or a real-world new asset category. Values are fixed before the
first CI study. Any inspected evaluation partition must be retired when
changing metrics, operations or thresholds.

## Genuinely distinct learning tasks

1. Source-trust gate: every GLB must match the manifest SHA-256 and original
   Kotlin schema; reject missing, duplicate or unexpected samples.
2. Physical audit: independently read all GLB vertices and triangles and
   reject open/nonmanifold edges, degenerate faces, inverted closed surfaces,
   and overbudget geometry. For tangent sweep, require a real perpendicular
   cross-sectional frame in the exported vertex buffers.
3. Shape operation classification: train our own fresh six-way CPU softmax
   exclusively on measured real geometry features, never file names, strength
   labels or construction code as features.
4. **Continuous control recovery:** fit per-operation monotone response
   curves from actual training GLB measurements only. Predict strengths
   from new, unseen continuous target levels rather than plugging in an
   authored default.
5. Heldout performance: require >=90% operation classification on the new
   dimension partition with >=13/16 correct per operation, >=82% on the
   aspect-shift partition with >=11/16 per operation, and strict conditional
   strength MAE <=.085/.12 respectively. Also enforce end-to-end error
   and real improvement over constant .50 strength.
6. Human visual inspection: 72 source-hashed side/three-quarter clay and
   wire frames. Automatic mesh correctness does not constitute approval.

Original training examples and original geometry remain the source of
learning. If any gate fails, preserve diagnostics and reject the candidate.
Do not weaken thresholds or substitute another pretrained model.

## Important limitations

This stage is still six isolated surface transformations, not an authored
multi-operation model, a learned general-purpose shape designer, Class-A
car body, Boolean assembly, truly welded engine, spline NURBS, genuine
G2 interface, or a trained understanding of all object categories.
Later programs will need composition, boundary continuity, triangle-budget
optimization, heldout object categories and hands-on visual approval.

References for a subsequent continuity-and-guide-rail stage:
- Autodesk Fusion Loft (cross sections, tangent G1, curvature G2, guide
  rails): https://help.autodesk.com/view/fusion360/ENU/?contextId=SLD-LOFT-SOLID
- Autodesk official advanced surface reference:
  https://help.autodesk.com/cloudhelp/ENU/Fusion-Patch/files/SFC-REF-LOFT-DLG.htm

These are conceptual teachers, not paid mesh generators or runtime assets.

## First-run measurement correction and benchmark retirement

The first 912-GLB source export completed successfully, but its independent
measurement audit rejected an **unstable descriptor**. In tall aspect-shift
shapes, an underside lift moved the naïve top/bottom bounding-box center,
causing the supposed lower-surface recess to appear negative. Twisted
sections also invalidated world-axis corner measures. A source GLB
structural pass alone was not sufficient to validate this analysis.

We did not weaken any acceptance threshold or adjust mesh geometry to
manufacture success. The corrected descriptors measure corner fullness in
the **actual local section basis**, and measure the upper/lower radial
difference about the true cross-sectional center determined by paired
source vertices. These measurements are invariant to cross-section
rotation and independently anchored to actual GLB coordinates.

The initial `advval1..4` and `advshift1..4` geometries were inspected
in debugging and are now retired, not pristine blind tests. New unseen
synthetic families `advval5..8` and `advshift5..8` replace them. The 720
training examples and strict independent study gates are unchanged. The
original failed build and uploaded GLBs remain in GitHub Actions evidence.
