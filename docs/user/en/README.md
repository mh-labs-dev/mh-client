# MH

[中文](../../../README.md) · [English](README.md)

MH is a remote Mac controller modified from [RustDesk 1.5.1](https://github.com/rustdesk/rustdesk), licensed under [AGPL-3.0](../../../LICENCE).

The Windows preview provides account login, a device list and a connection action. Sessions require an available Pro Server, enrolled Macs and appropriate permissions. The server is deployed separately. A Windows x64 preview is available. macOS arm64 supports local controller-only preview builds; service configuration and live-session verification are still required.

[Usage](USAGE.md) · [Release notes](../releases/1.5.1-mh.5-controller-test.md)

## Dependencies

- Windows x64, Git and Python 3.12.
- Visual Studio 2022 with Desktop development with C++ and the Windows SDK; CMake available on PATH.
- Rust 1.75.0, Flutter 3.24.5, pinned vcpkg and libclang 15.0.6.1, prepared by the scripts below.

## Build

Run PowerShell from the repository root. Prepare dependencies for the first build:

```powershell
git submodule update --init --recursive
python -m pip install -r tools/windows/requirements.txt
./tools/windows/prepare-windows.ps1 rust
./tools/windows/prepare-windows.ps1 flutter
./tools/windows/prepare-windows.ps1 vcpkg
./tools/windows/prepare-windows.ps1 clang
python tools/windows/prepare-sdk.py
python tools/windows/prepare-bridge.py
python tools/windows/prepare-branding.py
python tools/windows/prefetch-msys.py
./tools/windows/prepare-native.ps1
```

Builds use [config/controller.default.json](../../../config/controller.default.json) for the MH service addresses, server public key and secure WebSocket settings. This public configuration is maintained with the source. Server settings remain editable in the client.

Validate, build and package:

```powershell
python tools/controller_profile.py validate config/controller.default.json
./tools/windows/build-windows.ps1
./tools/windows/package-windows.ps1 -Version 1.5.1-mh.6-controller-test
```

The version number is an example. Output is stored in `release/windows/<version>/x64/`. Builds default to the login-first controller. Rebuild both native code and UI when changing configuration or variants.

For a custom service, copy `config/controller.example.json` to `.local/controller-profile.json` and pass the same `-ControllerProfile` path to both Windows build and packaging commands. Pass `-ControllerProfile ''` explicitly to build the general MH variant. Saved client network settings take precedence over build defaults.

To build macOS with the same public defaults, use the macOS build script after preparing its dependencies:

```sh
python3 tools/controller_profile.py validate config/controller.default.json
python3 tools/macos/build-macos.py --version 1.5.1-mh.10-controller-test --controller-profile config/controller.default.json
```

## Shared MH desktop behavior

Windows and macOS share the branding initialization, controller defaults and WebSocket relay policy in `src/mh/`, plus the existing Flutter theme, logos, login and device list. The native MH initialization is not enabled for iOS, Android or Linux.

Desktop builds must configure both layers:

- Flutter: `--dart-define=MH_DESKTOP=true` enables MH appearance. The legacy `MH_WINDOWS=true` flag remains supported.
- Flutter: `--dart-define=MH_CONTROLLER=true` enables the login-first page within MH appearance; use `false` for ordinary MH builds.
- Flutter: `MH_CONTROLLER_CONFIGURED=false` disables login in unconfigured previews; existing Windows builds default to enabled.
- Rust: `MH_CONTROLLER=true` enables outgoing-only mode independently of server configuration.
- Rust: `MH_CONTROLLER_PROFILE` contains the public profile JSON for controller builds; unset it for ordinary builds.

The Windows build script sets these inputs together. Controller builds retain the `MH Test` configuration name, outgoing-only connections and disabled TCP listening. Ordinary builds retain the `MH` name. Validate profiles with `python tools/controller_profile.py validate <profile-path>`; the previous Windows validation command remains compatible.

macOS builds always enable outgoing-only controller mode. Without a server profile, the login page is shown with login disabled; host ID, password and permissions panels are not shown. Builds use the shared inputs; see [build instructions](../../../tools/macos/README.md). All platform artifacts use the [release layout](../../../release/README.md). iOS and Android directories are placeholders.

## File structure

| Directory | Contents |
|---|---|
| `src/` | Rust core and platform implementations |
| `libs/` | Capture, input, clipboard and other libraries |
| `flutter/` | UI and platform projects |
| `res/`, `branding/` | Application resources and MH assets |
| `tools/` | Build, packaging, inspection tools and tests |
| `config/` | Public connection defaults and custom configuration template |
| `docs/user/` | Usage, translated homepage and release notes |
