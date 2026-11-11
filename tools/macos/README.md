# Build for macOS

Requires macOS, full Xcode, Homebrew and Python 3.11 or later. Run from the repository root:

```sh
bash tools/macos/prepare-macos.sh
python3 tools/controller_profile.py validate config/controller.default.json
python3 tools/macos/build-macos.py --version 1.5.1-mh.10-preview --controller-profile config/controller.default.json
```

The setup installs Rust 1.81.0, Flutter 3.24.5, pinned vcpkg and NASM 2.16.03 under `.cache/mh-tools/macos/`. Homebrew supplies CMake, Ninja, Autotools and CocoaPods.

The script builds the native library, helper and Flutter app for the host architecture, then writes the app, DMG, build manifest and checksums to `release/macos/<version>/<architecture>/`. The minimum target is macOS 12.3. Select a new version for each build.

`--controller-profile` accepts a custom public connection profile. Omitting it builds a controller preview with login disabled. All builds use outgoing-only mode and disable incoming TCP listening. Server settings remain editable in configured builds.

Packages use ad-hoc signing. Developer ID signing, notarization and App Store distribution require a separate release process.
