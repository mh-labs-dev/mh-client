# Release files

Build outputs use `release/<platform>/<version>/<architecture>/`.

| Platform | Architecture | Build entry |
|---|---|---|
| Windows | x64 | [Windows build](../README.md#build) |
| macOS | arm64, x86_64 | [macOS build](../tools/macos/README.md) |

Each Windows release provides one portable EXE with the application and license embedded. Source snapshots, checksums and expanded build files are retained under `.local/windows-builds/<version>/x64/`. macOS builds produce an app and DMG. Android and iOS builds are not available yet.

Upload the selected version's files as GitHub Release assets. Binary outputs remain outside Git; the release notes are maintained in [docs/user/releases](../docs/user/releases/).

Desktop packaging checks for local build paths. Windows Dart symbol maps are retained with the local build records under `debug-symbols/`; keep them for diagnosing that exact build.
