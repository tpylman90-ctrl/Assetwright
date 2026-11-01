# Assetwright Mini AI: private automatic learning loop (v0.2)

## What is actually automatic

**On Android**: generate an offline hover vehicle, adjust six geometry sliders,
then tap **Approve design · Teach Mini AI**. The corrected prompt + dimensions
are saved to the app's private storage, and future generations immediately use
the example. An exact prompt reproduces the approved parameters. No internet,
GPU, neural network training, or external account is required.

**On a home computer**: the `home_train.py --watch` process periodically
checks a **local** inbox for Android-exported approved examples. When files
change it validates provenance, deduplicates prompts, evaluates the upgraded
nearest-neighbor example memory against a held-out synthetic benchmark,
and writes a candidate pack + quality report. If the normalized MAE does not
regress more than 0.02, it also writes `approved_pack.json`.

**On Android again**: explicitly import that approved pack from device
storage; it affects later offline generations. The phone does **not**
automatically send prompts, assets or files to a public service.

This is a continuously updated **example-based parameter model**, not a
trained general text-to-3D neural network. GLB shape-understanding and
neural model training require further development.

## How to start the home trainer (Windows)

1. Download/clone the public Assetwright repository onto the home computer.
   Open PowerShell in the repository root and run `git pull` if already cloned.
2. Install Python 3 if necessary, verify `py -3 --version`.
3. Run `powershell -ExecutionPolicy Bypass -File tools/mini_ai/start_home_training.ps1`
   or `py -3 tools/mini_ai/home_train.py --watch`. This script only accesses
   files in your local repository. It requires no Python pip packages.
4. Keep that terminal open while you want the home watcher to run. To start
   at login, use Windows Task Scheduler to run the same command from the
   local repo directory. No home process has been installed or started for you.

## How to teach from your phone

1. In the Android app, generate a hover vehicle, move its dimension sliders,
   inspect the 3D preview and tap **Approve design · Teach Mini AI**.
2. Every approved example is saved privately, and the next generation
   immediately benefits. No home PC is required for this step.
3. Tap **Export approved learning examples** to create
   `assetwright-approved-examples.jsonl` in your device files.
4. Copy that file from your phone into
   `local-data/mini-ai/inbox/` on your home computer; use a unique name for
   each export if you want to retain older snapshots.
5. The watcher produces:
   - `local-data/mini-ai/trained/latest_report.json`
   - `local-data/mini-ai/trained/candidate_pack.json`
   - `local-data/mini-ai/trained/approved_pack.json` **only if validation passes**
6. Transfer `approved_pack.json` to the phone. Tap **Import home-trained model
   pack** in Assetwright and select it. Local device-approved corrections take
   precedence over the imported pack when the prompt matches.

The watcher runs without network access. File transfer from Android to PC and
back is **manual in this version**, pending a properly paired private LAN sync
service. Do not expose an unauthenticated home model-training endpoint to the
internet. If a new pack fails validation, retain the previous approved pack.

## Imported GLB libraries

The existing `tools/mini_ai/import_glb.py` scans the structure and reports
metadata for **user-verified CC0** GLB files. Those become candidates, **not**
training examples. To train on real GLBs, we must add inspected transforms,
part segmentation, geometry descriptors, accurate object descriptions,
user-verified labels and an evaluation pipeline. Never automatically train
from every free download; licenses vary.

Recommended future stages:

1. Add an opt-in local folder scanner for properly licensed GLBs, with hashes
   and source URLs recorded; quarantine missing-license assets.
2. Extract scene-corrected geometry features in Blender, plus consistent
   multiview renders for review. Preserve the originals locally.
3. Label controllable parameters and asset families; validate held-out sources
   and check near-duplicates before training.
4. Train a small geometry-parameter model on the home machine and export
   validated on-device inference weights. Keep older models for rollback.
5. Add LAN pairing + authenticated, user-approved synchronization between the
   phone and local computer without opening a public service.

## Privacy, retention and limits

- Phone feedback is in private app storage, capped at 500 approved examples.
- Android cloud backup of this app is disabled to avoid automatic upload of
  the learning records. **Uninstalling the app can erase them**; export a backup.
- All home data is under ignored `local-data/` folders and should never be
  committed into the public repository.
- No reference image is processed by the current offline Mini AI.
- The held-out test is a basic synthetic regression gate, not proof that a model
  is good at organic vehicle surfacing or general 3D construction.
- Run local tests: `python -m unittest discover -s tools/mini_ai -p 'test_*.py'`.
- The Android CI builds/tests remain the authoritative compilation gate.
