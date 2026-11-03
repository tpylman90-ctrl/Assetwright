# AssetWright — frozen operation classifier and separate strength calibration

## Motivation

The first mistake-driven clinic worsened unseen operation selection
(77.78% to 70.37% on the clinic's already observed blind test), even as it
improved strength prediction error (0.309 to 0.284). That checkpoint was
rejected, and is NOT used as the starting model.

This new experiment uses the **last validated original model stored in a
durable GitHub prerelease**, verifies its SHA against previously audited
native GLBs, and freezes the full operation classification weights and biases.

## Separate skills

* **Which operation?** The pretrained *AssetWright-owned*, narrowly
  supervised operation classifier is frozen byte-for-byte. Its scores and
  abstentions cannot change due to calibration.
* **How strong?** A separate own sparse regression head is updated from
  correct, explicitly authored operation-strength pairs (0.30, 0.60, 0.90).
  It sees correction examples and approved earlier training examples, not
  raw source CAD scripts, third-party meshes or teacher-generated proposals.
* **Do old skills still work?** The previously used 36 original holdout
  cases are measured only as a retention gate, not used for gradient updates.
* **Does it work on unfamiliar wording?** Candidate selection uses the
  27 development cases from the previous clinic. Then a **new, separately
  authored 36-case test** with 12 unseen templates across all three
  operations is evaluated exactly once, *after* candidate selection.
  The prior clinic's already seen blind set is explicitly excluded from
  training and evaluation.

## Hard acceptance rules (defined before running the new blind set)

The test must show a minimum 0.02 absolute improvement in conditional
strength MAE; absolute MAE no greater than 0.17; operator accuracy at
least 75%, without dropping relative to the original frozen classifier;
monotonic low/moderate/high strengths on at least 70% of blind template
groups; and no more than 0.02 regression on prior-skill strength MAE.

"Conditional" MAE uses the **correct operation** to measure strength
calibration independently of operation selection. It is *not* an end-to-end
asset quality metric, and operation accuracy is reported separately.
An approval requires the actual native GLB topology audit as a final
independent gate before a research-only checkpoint is released.

## Free, resumable provenance

The GitHub workflow loads the preserved release
`assetwright-native-verified-a4c94b1abb48`.
A new release is created only after all blind and native GLB gates pass.
A failure is documented, not automatically fixed by weakening thresholds.
Research weights remain separate from Android installation.

Zero-to-CAD and DINOv2 remain valuable CAD and visual teachers, but they
do not provide the operation-and-intensity natural language labels
used by this specific calibration experiment. All resulting native GLBs
are constructed by AssetWright's MiniGeometry/GlbWriter.

## Limits

This curriculum has three native geometric operations and small original
language templates. It does not demonstrate ability to model arbitrary
objects or create professional automotive Class-A surfaces. A genuine next
milestone requires learning parameters from measured target geometry
and testing on new object families, not merely more synonyms.
