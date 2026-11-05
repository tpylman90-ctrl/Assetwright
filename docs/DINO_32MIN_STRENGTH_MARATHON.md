# AssetWright — 32-minute active CPU geometry teaching marathon

## Why another run

The prior source-disjoint 16-session study learned native operations with
89.58% held-out accuracy, with continuous strength MAE 0.14659. Its
matched teacher-free student had lower strength MAE 0.14213 and fractionally
lower true GLB vertex reconstruction error. The source-verified research
gate correctly rejected the DINO checkpoint. More gradient updates alone
are NOT assumed to improve the geometry student; only independent
development-model selection and fresh native source reconstruction count.

## Active optimization budget

A dedicated GitHub Actions workflow, named
AssetWright DINO 32-Minute Native Geometry Marathon, runs **1,920 seconds
of active PyTorch optimization**, divided evenly across 16 individually
seeded experimental sessions (eight frozen-DINO-guided and eight
otherwise identical teacher-free controls). Real measured training time
must exceed 1,800 seconds for research eligibility; the pipeline cannot
mark sleep, download, rendering or waiting as gradient training.

Each seeded session:
- fits a wholly original small neural student on paired orthographic
  before and after source images, with no operation/strength text in
  image pixels;
- optimizes for its time quota using genuine minibatch gradients,
  deterministic independent seeds, small label-preserving camera noise,
  operator-conditioned continuous strength controls and strength-order
  ranking for source-matched native geometry;
- periodically evaluates *development-only* errors, saves its own
  source-safe safetensors checkpoint, and retains its best development
  state rather than the last (possibly overtrained) state;
- outputs training time, update count, selected checkpoint step and
  development metrics for auditing.

The two groups independently select only their DEVELOPMENT-winning
seed and checkpoint. Validation is measured only after all 16 sessions
complete and both winners have been selected. The CLI hard-rejects a
requested training budget outside 30–35 minutes. Separate data-prep
and training jobs keep model-fitting time distinct from CPU DINO
extraction and native renderer work.

## Fresh protected original geometry

DinoMarathonGeometryBatchTest.kt exports 888 ORIGINAL closed Kotlin
AssetWright GLBs, with exact source SHA256 hashes:
- 16 training families × six operations × seven strength settings =
  672 source-verified training transformations;
- four distinct development families × six × four =
  96 development transformations;
- four independent and NEW held-out families × six × four =
  96 never-inspected validation transformations;
- 24 unchanged source forms, one per family.

The 864 before/after transformations become 1,776 label-free
fixed-camera images. The frozen DINOv2 Small teacher contributes numeric
image-difference supervision and NEVER constructs or modifies a mesh.
All actual meshes, including student reconstructions, come from
original Kotlin AdvancedFormLab and GlbWriter. Heldout shape families
and heldout numeric strengths are different both from training and
from the previous delta_v1 and strength_v2 official validation sets.

The isolated run uses ASSETWRIGHT_DINO_STUDY=strength_marathon_v3.
Historical experiments retain their own source inventory and are not
silently replaced.

## Independent native geometry acceptance

DinoMarathonReconstructionTest.kt executes the two frozen student
proposals to produce 192 REAL original Kotlin GLB reconstructions.
The exact source GLB hashes are checked and meshes audited for
non-manifold edges, degenerate triangles, volume and connectivity.
Normalized original-vs-reconstructed vertex error is measured on
independent indexed geometry, not just rendered image embeddings.

Research acceptance requires all of:
- actual verified active optimization of at least 30 minutes;
- at least 65% native operator accuracy on 96 NEW source examples;
- heldout native continuous strength MAE at most 0.18, with no
  individual operation MAE above 0.30;
- at least 0.008 absolute better strength MAE than the same 32-minute
  teacher-free student;
- source-matched actual GLB vertex error at least 10% lower than leaving
  the original shape unmodified, and 2% lower than the equal-budget
  teacher-free student;
- no more than four incorrectly reversed adjacent strength steps among
  the 72 held-out per-family/operator ordering comparisons;
- independent hashes, topology and operation/strength values agree
  between the visual student and actual reconstructed Kotlin GLBs.

Any failed condition marks the candidate REJECTED; the workflow may
still be green if all computation and auditing completed. All seeds'
checkpoint files, honest source-aligned metrics, exact forward meshes,
and any rejected candidate are retained in GitHub Actions artifacts.
No mobile checkpoint deployment or automatic geometry promotion.

## Boundaries

These research students only identify and calibrate one of six
previously implemented single-shell modeling operations. This work
does not establish full CAD understanding, text-to-3D, arbitrary object
recognition, or production-quality vehicles. The user must review
multi-view examples before any integration can be considered.

All changes remain in the PUBLIC tpylman90-ctrl/Assetwright repository.
SceneForge, Forge-Core, Shattered Realms and the private AssetWright
repository are untouched. CPU software, Blender-free native generation,
and GitHub Actions remain free-tool compatible.
