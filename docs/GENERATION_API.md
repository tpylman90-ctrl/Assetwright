# Generation service contract

## Assetwright-owned generation workflow

Assetwright should turn a prompt and optional reference image into a game-ready mesh with its own Blender-based pipeline. Do not send generation jobs to a paid 3D-model API.

The initial workflow is:

1. Convert the prompt and reference image into a structured asset brief: asset family, silhouette, dimensions, materials, and optional details.
2. Use Blender Python generators for a small set of supported game-asset families. Build geometry from editable parameters and modular parts, not from a one-image depth extrusion.
3. Apply materials and image-derived details, then create UVs, a mobile-friendly mesh budget, collision geometry, and optional LODs.
4. Validate and export a GLB for preview and game-engine use.

This approach is intentionally scoped. A single image does not reveal hidden sides or exact geometry, so the first release should prioritize asset families with controllable geometry (for example, sci-fi crates, barrels, small drones, and weapon props). More families can be added as their Blender generators become reliable. The reference image guides proportions and surface treatment; it is not treated as complete 3D data.

Blender is the geometry and asset-processing engine, not an image-to-3D AI model. During development, concept images can be created through our existing image workflow. For a standalone app, users can start with an uploaded reference; prompt-only concept-image generation would require an image model that we control or host. Keep that choice separate from mesh generation.

## Compute plan

Run one Blender job at a time. Geometry generation, cleanup, and GLB export can run in a CPU worker; GPU compute is only needed if we later host an image-generation model. This avoids paying a per-asset 3D API fee and keeps the mesh pipeline under our control. Keep jobs queued and bounded, and store their outputs as Assetwright-owned files.

The current Android app calls Assetwright's versioned service only. The provider API key field and paid 3D-provider adapter are not part of this plan. Never submit live generation jobs from CI.

## Android-to-service API

All endpoints are versioned under `/v1`. The service requires authenticated requests over HTTPS. The provider API key is not an Android build secret and must never be shipped in the APK.

### Create a generation

`POST /v1/generations` as multipart form data:

| Field | Type | Rules |
| --- | --- | --- |
| `prompt` | text | Optional if an image is present; maximum 1,000 characters |
| `profile` | text | `mobile`, `balanced`, or `high_detail` |
| `reference_image` | file | Optional; one image, PNG/JPEG/WebP, maximum 20 MB |

The service accepts a prompt, an image, or both. A successful request returns `202 Accepted` with an Assetwright job ID and initial status. Each account may have one active generation at a time. A second create request while a job is active returns `409 generation_in_progress`; the app should keep the current job screen and let the user retry after it finishes.

Example response:

```json
{
  "job_id": "gen_01J...",
  "status": "queued",
  "profile": "mobile",
  "progress": 0
}
```

### Read generation status

`GET /v1/generations/{job_id}` returns one of:

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

Example while running:

```json
{
  "job_id": "gen_01J...",
  "status": "running",
  "progress": 42
}
```

On success, return a service-owned, authenticated download URL rather than the provider's temporary URL:

```json
{
  "job_id": "gen_01J...",
  "status": "succeeded",
  "progress": 100,
  "asset": {
    "download_url": "https://api.assetwright.example/v1/assets/asset_01J.../file",
    "format": "glb",
    "triangle_count": 18400,
    "texture_size": 1024
  }
}
```

The service should download provider outputs as soon as the provider marks a task successful; Tripo result URLs are temporary. Keep generated assets available long enough for the user to preview and export them.

## Initial game-asset profiles

The API profile is a target, not a promise from the generator. The service must inspect the generated mesh and report actual triangle and texture sizes.

| Profile | Initial target | Provider behavior |
| --- | --- | --- |
| Mobile | Up to 20,000 faces; 1K texture | Request smart low-poly output |
| Balanced | Up to 80,000 faces; 2K texture | Standard geometry and texture |
| High detail | Up to 150,000 faces; up to 4K texture | Detailed geometry and texture |

If the provider exceeds the profile budget, mark the asset as over budget and pass it through a mesh-reduction stage before presenting it as game-ready. Do not silently claim a mesh meets its profile based only on the generation request.

## Learning loop

Capture a learning record after every generation, but do not change the production generator from one unreviewed sample. A single thumbs-up or an unedited export says little about hidden geometry; useful learning data includes a corrected asset or a clear comparison against the result.

For each job, save:

