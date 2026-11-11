# MH

[English](README.md) · [简体中文](docs/user/zh-CN/README.md)

MH is a remote Mac controller modified from [RustDesk 1.5.1](https://github.com/rustdesk/rustdesk), licensed under [AGPL-3.0](LICENCE).

MH provides account login, a Mac device list and remote desktop connections. Windows x64 and macOS arm64 builds use the same controller interface. Access requires an account and an assigned Mac on a Pro Server.

[Usage](docs/user/en/USAGE.md) · [Release notes](docs/user/releases/1.5.1-mh.10-preview.md) · [macOS build](tools/macos/README.md)

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

Builds use [config/controller.default.json](config/controller.default.json) for the MH service addresses, server public key and secure WebSocket settings. This public configuration is maintained with the source. Server settings remain editable in the client.

Validate, build and package:

```powershell
python tools/controller_profile.py validate config/controller.default.json
./tools/windows/build-windows.ps1
./tools/windows/package-windows.ps1 -Version 1.5.1-mh.10-preview
```

The version number is an example. Output is stored in `release/windows/<version>/x64/`. Builds default to the login-first controller. Rebuild both native code and UI when changing configuration or variants.

For a custom service, copy `config/controller.example.json` to `.local/controller-profile.json` and pass the same `-ControllerProfile` path to both Windows build and packaging commands. Pass `-ControllerProfile ''` explicitly to build the general MH variant. Saved client network settings take precedence over build defaults.

To build macOS with the same public defaults, use the macOS build script after preparing its dependencies:

```sh
python3 tools/controller_profile.py validate config/controller.default.json
python3 tools/macos/build-macos.py --version 1.5.1-mh.10-preview --controller-profile config/controller.default.json
```

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
