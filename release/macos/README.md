# macOS

产物：`release/macos/<版本>/<架构>/`，包含 `MH.app`、DMG、构建清单和校验文件。

应用始终为纯控制端（登录、设备列表、连接）。服务配置未提供时显示待配置登录页，登录不可用。

本地首包面向 Apple Silicon（`arm64`）。测试包使用本地 ad-hoc 签名，不代表 Developer ID 签名或 Apple 公证。

准备环境及构建命令见 `tools/macos/README.md`。
