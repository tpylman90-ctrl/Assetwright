# Android signing

Signed release APKs use the same upload key on every update. Losing or replacing the key prevents Android from treating later APKs as updates to existing installs.

## Required GitHub Actions secrets

Add the values in **Settings → Secrets and variables → Actions**:

- ANDROID_KEY_ALIAS
- ANDROID_KEY_PASSWORD
- ANDROID_KEYSTORE_PASSWORD
- ANDROID_KEYSTORE_BASE64

The workflow decodes the Base64 value into a temporary runner file, builds the release APK, and uploads the artifact. The repository ignores keystore files and local secret files.

Keep a separate private backup of the keystore and passwords. Never put the values in a commit, issue, or public build log.
