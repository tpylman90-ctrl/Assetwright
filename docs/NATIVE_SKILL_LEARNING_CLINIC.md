# AssetWright — learn from mistakes, not from endless brute-force repetition

## Scope and truthful analogy

Language models improve through exposure to data, examples, correction signals,
and evaluation. I cannot introspect or remember subjective difficulties from
the training of a model like myself, so this project translates **observed
machine-learning failure modes** into explicit, testable engineering lessons.
This does not assert that AssetWright trains the same way as a foundation model.

The first bounded *learning clinic* targets three existing, actually verified
native modeling operations. It does NOT claim general Blender competency.

## What previously made the training process inefficient and how we address it

| Failure | Fix in this training session |
|---|---|
| Ambiguous "looks wrong" feedback | Every correction includes exactly one typed native operation and a numeric target strength; unapproved artistic critiques remain a separate problem queue |
| Memorizing easy common words, not distinctions | Contrasting *socket vs shoulder vs shroud* instructions on the same object, same strength, similar wording, with precise target changes |
| Repeating mastered exercises | Diagnose abstentions, wrong-operation decisions, and strength errors; emphasize actual mistakes while preserving a basic correction curriculum |
| Forgetting previously learned skills | Interleave the original 135 labeled training instructions and impose old-heldout nonregression thresholds |
| Believing pseudo-labels produced by its own model | Train ONLY on originally authored exact native labels; don't silently accept model predictions or prior unapproved visual feedback as truth |
| Gaming a benchmark | Choose checkpoints using *development* instructions only, then evaluate a disjoint *blind* set once, with no further tuning based on that test in the current session |
| Ignoring real geometry | Require source-SHA-matched, independently audited baseline and native GLBs for the three operations before any continuing training |
| Wasting CPU hours and starting again | Resume from the already validated owned student, run short bounded gradient updates, keep provenance hashes and candidate checkpoint for audit |
| Confusing 3D teacher competence with student ownership | Zero-to-CAD and DINOv2 remain knowledge sources, never third-party geometry producers; AssetWright-owned weights and Kotlin generate final GLBs |

## Implementation

- `tools/mini_ai/native_skill_clinic.py`: reads prior verified source student
  and four-GLB audit, grades *correction-only* mistakes, resumes weights,
  interleaves difficult exercises with old training examples (rehearsal),
  selects best checkpoint on new development templates, and measures old
  retention plus one untouched new blind set.
- `training/curricula/native_skill_clinic_v1.json`: explicit original
  operation labels across 15 correction, 9 development, and 9 blind phrase
  templates. These expand to 90 supervised correction, 27 development and 27
  blind cases. All examples are original authored descriptions, not model
  outputs, source CAD programs, or external GLBs.
- `tools/mini_ai/test_native_skill_clinic.py`: rejects duplicate or mixed
  teacher instructions, unsupported labels, forged GLB audit hashes, and
  positive learning labels derived from negative reviews. Tests resumable,
  nonforgetting updates.
- `.github/workflows/native-operator-student.yml`: only after the
  independent native GLB proof passes, perform one bounded learning clinic.
  Upload the candidate, diagnostic report and evaluation as **research-only
  artifacts**. Keep the existing Android app and native mesher unchanged.

## Actual gates

A clinic checkpoint can be *research-valid* only if its new unseen test has:

- at least 80% **operator accuracy**;
- no more than 0.15 average **strength error** (on a 0–1 scale);
- no fewer correct operations than the checkpoint before the clinic;
- improvement of at least 0.01 in mean strength error;
- old-skill regression of at most 3 percentage points operation accuracy and
  0.025 strength error.

Failures are informative. **Do not weaken these gates or keep adjusting the
model after observing the blind evaluation.** A subsequent independent
experiment must use a new untouched family of prompts and shapes.

## Real-world warnings

The first clinic still uses synthetic, reviewed *three-operation* examples. It
is a disciplined learning-process experiment, not evidence of lifelike
automotive surfacing or arbitrary CAD. Its old evaluation set was used during
past architecture tuning, so it measures retention only; it is NOT an
untouched external generalization benchmark.

The previously committed `training/reviews/vehicle_visual_feedback.json`
contains **negative, unapproved design observations**. The clinic reports
unresolved themes such as cockpit-hull continuity, engine-body integration,
and exposed structural mounts, but does not treat those observations as
verified geometry targets or promote them to training labels.

GitHub Actions artifacts expire. Cumulative training beyond the first session
requires versioned durable checkpoints and validation data; approved results
can be added to persistent source-controlled training history. This workflow
does not pretend that temporary CI artifacts create unlimited background
training. We retain deliberate, small, reproducible, free training steps.
