# Local Blender worker

Assetwright's detailed modeling work runs on the user's PC. GitHub Actions remains the reproducible build and validation path; it is not the main modeling workstation.

The local worker exposes three MCP tools:

- `blender_status` checks whether Blender is installed and reports its version.
- `generate_cargo_drone_demo` runs the allowlisted Blender generator and creates a new GLB and PNG preview.
- `get_latest_blender_preview` returns the last render to ChatGPT for visual review.

The worker binds to loopback (`127.0.0.1`) and uses ChatGPT's Secure MCP Tunnel for private access. It does not expose an open network port. It accepts no arbitrary shell commands, Python scripts, Blender arguments, or output paths from ChatGPT. Generation is limited to one run at a time, has a 15-minute timeout, and writes to a unique folder under `generated/local/`. ChatGPT should request confirmation before calling the generation tool.

## Windows setup

Install Blender and Python 3.10 or newer. Clone the Assetwright repository, then open PowerShell in the repository folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\blender\start-local.ps1
```

The launcher finds Blender from PATH or the standard Program Files location, creates a local Python virtual environment, installs the MCP SDK, and starts the server at `http://127.0.0.1:8765/mcp`. Keep the terminal open while using the connector.

If Blender is installed in a custom location, set `ASSETWRIGHT_BLENDER` to the full path to `blender.exe` before starting the script.

## Connect ChatGPT

In ChatGPT web, add a custom MCP server and choose **Tunnel** with an available **Secure MCP Tunnel**. Point the tunnel at the local MCP endpoint shown by the launcher, then scan the tools. Keep the connection private; do not publish a public unauthenticated URL. Enable the generation action as a write action that requires confirmation.

Call `blender_status` first. Then call `generate_cargo_drone_demo` only after approving the run. ChatGPT can inspect the rendered preview with `get_latest_blender_preview`. The GLB remains on the laptop at the returned path.

## Current scope

The bridge proves local execution and review using the cargo-drone demo. It is not yet connected to the Android app or to an automatic prompt-to-geometry model. Add new asset families as explicit allowlisted Blender generators, with bounded parameters and budgets. Keep user edits and before/after previews as training records only after the user opts into retaining them.
