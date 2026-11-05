# Deep DINOv2 Teaching — Research-only CPU Curriculum

## Purpose and authority

This workflow gives **AssetWright's own original Mini AI research student** a richer, four-view visual teacher. The licensed teacher is frozen `facebook/dinov2-small` (Apache-2.0). Source CAD lessons come from Autodesk Research's `ADSKAILab/Zero-To-CAD-100k` dataset (Apache-2.0). No outside AI builds a final GLB; no downloaded CadQuery program executes. The pretrained image encoder supplies **numeric supervision**, not vertices, geometry, materials or finished game assets.

The new study is independent of existing native Kotlin MiniGeometry/GlbWriter and verified advanced geometry/branch/composition checkpoints. It never changes Android weights or unlocks production geometry.

## Source and schedule

Files:
- `tools/mini_ai/deep_dino_curriculum.py`: bounded official split ingestion; pin one immutable dataset revision for training and validation; hash source CadQuery programs and 4 reference images (`image_0`, `image_2`, `image_4`, `image_6`); use DINOv2 Small on CPU without execution of any source CAD program.
- `tools/mini_ai/deep_dino_student.py`: an **AssetWright-owned, from-scratch** two-layer 64-hidden-unit student that predicts 24-dimensional visual signatures from supported CAD operation sequences. It is not prompt-to-mesh, and teacher images or a face count are not student inference inputs.
- `tools/mini_ai/test_deep_dino_curriculum.py`: source integrity, disjoint validation, missing/tampered images, no leakage from source mesh face counts, bounded revision-pinned inputs.
- `.github/workflows/deep-dino-training.yml`: triggered on first source push, can be manually rerun, and runs once per week on Sunday at 08:13 UTC. The cron job rotates among six fixed development cohorts; it does **not** implicitly accumulate validated weights or promote any model.

Default bounded research cycle:
- 320 licensed source-hashed training CAD programs (starts after the earlier 96-example training study).
- 80 separate official validation CAD programs, starting at official validation offset 80 to avoid the previously inspected first 40.
- 4 independently hashed camera views per object: 1,600 frozen-encoder image observations if ingestion succeeds.
- 384-dimensional frozen DINOv2 visual vectors averaged across the four views; each record retains image/source SHA provenance and cross-view disagreement.
- One original 24-dimensional student visual signature, fit in a staged curriculum.
- A SHA-defined internal development subset, with model selection **only** on internal development data, followed by one official validation score.
- Rejection unless the student beats the training-set mean by 3% and a same-input linear CAD-to-visual baseline by 2%; advanced-operator holdout regressions have an additional guard.

Three cumulative training phases *within one experiment*:
1. Shape foundations: simple supported construction sequences.
2. CAD composition: all supported operation sequences with prior learned weights.
3. Advanced geometry focus: increased emphasis on lofts, sweeps, booleans, fillets, shells, chamfers and complex operations. Weight updates continue from the previous phase.

Each complete run stores evaluation and a candidate student in GitHub Actions artifacts (45-day retention). Only a passing candidate gets a `validated_research_student.json` inside that artifact. Failing gates remain reported and unpromoted. Temporary runner caches are not durable memory.

## What counts as progress

A lower held-out DINO feature error means the student predicts numeric teacher features better than the baselines on these particular CAD source families. It **does not prove** faithful surface reconstruction, manifold topology, vehicle styling, real-world image understanding, or arbitrary text-to-3D generation. The official validation examples will become exposed development evidence after inspection and must be retired before claims of novel blind generalization.

A subsequent phase must train and audit **actual native geometry operators** using independently generated Kotlin GLBs, test continuity/manifoldness/triangles/physical dimensions, evaluate unseen object families, and require human visual approval before any Android deployment. DINOv2 cannot bypass these mechanical and artistic gates.

## How to inspect

GitHub Actions → `AssetWright Deep DINOv2 Teaching Research` → latest run → `assetwright-deep-dino-four-view-research` artifact. Review `result/evaluation.json` and compare mean, linear and deep student metrics. `candidate_student.json` is not approved for Android. A green Actions job means execution passed; the research result is only accepted when `status=validated_research_only`.

The public repository remains the sole writing target. The SceneForge, Shattered Realms, Forge-Core, and private AssetWright repositories remain untouched.
