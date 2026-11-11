# MH

[English](../../../README.md) · [简体中文](README.md)

MH 是基于 [RustDesk 1.5.1](https://github.com/rustdesk/rustdesk) 修改的远程 Mac 控制端，采用 [AGPL-3.0 许可](../../../LICENCE)。

MH 提供账号登录、Mac 设备列表和远程桌面连接。Windows x64 与 macOS arm64 构建使用同一控制端界面。使用需要 Pro Server 账号及分配的 Mac。

[使用说明](USAGE.md) · [版本说明](../releases/1.5.1-mh.10-preview.md) · [macOS 构建](../../../tools/macos/README.md)

## Dependencies

- Windows x64、Git、Python 3.12。
- Visual Studio 2022：桌面 C++ 工作负载和 Windows SDK；CMake 可从 PATH 调用。
- Rust 1.75.0、Flutter 3.24.5、固定 vcpkg 和 libclang 15.0.6.1，由下列脚本准备。

## Build

在仓库根目录使用 PowerShell，首次构建先准备依赖：

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

构建默认读取 [config/controller.default.json](../../../config/controller.default.json)，预置 MH 的固定服务地址、服务器公钥和安全 WebSocket 设置。该配置随源码维护，客户端中的服务器设置仍可修改。

然后校验配置、编译并打包：

```powershell
python tools/controller_profile.py validate config/controller.default.json
./tools/windows/build-windows.ps1
./tools/windows/package-windows.ps1 -Version 1.5.1-mh.10-preview
```

版本号仅为示例。产物位于 `release/windows/<版本号>/x64/`。默认构建为登录优先的控制端；修改配置或切换变体时完整重建。

自定义服务可从 `config/controller.example.json` 复制到 `.local/controller-profile.json`，在 Windows 构建和打包时传入相同的 `-ControllerProfile` 路径。显式传入 `-ControllerProfile ''` 可构建通用 MH 变体。客户端已保存的网络设置优先于构建默认值。

macOS 准备依赖后，使用同一公开默认配置构建：

```sh
python3 tools/controller_profile.py validate config/controller.default.json
python3 tools/macos/build-macos.py --version 1.5.1-mh.10-preview --controller-profile config/controller.default.json
```

## File structure

| 目录 | 内容 |
|---|---|
| `src/` | Rust 核心与平台实现 |
| `libs/` | 采集、输入、剪贴板等功能库 |
| `flutter/` | 界面及各平台工程 |
| `res/`、`branding/` | 程序资源与 MH 品牌素材 |
| `tools/` | 构建、打包、检查工具及测试 |
| `config/` | 默认公开连接配置与自定义模板 |
| `docs/user/` | 使用说明、英文首页与版本说明 |
