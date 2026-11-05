# Licensed CAD Shape School V2 — external teaching experiment

Dataset: Autodesk Research Zero-to-CAD 100K, Apache-2.0.
https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-100k

This study expands the earlier 96 training / 40 validation CAD source
curriculum to up to 1600 source-hashed official train programs and 400
new official validation programs. The first 256 validation records are
excluded because earlier runs exposed that prefix. All examples come
from a single explicitly pinned upstream dataset commit.

The pipeline only parses whitelisted construction-operation names and
the provided B-rep face-count metadata; it NEVER executes downloaded
Python, imports STEP/STL geometry as a generated asset, or uses outside
AI to generate a final GLB. Native Kotlin remains the sole mesh source.

Student 1 learns which operation concept is likely next from the
preceding operation sequence: profile, volume, cut, finish, pattern,
transform. It must beat training-only unigram cross entropy by 7.5%
and top-1 accuracy by 3.5 absolute percentage points on official
heldout examples.

Student 2 predicts log1p(original face count) from operation names.
The source face-count target is never an inference feature. It must
beat train-median heldout log-MAE by 5% and a fitted sequence-length
baseline by 1.5%.

Teaching cards include source support and observed concept transition
probabilities, plus plainly marked educational explanations. Learned
statistical correlations are not claimed to prove causal/engineering
intent. Native transfer remains partial for lofts, sweeps, through-bores
and blind sockets. True CSG, arbitrary fillets, G2 continuity and
connected patterns remain unsupported, pending independent GLB tests.

All fixed gates must pass (including >=1000 train, >=250 validation,
source hash/ID disjointness, immutable source SHA and zero Android
promotion). Weak students remain rejected, with evidence saved.
Previously inspected evaluation rows are retired for future studies.

This teaches construction syntax, conceptual relationships and a
complexity proxy. It is NOT evidence of accurate outside-CAD geometry
reconstruction, independent feature design, or a production-ready
shape generator. Frozen DINOv2 visual teaching and earlier native
shape/connected-branch checkpoints are separate and unchanged.
