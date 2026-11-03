# AssetWright: pretrained visual knowledge transfer into OUR Mini AI

## Hard boundary: who generates the final geometry?

The user requires **our Mini AI and native modeling engine** to perform the
final modeling. We will not substitute a TripoSR, TRELLIS, or other third-party
AI-generated GLB for an AssetWright model. Other pretrained systems are
**teachers only**, and only in ways permitted by their respective licenses.

This first research implementation uses the public Apache 2.0 licensed
[facebook/dinov2-small](https://huggingface.co/facebook/dinov2-small)
image *encoder* during an optional training experiment. It outputs 384
numerical image features, not polygons, materials, or model geometry.

The AssetWright student is independently initialized and trained by our own
standard-library Python code. At inference the student receives **text only**
and proposes six bounded parameters consumed by the existing native Kotlin
`MiniGeometry` + `GlbWriter` engine. No pretrained teacher weights or
vision runtime are needed for that student inference.

## Implementation and provenance

1. `VisualTransferExportTest.kt` optionally exports 36 unique original
   native GLBs with the actual six editable parameters used by MiniGeometry.
   This is disabled during normal Android use and unit tests unless the
   `ASSETWRIGHT_TRANSFER_OUT` environment variable is explicitly set.
2. `render_visual_transfer.py` checks the exact GLB hash and native
   generation marker, then renders four fixed Blender views (front, side,
   top and three-quarter). Every PNG and GLB receives a SHA-256 hash in the
   manifest.
3. `extract_dinov2_features.py` optionally loads a **frozen** public image
   encoder on CPU and extracts its visual representation. It never generates
   3D meshes.
4. `visual_transfer_student.py` trains a small original text neural network
   with geometry-parameter supervision and an auxiliary frozen-image-feature
   objective. It does **not** fit or copy external mesh-generator weights.
5. Entire design groups, including all their views, stay in one side of the
   train/holdout split. An identical native source mesh cannot appear twice.
6. The knowledge-transfer challenger must beat (a) the **same text model
   without the image-teacher objective** and (b) the train-set constant-mean
   baseline by at least 3% held-out parameter MSE, with bounded
   per-dimension regressions. Otherwise its visual-transfer claim is rejected.
7. Even a research-valid student remains `android_deployable=false`, and
   no workflow auto-deploys a student to a phone. The real native GLB and
   human visual approval gates still apply.

## Free GitHub workflow

Workflow: `.github/workflows/visual-transfer.yml`

Ordinary pushes run offline provenance/learning safety tests only.
A **manual workflow dispatch** with
`train_on_original_native_glbs=true` runs the full CPU experiment:
native Kotlin GLB export -> Blender four-view rendering -> frozen DINOv2
feature extraction -> native-owned student fitting -> heldout evaluation.
Results go to the GitHub Actions artifact
`assetwright-owned-student-visual-transfer-research`.

Pretrained model downloads and CPU inference are isolated from regular
Android builds. We do not copy the pretrained weights into the public repo,
and personal data and private training examples are excluded entirely.

Offline safety tests:

```sh
python -m unittest discover -s tools/mini_ai -p 'test_*.py'
```

## Honest interpretation of early experiments

The 36 original examples are synthetic and combinatorial: three vehicle
types x three length descriptions x four roof/nose descriptions. They are
**not** 36 independent artist-approved high-fidelity vehicles. A successful
holdout test proves at most that a compact text student recovers some of
our *existing six parameters* from those narrow descriptions. It does
not demonstrate Class-A surfacing, correct joined topology, game
readiness, or broad text-to-3D generation.

The next milestone after a genuine evaluated CPU run is more diverse,
licensed/reviewed construction-pair supervision and an explicitly reviewed
bridge into the Android Mini AI. Improving geometry will still require
new *native* model-building operations such as welded cutouts, shared
boundary loops and smooth tangent/normal continuity. No neural feature
encoder can bypass that engineering.

**No external AI should produce the final model. The goal is to help our
Mini AI learn to construct better models itself.**
