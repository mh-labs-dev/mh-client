# macOS 本地测试包

需要 macOS、完整 Xcode、Homebrew、Python 3.11+。首次准备依赖：

```sh
bash tools/macos/prepare-macos.sh
```

Rust 1.81.0、Flutter 3.24.5、固定 vcpkg 和 NASM 2.16.03 放在项目忽略的 `.cache/mh-tools/macos/`；Homebrew 安装 CMake、Ninja、Autotools 和 CocoaPods。不会更改 Windows 的依赖缓存或版本。

无服务配置的控制端预览（仍为登录首页，登录暂不可用）：

```sh
python3 tools/macos/build-macos.py --version 1.5.1-mh.9-controller-preview
```

可登录的控制端使用公开服务配置，不包含账号密码：

```sh
python3 tools/controller_profile.py validate .local/controller-profile.json
python3 tools/macos/build-macos.py --version 1.5.1-mh.9-controller-test --controller-profile .local/controller-profile.json
```

脚本构建 Rust 动态库、辅助服务和 Flutter/Xcode 应用，生成 MH 原生图标，随后打包到 `release/macos/<版本>/<架构>/`。已有版本不会覆盖；更换配置时重新执行完整构建。

当前最低目标为 macOS 12.3，按主机架构构建，Apple Silicon 为 `arm64`。输出包含 `.app`、`.dmg`、构建清单和 SHA-256 校验文件。使用本地 ad-hoc 签名，不包含 Developer ID 签名、Apple 公证或 App Store 发布；不自动安装后台服务。

macOS 构建入口始终启用纯控制端：原生层仅主动连接、禁用 TCP 监听，界面为登录 → 设备列表 → 连接。不提供服务配置时不会退回受控端界面，也不会发送登录凭据。
