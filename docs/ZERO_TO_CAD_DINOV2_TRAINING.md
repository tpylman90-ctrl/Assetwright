# Zero-to-CAD + DINOv2 Small: training AssetWright's own Mini AI

## Sources and permission
- Autodesk Research Zero-to-CAD 100K (https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-100k), Apache License 2.0, provides synthetic CadQuery construction programs, structured operator records, geometry metadata, and eight rendered views.
- Meta DINOv2 Small (https://huggingface.co/facebook/dinov2-small), Apache License 2.0, provides *frozen* image-encoder features. Its 384-D embeddings are NOT the same as the dataset's precomputed DINOv3 embeddings.

## Mandatory ownership boundary
Other models may provide visual supervision, but **AssetWright's own student and native geometry engine must construct final GLB assets**. No Tripo, external generator or downloaded CAD script can generate or replace native production models. This research code never imports outside meshes into the Android app.

## First bounded implementation
1. tools/mini_ai/zero_to_cad_ingest.py streams at most 96 official training and 40 validation examples, with 384/160 scan limits. It records only whitelist-approved operation names, source hashes, face counts, and two ephemeral render PNGs where available. Safe Python AST inspects fallback CadQuery methods without executing source code. No STL/STEP files are written to git or used by the production mesher.
2. tools/mini_ai/zero_to_cad_operation_student.py trains a compact original operation-sequence prior in AssetWright-owned code. It models next-operation probabilities conditional on preceding steps, and compares held-out cross entropy to a unigram baseline. The official train/validation splits remain distinct. At least a 2% gain is required for research acceptance. The output is never deployed to Android.
3. tools/mini_ai/zero_to_cad_dinov2_teacher.py reads only hashed reference PNGs, loads frozen DINOv2 Small on CPU, and emits 384-dimensional source-associated visual features. It produces no geometry. **The operation grammar remains separate.** The additional research-only visual student now learns to predict DINO-derived 24-dimensional shape signatures from the CAD operation sequence; it does not generate meshes.
4. .github/workflows/zero-to-cad-teacher.yml runs offline safety checks on relevant pushes. Explicit [study-zero-to-cad] commit messages or manual dispatch also run a bounded 90-minute CPU study. The image cache remains on the runner; only operation data, features and evaluations are temporary Actions artifacts. Standard GitHub policy and usage limits apply.

## Research limitations
- CAD programs have operations, not natural-language vehicle design briefs. Do not falsely claim free-text-to-vehicle training has been performed.
- Measure coverage from actual source records before claiming improvement; source hashes and official split checks reject leakage.
- A native modeling bridge must map these lessons into actual implemented AssetWright modeling operators (lofts, Boolean cutouts, shells, seams), then compare real generated GLBs.
- DINOv2 visual features must eventually supervise an owned student and beat independent nonvisual baselines before promotion.
- No teacher teaches production-ready Class-A automotive surfacing or welded seams without constructing and testing the corresponding native geometry controls.
- Preserve cumulative approved checkpoints in durable authorized storage, not solely temporary GitHub caches.

## Citations
Dataset: https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-100k
Vision teacher: https://huggingface.co/facebook/dinov2-small


## Verified first combined source study — November 3, 2026

Successful [GitHub Actions run 41668523988](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41668523988) read actual Zero-to-CAD 100K train and official validation examples and extracted real frozen DINOv2 Small embeddings:

- 96 distinct CAD training programs, safely inspected using native Python AST (never executed).
- 40 independent official validation programs.
- 96 samples with source-hashed reference image views and 96 frozen DINOv2 feature records of 384 values each (two provided CAD views per training sample).
- The owned operation-sequence grammar reduced heldout next-operation cross entropy from 2.979556 (unigram baseline) to 1.763503 (smoothed trigram), a 40.8132% decrease, over 774 heldout operation tokens.
- Heldout next-operation top-1 prediction accuracy: 21.5762% baseline vs 47.2868% learned trigram.
- Both the grammar and visual features remain research-only. They are not fused into a multimodal student yet and are not deployed to Android.

The experiment measures only regularities in *operation order*, not valid CAD execution, accurate part geometry, or free-text 3D generation. In particular, our source AST collector does not prove that arbitrary nested CadQuery expressions will always have complete semantic execution order. Further blind source families and native operator execution tests are required.

The original Zero-to-CAD image fields were raw bytes, not Pillow objects; this was corrected before the successful run. The resulting artifact is named 'assetwright-zero-to-cad-dinov2-research' and contains only source-provenance metadata, operation grammar/evaluation, and frozen numeric visual features—not the CAD scripts, STL/STEP files, or outside meshes.

## Visual distillation experiment
- An AssetWright-owned model now tries to predict a compressed 24-dimensional DINOv2 visual signature from a CadQuery operation sequence and conservative source geometry metadata. Its inference uses no image encoder or external CAD meshes.
- The workflow computes DINOv2 features for both the train and **independent official validation** split, joining them only with exact CAD source hashes and PNG view hashes.
- The research student must beat the train-set constant mean visual signature by at least 3% on official heldout examples or its visual-learning claim is rejected.
- Even if validated, it remains research-only and cannot create or deploy native 3D geometry until we build and evaluate a true visual-to-native-construction bridge.


## Verified operation-to-DINOv2 visual distillation — November 3, 2026

[Successful GitHub Actions run 41669695101](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41669695101) executed the complete CPU curriculum including a new AssetWright-owned visual distillation model.

- **96** independent training source CAD programs, with **96** source-hash-verified two-view image examples and 384-D DINOv2 Small frozen feature records.
- **40** official validation programs, with **40** source-hash-verified two-view examples and 384-D frozen DINOv2 feature records; no source IDs or code hashes overlap the training split.
- Previous own next-operation grammar result reproduced: **40.8132% reduction** in held-out cross-entropy versus a unigram baseline.
- The new *owned* visual student predicts a fixed 24-D projection of the frozen DINOv2 visual embedding from **CAD operation-sequence features**. It is trained in our code from random initial weights, and at inference uses no pretrained image encoder or external mesh generator.
- **Held-out validation MSE**: constant training-set feature mean **0.05835413**; owned visual student **0.04515133**, a **22.6253% reduction**.
- The student passed its predeclared 3% research-validation gate. The artifact includes an accepted *research-only* checkpoint, never approved for geometry generation or Android deployment.

Limitations: The learned 24-D signatures are compressed *teacher-feature representations*, not measured surface distance, actual mesh reconstruction, topology correctness, or aesthetically graded output. The construction program learner does not yet write executable native geometric operators from arbitrary text. To progress from this result, connect the learned visual semantics to new native cutout/loft/join operations and require independent GLB and visual-quality evaluation. Keep teacher-derived research weights separately from production until those gates pass.
