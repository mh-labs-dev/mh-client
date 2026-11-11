# MH

[中文](../../../README.md) · [English](README.md)

MH is a remote Mac controller modified from [RustDesk 1.5.1](https://github.com/rustdesk/rustdesk), licensed under [AGPL-3.0](../../../LICENCE).

The Windows preview provides account login, a device list and a connection action. Sessions require an available Pro Server, enrolled Macs and appropriate permissions. The server is deployed separately. The current preview is available for Windows x64.

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
New-Item -ItemType Directory -Force .local
Copy-Item config/controller.example.json .local/controller-profile.json
```

Edit `.local/controller-profile.json`, replacing the example domain and all-zero public key with your public service configuration. The template targets a same-domain HTTPS API and WebSocket signaling/relay endpoint. Keep `allow-websocket=Y` and `allow-insecure-tls-fallback=N`.

Validate, build and package:

```powershell
python tools/windows/controller-profile.py validate .local/controller-profile.json
./tools/windows/build-windows.ps1 -ControllerProfile .local/controller-profile.json
./tools/windows/package-windows.ps1 -Version 1.5.1-mh.6-controller-test -ControllerProfile .local/controller-profile.json
```

The version number is an example. Output is stored in `dist/<version>/`. `-ControllerProfile` enables the login-first controller. Rebuild both native code and UI when changing configuration or variants.

## File structure

| Directory | Contents |
|---|---|
| `src/` | Rust core and platform implementations |
| `libs/` | Capture, input, clipboard and other libraries |
| `flutter/` | UI and platform projects |
| `res/`, `branding/` | Application resources and MH assets |
| `tools/` | Build, packaging, inspection tools and tests |
| `config/` | Public configuration examples |
| `docs/user/` | Usage, translated homepage and release notes |
