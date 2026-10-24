# Generation service contract

## First provider adapter

Use a server-side adapter around the Tripo OpenAPI for the first end-to-end prototype. The Android app must call Assetwright's service, never Tripo directly; provider credentials must remain on the server. Tripo tasks are asynchronous, so the Assetwright service owns submission, status polling, and immediate result download.

The adapter should start with Tripo H3. Its API supports text-to-model and image-to-model inputs, standard and detailed quality controls, and a smart low-poly option. Keep provider selection behind an interface so a self-hosted model can replace it later without changing the Android API.

Tripo's API is prepaid and generation consumes credits. Do not enable live generation until a server-side API key is configured and the app can show the expected credit cost before submission. Never submit test jobs from CI.

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

## Service boundaries

- One generation worker processes a single model job at a time on the selected backend.
- Persist job state outside process memory so a restart does not lose track of running provider jobs.
- Enforce per-account active-job limits and request-size limits on the server.
- Keep provider keys, authentication tokens, and provider task IDs on the server.
- Store the final GLB under Assetwright control; do not expose short-lived provider URLs to the app.
- Record provider-reported credits with the job so a future confirmation screen can show cost before submission.
- Validate GLB structure and report actual mesh statistics before allowing export.

## Provider references

- [Tripo API authentication and asynchronous task flow](https://docs.tripo3d.ai/get-started/quick-start.html)
- [Tripo H3 text-to-model controls](https://docs.tripo3d.ai/model-generation/text-to-model-v3-0-v3-1.html)
- [Tripo H3 image-to-model controls](https://docs.tripo3d.ai/model-generation/image-to-model-v3-0-v3-1.html)
- [Tripo API pricing](https://docs.tripo3d.ai/get-started/pricing.html)
