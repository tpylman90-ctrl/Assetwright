# Forge self-training loop v1 — research model promotion gate

Assetwright has a bounded repeatable model-training workflow on GitHub.
When Forge (or a user-triggered study) runs a CC0 cycle, it can collect and
verify new models, train a challenger, compare to the last champion and
retain the better validated research model without manually re-importing
each sample. This is **not autonomous mesh generation**, and is not a
continuous ChatGPT assistant running after the conversation ends.

## Data flow and boundaries

1. Read approved third-party CC0 source metadata and a bounded number of
   official 3D files from Poly Haven's API.
2. Headless Blender extracts actual mesh features and source fingerprints.
   Original downloaded meshes remain temporary.
3. Match the publisher's textual descriptions to the exact source object
   and mesh SHA-256. Deduplicate across cycles.
4. Learn a caption-to-eight-numeric-geometry-descriptors challenger from
   independently inspected, licensed source models. **No generated objects,
   unverified part labels, or private user prompts are used as truth.**
5. Split source IDs deterministically into training and holdout sets. No
   parts of one held-out source are used for the fitted weights.
6. Compare challenger to (a) untrained average shape baseline and
   (b) the previously accepted champion on the same holdout sources.
7. Accept a new research champion only if:
   - at least 32 independently verified model pairs exist, with >=6
     held-out sources;
   - candidate passes the existing baseline error reduction gate;
   - at least two new independent training sources were added;
   - candidate has >=1% lower average held-out error than the incumbent
     (initial champion requires no incumbent);
   - no individual geometry output experiences a major accuracy regression.
8. Preserve last champion if a candidate fails these checks. Retain
   evaluation JSON and optional candidate for audit.
9. Cache **only** the accepted research champion across GitHub Actions runs.
   Candidate and metrics remain in time-limited downloadable artifacts.

The research champion is openly derived from CC0 source meshes and does
not contain private user examples. GitHub's public repository/workflows are
**not** private model storage. Privately owned game-specific weights, design
references, prompts and outputs must eventually live in a private repository
or private on-device storage. They must not be pushed to this public repo.

## Known limitations

The current teacher is verified CC0 geometry, not Assetwright's own
predictions. Deliberately, candidate AI outputs cannot recursively label
themselves correct. This avoids the common feedback failure in which
models amplify their mistakes.

A fixed held-out dataset repeatedly used for model selection can itself
be overfit over time. A *completely separate, genuinely blind final
evaluation* is needed before promotion to the phone, and actual rendered
vehicles need geometry/topology/visual inspection. Current model outputs
are eight approximate descriptors, not editable part assembly commands.

We have not enabled a recurring time-based schedule to spend GitHub CI
resources without the user's explicit choice. Each requested Forge study
automatically executes data intake, training, incumbent comparison and
regression gating. A private generation model will require a dedicated
controlled execution environment and deployment plan.

## Audit artifacts

Per-run output directory: `local-data/mini-ai/forge-study/self-training/`

- `evaluation.json`: incumbent and challenger loss, decision, reasons,
  heldout count, new verified sources, per-feature regression gate
- `candidate.json`: optional rejected or accepted challenger
- `champion.json`: accepted model or restored incumbent
- GitHub Actions cache: `forge-research-champion-<run id>`
- GitHub artifact: `forge-cc0-shape-study` includes the research evaluation

Run implementation: `tools/mini_ai/self_training_loop.py`.
Tests: `tools/mini_ai/test_self_training_loop.py`.

## Next stages

We should next add a reliable **procedural generator evaluation harness**:
create vehicles from the current build, check topology, bounding dimensions,
surface normals, manifoldness, part collisions, and similarity to reference
assets, then compare actual renders from fixed test prompts. These checks
can automatically reject poor generated geometry, but they cannot supply
real semantic part labels without reviewed examples. After those gates
work, the private model can propose edits and learn from accepted
construction outcomes rather than only coarse source statistics.
