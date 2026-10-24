# Private Blender workbench

Use this workbench to run Blender on the laptop through GitHub Actions. It avoids a ChatGPT MCP connector: ChatGPT updates a run request in the private repo, GitHub starts the self-hosted Windows runner, and the workflow returns the GLB and preview.

The public Assetwright repo remains the source for the Android app and Blender generator scripts. The private workbench contains only the runner workflow and a small run request. The workflow checks out the current public generator at run time.

## Storage and job limits

- One local Blender workflow runs at a time.
- Generated files stay in the runner's temporary directory and are uploaded as an Actions artifact; they are not committed to Git.
- Each artifact expires after 3 days.
- The workflow stops if outputs exceed 250 MiB.
- Keep only selected, approved GLBs in long-term project storage.

## Create the private workbench

Create a new private GitHub repository named `Assetwright-Workbench`. Copy these templates from the public Assetwright repository:

- `docs/workflows/private-blender-runner.yml.example` → `.github/workflows/blender.yml`
- `docs/workflows/private-run-request.json.example` → `run-request.json`

Commit them to the private repo's `main` branch.

## Register the laptop as a runner

In the private workbench repo, open **Settings → Actions → Runners → New self-hosted runner**, choose **Windows x64**, and follow the commands GitHub shows. Give the runner the custom label `assetwright-blender` in addition to the default labels. Keep the runner process open while a Blender job is needed.

The runner invokes the Blender installation already on the laptop. Make sure `blender.exe` is available on PATH. GitHub's registration token is short-lived; use it only in the local runner setup screen and do not paste it into chat.

The workflow runs only for changes to `run-request.json` on `main` or a manual `workflow_dispatch`. It has no pull-request trigger. GitHub warns that self-hosted runners attached to public repositories can be compromised by untrusted pull-request code, so this runner belongs in the private workbench. Avoid adding untrusted collaborators or pull-request triggers. See [GitHub's self-hosted runner security guidance](https://docs.github.com/en/actions/reference/security/secure-use).

## Starting a generation

Once the private repo exists and the runner is online, ChatGPT can update `run-request.json` through the connected GitHub account to start a run. Each request must use an allowlisted generator. The first template supports only `cargo_drone_demo`; prompt-driven and higher-detail asset families will be added to the public generator and picked up by later runs.

Open the workflow run in **Actions** and download its `assetwright-blender-<run id>` artifact. It includes the GLB and preview. Keep the run request small; generated model files are not committed to either repository.
