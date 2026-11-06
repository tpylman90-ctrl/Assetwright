# Forge Mini v7 — Shape Identity Before Deformation

## Why this is necessary

V6 generated 8 actual native form archetypes, trained six real sessions and reconstructed 768 original Kotlin GLBs. Its development-selected balanced student achieved 60.42% form accuracy and 90.10% operation accuracy on 192 unseen transformations. Despite better geometry than the generic prior, it was not better than leaving the correct form unchanged, so the gate REJECTED promotion.

The worst unseen identity confusions were BOX_MODULE (7/24 correct), BARREL (4/24) and BLADE (3/24); CANOPY_POD was 24/24 and TRUSS_BEAM 23/24. Previous 16x16 paired images were built to infer deformation, not distinguish starting shapes.

## Independent form encoder and existing knowledge

The NEW identity encoder uses **three original undeformed baseline views**: side, front and top, 32x32 grayscale occupancy each. It learns shape identity independently of the six native operation/strength heads, which remain **completely frozen**. Its 9 output classes cover eight original form archetypes plus legacy shell. The experimental v6 balanced-forms checkpoint is source-SHA verified; v6 was NOT previously approved for production. The older verified v3 teacher-free checkpoint is unchanged.

This is a true new neural learning experiment, not a claim of arbitrary text-to-3D or a deployed Android checkpoint.

## More distinct sources; no dimension-to-label shortcut

V7 creates 2,040 entirely new original Kotlin GLBs: 40 TRAIN form families (5 independent physical dimension sets per each of eight archetypes), 16 separate DEVELOPMENT families (2 independent sets per form), and 16 untouched BLIND families (2 other sets per form). Each form receives the **same dimensions within a variation**, making dimensions and tessellation incapable of revealing archetype by shortcut. Across six original operations and different strength values, the curriculum contains 1,200 train, 384 dev and 384 blind transformations plus 72 original baselines.

The training-only identity data is correctly counted as **56 genuinely distinct original baseline shapes**: 40 new source families and 16 previous v6 training-only baselines. Transform/strength examples that reuse a baseline are NOT falsely counted as independent shape identity examples. Earlier exposed v6 development/blind families are excluded.

The source audit confirms original GLB source hashes, multiple topologies, correct form labels, disjoint cohorts, and matched orthographic camera rendering. Only old and new TRAIN baseline images enter neural optimization; DEV selects model checkpoints; BLIND is used after method selection.

## Three fair, free CPU experiments

Each of the following gets two separately seeded sessions under the same total 1,800-second active gradient budget:

- Three-view identity: a balanced standalone form classifier.
- Contrastive identity: the same shape network plus same-class / different-class representation loss.
- Hard distinctions: the same input with extra correct-label emphasis on BOX_MODULE, BARREL and BLADE, plus their confused neighbors.

All sessions use the same real original source shapes, same CPU budget, and preserve the exact v6 action and strength network. Only 16 new development source families choose the checkpoint/method.

After all choices are frozen, the study evaluates **384 completely fresh blind transformations** and builds **1,536 actual Kotlin GLBs** from the frozen parent plus three independently learned identity heads. It uses actual surface Chamfer distance across different triangle counts, not matched-index errors valid only for a single generic mesh.

## Required checks for research-only review

The predeclared gate requires at least 80% correct form identity, at least seven of eight classes with nontrivial new-family recognition, all eight generated form types, at least four output topologies, minimal generic-shell fallback, stable shape identity across native deformations, 12% lower true source-surface error than the frozen v6 research parent, and geometric error below leaving the correct source unchanged.

Exact old operation/strength outputs are verified across ALL blind GLBs; those neural weights never receive gradients. A green workflow does not automatically mean success. Regardless of gate outcome, newly learned research identity weights and 3D evidence are permanently retained in public AssetWright with source hashes. No research weights are deployed to Android automatically.

## Compound geometry is later, not falsely declared complete

NativeComposedFormLab already supports bounded original two-to-four-operation construction programs, but it is not yet a trained program decoder. The next stage can train sequences AFTER the identity predictor demonstrates improvement without silhouette collapse.

Pipeline entrypoint: .github/workflows/forge-mini-shape-identity-v7.yml

Only the PUBLIC repository tpylman90-ctrl/Assetwright is modified. All code relies on free Kotlin/PyTorch/GitHub Actions.