- The prompt, user-provided reference image(s), selected game profile, and any requested views.
- The structured asset brief and Blender generator/template version used.
- The editable geometry parameters and the exported GLB.
- Turntable renders from consistent front, side, rear, and top views.
- Mesh statistics and any validation failures.
- User feedback: accepted, edited, or rejected; which parts were wrong; and the actual parameter or geometry changes made.

Make feedback easy to give in the app. Offer a short reason list (silhouette, proportions, missing parts, hidden-side layout, materials, or detail) and let users adjust the relevant asset parameters. Save the before/after pair so the correction can be replayed and reviewed.

Improve in stages:

1. After each run, add its record to a versioned dataset, with the user's permission to retain the images and model for improvement.
2. Initially improve deterministic Blender templates and prompt-to-brief rules from these corrections. This gives a fast, inspectable learning loop without needing to train a large model.
3. Once the dataset contains enough reviewed examples, train or fine-tune the component that predicts asset briefs or geometry parameters. Keep a held-out validation set and compare each candidate against the current version.
4. Promote only candidates that improve measured geometry and user acceptance. Version every generator and model, retain rollback ability, and keep training asynchronous to asset generation.

To learn hidden geometry, gather supervision for unseen sides. When a user has only one reference image, mark unseen geometry as an inferred design choice. Use user edits, extra views, and accepted/rejected turntable views to teach the system what belongs on the rear and sides. Single-view reconstruction is inherently ambiguous; more complete views and corrections provide stronger evidence.

## ChatGPT training bridge

Expose the run-review workflow through a private MCP server backed by Assetwright's service. Connect that server to ChatGPT as a custom MCP app. This lets ChatGPT inspect saved runs and return structured corrections without placing a model-provider key or unrestricted Blender shell inside the Android app.

Initial MCP tools:

| Tool | Access | Purpose |
| --- | --- | --- |
| `list_generation_runs` | Read | Find recent runs by status, asset family, or profile |
| `get_generation_review` | Read | Return prompt, asset brief, generator version, mesh metrics, and turntable images |
| `propose_geometry_patch` | Write, approval required | Save a constrained JSON patch for an existing asset recipe |
| `run_blender_revision` | Write, user confirmation required | Queue a revision using an allowlisted Blender generator and a patch |
| `record_training_feedback` | Write, user confirmation required | Save accepted, edited, or rejected labels and before/after outputs |
| `queue_training_candidate` | Write, explicit confirmation required | Start an offline candidate training/evaluation job after the dataset gate is met |

The assistant should inspect the turntable and mesh report, propose changes to named geometry parameters, and explain the expected effect. It must not execute arbitrary Python from prompts, images, or generated scripts. Blender runs in a restricted worker with allowlisted generators, time and resource limits, and no access to signing secrets.

Keep reads available for review. Require confirmation before queuing a Blender revision or changing the training dataset. Candidate training stays offline until it passes the held-out comparison; promoting a candidate to production remains a separate user-approved action.

Connect ChatGPT to the MCP server over authenticated HTTPS or a private Secure MCP Tunnel. Install and configure the custom MCP app from ChatGPT web; the server must be reachable through one of those supported paths. Keep authentication and dataset-retention choices explicit. Do not expose the server publicly without authentication.

## Service boundaries

- One generation worker processes a single model job at a time on the selected backend.
- Persist job state outside process memory so a restart does not lose track of running provider jobs.
- Enforce per-account active-job limits and request-size limits on the server.
- Keep provider keys, authentication tokens, and provider task IDs on the server.
- Store the final GLB under Assetwright control; do not expose short-lived provider URLs to the app.
- Record model name, profile, and GPU worker time per job; enforce a monthly spend limit at the hosting layer.
- Validate GLB structure and report actual mesh statistics before allowing export.

## Provider references

- [Tripo API authentication and asynchronous task flow](https://docs.tripo3d.ai/get-started/quick-start.html)
- [Tripo H3 text-to-model controls](https://docs.tripo3d.ai/model-generation/text-to-model-v3-0-v3-1.html)
- [Tripo H3 image-to-model controls](https://docs.tripo3d.ai/model-generation/image-to-model-v3-0-v3-1.html)
- [Tripo API pricing](https://docs.tripo3d.ai/get-started/pricing.html)

## Blender references

- [Blender Python API](https://docs.blender.org/api/current/)
- [Blender background mode](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html#background-mode)
