# Native connected branch placement — research stage

## Objective and scope

Previous validated AssetWright checkpoints learned simple forms, six
native geometry responses, three-operation construction programs, and
one connected hollow housing with an integral flange. The next challenge
is **where a structural junction attaches** and how its exterior shoulder
and internal socket are formed, while still generating ALL final mesh
geometry through our own Kotlin geometry engine.

This is deliberately a new research module. The regular Android generator,
prior acceptance thresholds, historical synthetic holdouts and frozen
student weights are untouched.

## Original new geometry and topology

NativeBranchLab takes the accepted original NativeInterfaceLab hollow parent.
It removes one 6-by-8-quad PATCH from the parent exterior, reuses the patch
boundary vertex IDs, and joins a sequence of new support/shoulder/boss
rings to the parent. A narrower annular mouth and a recessed, capped
interior produce a REAL blind socket. It is not an overlay, glued-together
pipe, simple color inset, or Boolean approximation made from detached parts.

The parent longitudinal through-bore stays open. The side socket is blind,
NOT a connected T-junction or a branch that traverses the parent inner wall.

After mesh compaction, each source must have:
- **2,730** indexed (actually referenced) vertices;
- **5,460** valid triangles and **8,190** uniquely paired edges;
- a single connected component, Euler characteristic **0**, genus **1**;
- zero open/nonmanifold edges, consistent edge winding and positive volume;
- an actual socket recessed from a raised side mounting boss.

The site grammar comprises five longitudinal attachment zones and
four azimuth quadrants: 20 discrete junction positions. Three bounded
continuous controls change rise, blind-socket depth and shoulder blending.
The current transition is formed from a series of profile rings; it is
**not** a proven real-radius fillet, surface-surface Boolean algorithm or
Class-A NURBS/G2 patch. We do not claim self-intersection-free arbitrary
vehicle bodies.

## Fresh source curriculum (not old holdouts)

| Partition | Dimensions | Attachment sites | Strength variants | GLBs |
|---|---:|---:|---:|---:|
| Native train | 6 | 20 | 3 | 360 |
| New dimension families | 2 | 20 | 2 | 80 |
| Extreme proportions | 2 | 20 | 2 | 80 |
| **Total** | | | | **520** |

All meshes are created by AssetWright native Kotlin, exported by GlbWriter,
hashed with SHA-256, then independently read and checked from their GLB
buffers. Train/holdout dimensions are distinct from each other and from
the old connected-housing experiments. Any evaluated family inspected
while debugging is retired as pristine future evidence.

## Own learner and fixed gates (frozen before first evaluation)

A small supervised source-geometry model measures actual direction and
longitudinal location of the raised boss, its physical rise, interior
blind-socket depth and profile-blend ratio. It trains a 20-way geometry
nearest-centroid *site classifier* and a regularized polynomial control
regressor. Neither model uses source labels or filenames as inference
features. The old weights remain frozen.

- >=95% correct position on unseen dimensions; >=90% on aspect shifts;
- at least 3/4 positions correct for every specific site in each split;
- <=0.020/0.030 overall control-strength mean absolute errors;
- <=0.028/0.040 per-control errors and hard maximum-error caps;
- >=0.12 strength MAE improvement over a fixed-0.5 baseline;
- source-hashed **160 native student-reconstructed GLBs**, with closed genus-1
  topology, no degenerate or nonmanifold faces;
- <=0.018/0.028 normalized mean source-vs-reconstruction surface RMS;
- strict per-split worst-surface-error bounds;
- 80 real source-hashed clay and wireframe previews, followed by human review.

No acceptance threshold will be lowered to manufacture a pass. A failed
result is retained in CI and is not deployed.

## Honest learning boundary

This stage learns to **recognize and invert placement in existing target
geometry** with a known fixed 20-site construction grammar. It does not
choose whether a novel design *needs* a structural connection based on
semantics, and it cannot place an arbitrary-angle branch, generate general
Boolean T-junctions, evaluate engineering load paths or guarantee
C1/G1/G2 face continuity. Those are future stages that need genuinely
new shapes, categories and independent human review.

Technical reference concepts:
- Blender mesh extrusions and manifold modeling:
  https://docs.blender.org/manual/en/latest/modeling/meshes/editing/mesh/extrude.html
- Open Cascade BRep fillet/shape construction:
  https://dev.opencascade.org/doc/overview/html/specification__modeling_algorithms.html

Only original Kotlin geometry, free Python/NumPy/Pillow, and GitHub Actions.

## First-study evaluation freeze

The original one-shot study was launched from `a4248753b47387879eb48948b9daca8fd40bad67`
at https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41944304381.
Its 520 source family choices and all classification, continuous strength,
forward reconstruction and structural limits were committed before testing.
We now keep the original workflow manual-reproduction-only, to avoid
automatically repeating or promoting an exposed synthetic benchmark on
subsequent commits. Any correction involving the student, measurements,
native shapes or testing thresholds must establish fresh, untouched
evaluation families first. This does not affect the already-running run.
