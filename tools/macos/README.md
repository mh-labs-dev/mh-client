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

The macOS build remaps personal source directories in Rust, C/C++ and Swift to
neutral build paths, including the vcpkg static dependencies. It refreshes those
dependencies and invalidates the Rust wrappers when their installed ABI changes.
Flutter debug symbols stay in `.local/macos-symbols/` and
must not be uploaded with the DMG. Native debug/local symbols are stripped before
signing, while exported symbols needed by plugins and FFI are retained. The final
app is scanned for personal home-directory paths (including binary and UTF-16
strings) and absolute symlinks; any match stops packaging. System library paths
and bundle-relative library references remain valid runtime dependencies.

After `flutter pub get`, the script adds a generated-only package entry to the
ignored `.dart_tool/package_config.json` and builds with `--no-pub`. This gives
Flutter's plugin registrant a stable `package:` URI for runtime lookup instead
of embedding its local file URI. A subsequent normal `pub get` may remove this
entry; the macOS build recreates it. Application code is not obfuscated.

After a build, archive the local Flutter symbols separately if crash symbolication
is needed; the next build may replace them. These settings only affect macOS.
