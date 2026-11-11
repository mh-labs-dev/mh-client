# MH

[中文](README.md) · [English](docs/user/en/README.md)

MH 是基于 [RustDesk 1.5.1](https://github.com/rustdesk/rustdesk) 修改的远程 Mac 控制端，采用 [AGPL-3.0 许可](LICENCE)。

Windows 版本提供账号登录、设备列表和连接入口。连接需要可用的 Pro Server、已接入的 Mac 和相应权限；服务端独立部署。当前提供 Windows x64 预览版。

[使用说明](docs/user/zh-CN/USAGE.md) · [版本说明](docs/user/releases/1.5.1-mh.5-controller-test.md)

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
New-Item -ItemType Directory -Force .local
Copy-Item config/controller.example.json .local/controller-profile.json
```

编辑 `.local/controller-profile.json`，将示例域名和全零公钥替换为实际公开服务配置。模板针对同域名的 HTTPS API 和 WebSocket 信令/中继入口；保留 `allow-websocket=Y`、`allow-insecure-tls-fallback=N`。

然后校验配置、编译并打包：

```powershell
python tools/windows/controller-profile.py validate .local/controller-profile.json
./tools/windows/build-windows.ps1 -ControllerProfile .local/controller-profile.json
./tools/windows/package-windows.ps1 -Version 1.5.1-mh.6-controller-test -ControllerProfile .local/controller-profile.json
```

版本号仅为示例。产物位于 `dist/<版本号>/`。`-ControllerProfile` 启用登录优先的控制端；修改配置或切换变体时完整重建。

## File structure

| 目录 | 内容 |
|---|---|
| `src/` | Rust 核心与平台实现 |
| `libs/` | 采集、输入、剪贴板等功能库 |
| `flutter/` | 界面及各平台工程 |
| `res/`、`branding/` | 程序资源与 MH 品牌素材 |
| `tools/` | 构建、打包、检查工具及测试 |
| `config/` | 公开配置模板 |
| `docs/user/` | 使用说明、英文首页与版本说明 |

