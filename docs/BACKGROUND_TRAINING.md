# Assetwright background training — private home and Android

## What runs automatically

Assetwright's current offline learner predicts six editable hover-vehicle
parameters from approved examples. The worker detects **new user-approved
feedback**, validates it against held-out examples, and publishes an updated
**example-memory** model pack if the regression gate passes. This is not
neural training from raw GLBs or a self-running ChatGPT instance.

The worker never publishes prompts, geometry or private learning records
to GitHub. Real GLBs remain license-reviewed, untrained candidates.

## A. Install unattended Windows worker

1. Clone the public Assetwright repository onto the home Windows PC.
   Install Python 3 and confirm the command: py -3 --version
2. Open PowerShell at the Assetwright repository root and run:

    powershell -ExecutionPolicy Bypass -File tools/mini_ai/install_background_training.ps1 -StartNow

3. The task starts on **user logon** and runs while signed in and awake.
   Windows Task Scheduler may require a permission adjustment for the
   current account. It is not a Windows service that runs before login.
4. Check its status and log:

    Get-ScheduledTask -TaskName "Assetwright Mini AI Background Training"
    Get-Content local-data/mini-ai/background-worker.log -Tail 40

5. To remove the task without deleting training data:

    powershell -ExecutionPolicy Bypass -File tools/mini_ai/uninstall_background_training.ps1

## B. Fully automatic phone-to-PC folder transfer over home Wi-Fi

For local-only transfer, install free Syncthing on Windows and the maintained
Syncthing-Fork app on Android; the original Syncthing Android wrapper was
discontinued. Pair the devices, and restrict to LAN if desired: turn off
relay connections, global discovery and NAT mapping, leaving LAN discovery
enabled. Use only trusted devices.

1. On Android, create a directory such as Documents/AssetwrightLearning.
2. Pair Syncthing devices, then share *only* that folder with Windows.
3. Set the matching Windows folder to:

    <Assetwright repository>/local-data/mini-ai/sync

4. In Assetwright, tap **Enable background training folder sync** and select
   that Android folder using the system picker. The permission is specific
   to the folder you selected.
5. Generate an asset, adjust its shape, and tap **Approve design · Teach
   Mini AI**. The app writes approved-phone.jsonl to that folder.
6. The sync program copies it to your PC while both devices are connected.
   The home watcher detects the new file, runs its quality gate, and, only
   on a passing result, writes approved_pack.json in the shared folder.
7. Syncthing copies the pack back to Android. Android WorkManager checks
   for new packs approximately hourly (the OS may delay it), and the app
   also checks upon opening.

The phone still generates offline when away from home. The PC must be
awake and logged in for training, and the devices need a working LAN
connection for LAN-only file synchronization.

**Never sync the entire repository, private home data folder, or Android
app-private directory.** The shared directory is excluded from Git.

## C. Verify the end-to-end learning loop

Look for approved-phone.jsonl under the synced folder on Windows, then
inspect local-data/mini-ai/trained/latest_report.json. The report includes
example counts, baseline and candidate normalized error, and a status.
A passing model appears as approved_pack.json; the app should show a
home example count after importing it. Re-run the same corrected prompt
to verify its learned dimensions.

Use the model-review ZIP to give Forge a specific GLB to analyze and
recommend corrections. ChatGPT **cannot autonomously access the private
PC learning folder**. Scheduled assistant reviews can analyze GitHub
code and reports only when those reports are explicitly made accessible.

## Boundaries and safety

- Only approved parameter examples train the current mini AI. External CC0
  GLBs are merely indexed for future geometry-learning research.
- No neural network weights are trained yet. Build a separately evaluated
  tiny neural parameter regressor in a future version if desired.
- Poor or invalid feedback is rejected; keep previously approved pack.
- Windows may pause work while sleeping; WorkManager is not exact-time.
- Paired Syncthing devices exchange data only through the configured sync
  software; Assetwright itself has no server or cloud inference dependency.
- Disabling sync preserves on-device learning memory. Uninstalling the app
  may delete private training data, so periodically export backups.
- Do not publish feedback files or third-party GLBs in the public repository
  without deliberate review and appropriate rights.
