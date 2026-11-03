# Zero-to-CAD + DINOv2 Small: training AssetWright's own Mini AI

## Sources and permission
- Autodesk Research Zero-to-CAD 100K (https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-100k), Apache License 2.0, provides synthetic CadQuery construction programs, structured operator records, geometry metadata, and eight rendered views.
- Meta DINOv2 Small (https://huggingface.co/facebook/dinov2-small), Apache License 2.0, provides *frozen* image-encoder features. Its 384-D embeddings are NOT the same as the dataset's precomputed DINOv3 embeddings.

## Mandatory ownership boundary
Other models may provide visual supervision, but **AssetWright's own student and native geometry engine must construct final GLB assets**. No Tripo, external generator or downloaded CAD script can generate or replace native production models. This research code never imports outside meshes into the Android app.

## First bounded implementation
1. tools/mini_ai/zero_to_cad_ingest.py streams at most 96 official training and 40 validation examples, with 384/160 scan limits. It records only whitelist-approved operation names, source hashes, face counts, and two ephemeral render PNGs where available. Safe Python AST inspects fallback CadQuery methods without executing source code. No STL/STEP files are written to git or used by the production mesher.
2. tools/mini_ai/zero_to_cad_operation_student.py trains a compact original operation-sequence prior in AssetWright-owned code. It models next-operation probabilities conditional on preceding steps, and compares held-out cross entropy to a unigram baseline. The official train/validation splits remain distinct. At least a 2% gain is required for research acceptance. The output is never deployed to Android.
3. tools/mini_ai/zero_to_cad_dinov2_teacher.py reads only hashed reference PNGs, loads frozen DINOv2 Small on CPU, and emits 384-dimensional source-associated visual features. It produces no geometry. **These features are stored as research evidence, but do not yet update the operation grammar.** A measured multimodal-distillation model is a separate future step.
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
