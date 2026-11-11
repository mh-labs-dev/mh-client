# MH

[中文](README.md) · [English](docs/user/en/README.md)

MH 是基于 [RustDesk 1.5.1](https://github.com/rustdesk/rustdesk) 修改的远程 Mac 控制端，采用 [AGPL-3.0 许可](LICENCE)。

Windows 版本提供账号登录、设备列表和连接入口。连接需要可用的 Pro Server、已接入的 Mac 和相应权限；服务端独立部署。Windows x64 已有预览版；macOS arm64 支持本地纯控制端预览构建，实际服务连接仍需配置与验证。

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
```

构建默认读取 [config/controller.default.json](config/controller.default.json)，预置 MH 的固定服务地址、服务器公钥和安全 WebSocket 设置。该配置随源码维护，客户端中的服务器设置仍可修改。

然后校验配置、编译并打包：

```powershell
python tools/controller_profile.py validate config/controller.default.json
./tools/windows/build-windows.ps1
./tools/windows/package-windows.ps1 -Version 1.5.1-mh.6-controller-test
```

版本号仅为示例。产物位于 `release/windows/<版本号>/x64/`。默认构建为登录优先的控制端；修改配置或切换变体时完整重建。

自定义服务可从 `config/controller.example.json` 复制到 `.local/controller-profile.json`，在 Windows 构建和打包时传入相同的 `-ControllerProfile` 路径。显式传入 `-ControllerProfile ''` 可构建通用 MH 变体。客户端已保存的网络设置优先于构建默认值。

macOS 准备依赖后，使用同一公开默认配置构建：

```sh
python3 tools/controller_profile.py validate config/controller.default.json
python3 tools/macos/build-macos.py --version 1.5.1-mh.10-controller-test --controller-profile config/controller.default.json
```

## Windows / macOS 共享的 MH 功能

MH 的名称、控制端默认配置和 WebSocket 中继选择位于 `src/mh/`，在 Windows 和 macOS 的同一初始化入口调用。两平台复用 Flutter 中的 MH 配色、图标、登录和设备列表页面；iOS、Android 和 Linux 未接入这套原生初始化。

构建时须同时配置 Rust 和 Flutter，不能只切换界面：

| 构建输入 | 含义 |
|---|---|
| Flutter `--dart-define=MH_DESKTOP=true` | 启用共享的 MH 桌面外观；旧参数 `MH_WINDOWS=true` 仍兼容 |
| Flutter `--dart-define=MH_CONTROLLER=true` | 在 MH 外观下启用登录和设备列表首页；普通 MH 构建使用 `false` |
| Flutter `--dart-define=MH_CONTROLLER_CONFIGURED=false` | 未配置服务的预览禁用登录；已有 Windows 构建默认保持可登录 |
| Rust 环境变量 `MH_CONTROLLER=true` | 启用仅主动连接模式，与服务器配置是否就绪分开 |
| Rust 环境变量 `MH_CONTROLLER_PROFILE` | 控制端的公开配置 JSON 内容；普通 MH 构建需取消该变量 |

Windows 构建脚本会继续成对设置这些输入。控制端保留 `MH Test` 配置名称、仅主动连接及禁用 TCP 监听的行为；普通 MH 构建保留 `MH` 名称。共享校验入口为 `python tools/controller_profile.py validate <配置路径>`，原 Windows 校验命令仍可使用。

macOS 构建入口固定使用纯控制端模式；尚无服务配置时显示待配置登录页，不显示本机 ID、临时密码或被控权限。macOS 本地测试包构建见 [macOS 构建说明](tools/macos/README.md)。各平台产物统一存放在 [release](release/README.md)；iOS、Android 目前仅预留目录。

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

