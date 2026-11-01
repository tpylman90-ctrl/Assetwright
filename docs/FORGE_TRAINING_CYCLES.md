# Forge-run Assetwright research and training cycles

This is the workflow for: "Forge, train Assetwright again using free 3D assets."
The user needs only to ask in a ChatGPT conversation with GitHub connected.

## How it operates

1. Forge reviews the current Assetwright repository and last study evidence.
2. Forge commits a new numbered request to
   `training/requests/forge_cycle.json` in the public Assetwright repo.
3. GitHub Actions **Forge CC0 Asset Study** starts automatically on that
   request (or can be manually dispatched with `workflow_dispatch`).
4. The action uses **Poly Haven's official public API** with an identifying
   User-Agent. It selects at most 8 mechanical/vehicle-related CC0 models,
   examines metadata (mesh budgets, bounding ratios), and attempts to
   inspect small, explicitly linked .glb variants if available.
5. The compact report is uploaded as the `forge-cc0-shape-study` Actions
   artifact. No downloaded GLB is committed into GitHub. No credentials.
6. Forge can examine the report during the same conversation, improve
   modeling techniques, add tests, and publish separately validated
   Forge lessons. No unreviewed geometry is deployed to Android.
7. Android users who enabled Forge Lessons receive new validated recipes.
   Mesh-engine changes still require a new APK.

## Important distinction

**The automated asset-study job is source ingestion and shape study only.**
It does NOT train Android AI weights, learn full mesh topology, infer editable
construction operations from arbitrary models, or claim neural training.
Those are separate extraction, labeling, model-training and evaluation steps.

Forge is not a persistent background process. A running GitHub Action cannot
automatically invoke ChatGPT to continue its work after the chat ends.
The user can request a new interactive training cycle whenever desired.

## Sources, licensing and privacy

- Source: https://polyhaven.com and https://api.polyhaven.com
- Assets: CC0 — https://polyhaven.com/license
- API terms: https://github.com/Poly-Haven/Public-API/blob/master/ToS.md
- Live API use requires identifiable requests and visible "Powered by Poly
  Haven" credit. These reports record the credit and source links.
- The website is not scraped; this process uses its documented API.
- Compact structure statistics are retained in the report; third-party
  mesh binaries stay in temporary runner directories.
- Limits: 8 selected model records, 12 MiB per GLB, 12-minute runner timeout.
- Not every Poly Haven model is a vehicle. Semantic suitability needs
  independent review; unrelated object geometry is not silently injected
  into the hover-vehicle predictor.

## How to repeat

Ask Forge: **"Run another Assetwright training cycle. Focus on vehicle body
panels, engine attachments and hard-surface topology."**

Forge increments the request's `cycle` value, sets the focus and commits.
The GitHub workflow collects material for review without manual downloading.

Results: https://github.com/tpylman90-ctrl/Assetwright/actions/workflows/forge-asset-study.yml

A real recurring schedule would be separate, with an explicit automation
or GitHub schedule trigger. A scheduled job could collect data unattended,
but would not cause the ChatGPT assistant to autonomously keep editing code.
