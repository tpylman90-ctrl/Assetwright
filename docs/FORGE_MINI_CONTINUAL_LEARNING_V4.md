# Forge Mini — cumulative neural learning, not disposable tests

## Persistent knowledge

The strongest original teacher-free neural student from the 32-minute
marathon has 160,938 learned parameters, 93.75% operation recognition,
and strength MAE 0.12706 on its now-exposed 96-case research holdout.
This model is permanently saved under:
training/knowledge/native_strength_teacher_free_42080318206/

The v4 training pipeline no longer starts from random neural weights.
It loads and SHA256-checks the exact previously saved original
safetensors file and training-only image normalization. The first
dense layer is analytically rebased to new normalization statistics,
preserving the old model's learned predictions; this is checked in code.

## What the new sessions learn

The new source curriculum generates 716 original Kotlin GLBs:
- 504 changes in 12 training families, each with six operations and
  seven strength values;
- 96 new development changes in four disjoint families;
- 96 genuinely blind validation changes in four other families;
- 20 untouched original reference forms.

The workflow also downloads the original source-hashed study artifact,
replays 672 prior TRAINING images and labels, and excludes every older
blind validation shape from training. 96 inspected older development
examples can be used for retrospective forgetting reports only.

Eight continued-learning sessions start from the same original saved
neural weights. Each mixes new lessons with older replay lessons; half
also use original teacher-free model predictions as a retention target.
The sessions have a combined active CPU-gradient budget of 1,920
seconds, and each session saves its development-selected weights.

Only fresh development examples and previous TRAINING retention
criteria select the model. Once the choice is fixed, 96 new blind
examples are evaluated one time. Both the saved parent and new
student reconstruct 96 real original Kotlin GLBs, producing 192
GLBs for independent source-hashed topology and vertex-distance
comparison.

## Approval and durable new history

A green GitHub Actions workflow proves the work ran, but does NOT
prove the new model improved. A research successor needs at least 2%
lower actual GLB vertex error than the frozen parent, no more than
about one percentage point classification loss on new sources, no
significant strength regression, at least 10% better 3D geometry than
an unmodified base, and retention of earlier known skills.

After independent audit, the workflow commits the new student's
REAL trained weights, detailed validation and geometry metrics,
parent lineage and disposition under:
training/learning_runs/strength_continual_v4_<github_run_id>/

A failed candidate is kept as research history without displacing
the previous verified checkpoint. Passing permits human RESEARCH
review, never automatic Android promotion. No external AI
generates GLBs; only AssetWright Kotlin AdvancedFormLab does.

## Relationship to the Android mini AI

The Android app already has a native geometry skill panel and
local memory: reviewed original operation+strength choices persist
on the phone and affect future geometry-lab prompts. This is
directly usable now but distinct from neural pixel decoding.
The continued research student is not an Android inference model
until compatible image preprocessing, runtime and human review
are implemented and verified.

Workflow: .github/workflows/forge-mini-continual-learning.yml

Protected: previously verified research weights, all earlier
benchmark evidence, Android generator, private AssetWright repo,
SceneForge, Forge-Core and Shattered Realms.
