# CAD Surface Transfer — physically measured source teacher (research only)

## Why this experiment exists
Earlier AssetWright native research learned deterministic construction
programs, through-bores, and blind sockets. A separate 1600/400 licensed
CAD-program study established an operation grammar and source B-Rep
face-count proxy. **Neither is evidence of having learned real CAD
surfaces**. This stage teaches surface descriptors from original external
STL geometry, without permitting any outside mesh into a finished
AssetWright game asset.

Official source: ADSKAILab/Zero-To-CAD-100k, Apache-2.0
https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-100k

The original STL mesh is read as bytes and discarded. Downloaded CadQuery
Python is only statically parsed; scripts are NEVER executed. Immutable
upstream source revision, dataset train/validation splits and per-record
CAD+STL SHA-256 hashes are required. We retain numeric descriptors and
provenance, NOT downloaded mesh assets.

## Real geometry teaching targets
From bounded binary STL triangles, with only a temporary, quantized,
measurement-purpose vertex-weld, compute five dimensionless targets:

1. Intermediate bounding-box dimension / largest dimension
2. Smallest bounding-box dimension / largest dimension
3. Original triangle surface area / bounding-box area (clipped to 4)
4. Shared mesh-edge fraction with dihedral normal variation >30 degrees
5. Shared mesh-edge fraction with dihedral normal variation >15 degrees

The last two are **discrete triangle-face normal variation proxies**.
They do not certify true CAD surface curvature, fillet radii, G1/G2 seam
continuity, or visually pleasing shape. Sampling density and STL
tessellation can alter them. STL sources that exceed bounded byte/triangle
limits, are not exact binary STL, have degenerate geometry, or lack enough
shared edges are rejected rather than repaired secretly.

## Own Mini AI inference
Inputs are **only** whitelisted CAD construction operation names and
numerical literal summaries from safely parsed CadQuery source.
The original target STL, its filename/hash, source dimensions, label
face-count and measured surface descriptors are never inference features.

The student is a from-scratch regularized multi-output ridge regression.
It compares three independent source-trained alternatives:

- Training-only median surface signature.
- A stronger operations-only regression (CAD vocabulary and counts).
- The owned operation-plus-numeric-literals regression.

Fit/regularization strength is selected from an INTERNAL SHA-defined
development split. Official validation is scored once, independently,
and not used to tune the candidate.

## Original held-out study and fixed gates
- 320 new official TRAIN STL sources, starting at dataset row offset 2300;
- 96 previously uninspected official VALIDATION STL sources, starting at
  row offset 1700, beyond previous 96/40, 1600/400 and deep-DINO cohorts;
- both official splits pinned to the same immutable dataset SHA;
- >=256 accepted train meshes and >=64 independent validation meshes;
- >=5% reduction in normalized signature MAE over the train median;
- >=1.5% improvement over the stronger operations-only model;
- at least 3/5 measured target classes better than the train median;
- <=0.18 normalized mean absolute error over the five targets;
- no duplicated source code hashes, STL hashes or official source IDs;
- no unsafe downloaded Python execution and no outside geometry export.

Failures are preserved as rejected research evidence. The original
evaluation thresholds are frozen; once examined, this validation cohort
must be retired for future pristine blind claims.

## Geometry quality and production boundary
No native GLB is generated in this experiment. Passing means useful
prediction of **surface descriptors from real licensed geometry**.
It does NOT yet produce arbitrary STL-to-native reconstruction, G2 fillets,
connected joints, vehicle bodies, or approved professional-quality assets.
The accepted Android generator, earlier mini-student checkpoints and
frozen pretrained visual teacher remain separate and unchanged.

The subsequent native stage should learn how to modify its own Kotlin
surfaces to match measured proportions and smoothness *without copying
the training source meshes*, and audit source-hashed GLBs, manifoldness,
curvature transitions, and human clay/wire approval.


## Measured first and second studies — mandatory rejection history

2026-11-04, official original source revision
48bcf0a8c6fbfb47a27f5662007c24dff8d754ae.

First run 41958208141 extracted 320 new STL training measurements and
96 validation measurements but the student input auditor correctly stopped
on a BUG in a legal signed numerical feature: a group can be exactly -1,
not strictly greater than -0.999999. The audit bound and unit test were
corrected. Those first 96 validation records (offset 1700) were retired.

Second run 41959059624 re-used only the *identical original* 320 train
records, then measured 96 new official validation STL records at offset 2600.

**Reject the first numerical surface candidate.** Heldout normalized MAE:
- Train-only median: 0.14302803019270835.
- Operations-only learned baseline: 0.12386975301530968.
- Operations plus simple 18-number numeric summary: 0.12332584793985785.
- That is 13.78% better than a constant baseline but only 0.439%
  better than the genuinely stronger learned operations-only baseline.
- Original accuracy gate demanded at least 1.5% better than the
  operations-only baseline: FAILED, and the other six checks passed.

The student is NOT accepted. Its data and rejected candidate remain in
GitHub Actions evidence. This measured failure suggests source numerical
features have lost critical relational structure: a mean of CAD dimensions
is not the same as a width/height or fillet/body proportion.

## Third pre-registered experiment: explicit CAD relative geometry

Code: cad_surface_profile_features.py, cad_surface_student_v2.py.
Original training offset 2300 (320 STL shapes) and *fresh*, disjoint
official validation offset 3700 (96 STLs). The new source parser recognizes
literal geometry arguments without evaluating Python and computes
relative profile dimensions, extrusion-to-body ratios, hole/cut-to-body
ratios, blend/fillet ratios, and pattern/transform magnitudes.

Three students are trained and compared fairly using only a train-internal
development split for model choices: original operations-only, older
aggregate numeric, and richer explicit proportions. Heldout acceptance
keeps all original 7 thresholds and **adds** a new predeclared minimum
1% improvement over the older numeric source-summary model. No foreign
meshes become generated AssetWright meshes.

A rejected result must remain rejected, documented, and measured again
only with new untouched CAD source families. This is a geometry-learning
program over months, not a demand for a single quick positive score.
