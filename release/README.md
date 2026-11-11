# 本地发布产物

统一格式：`release/<平台>/<版本>/<架构>/`。

```text
release/
  windows/<版本>/x64/
  macos/<版本>/arm64/
  ios/<版本>/arm64/
  android/<版本>/arm64-v8a/
```

Windows 打包入口：`tools/windows/package-windows.ps1`。
macOS 打包入口：`tools/macos/build-macos.py`。
iOS、Android 目前仅预留目录，尚未适配 MH 构建。

每个版本目录保存应用、安装包、构建清单及 SHA-256 校验文件；相同版本和架构的产物不得覆盖。构建中间文件继续留在 `target/`、`flutter/build/`，依赖放在 `.cache/`。

这里的安装包和真实服务配置不提交 Git；Git 仅保留目录说明和构建脚本。源码 push 不会自动上传安装包或创建 GitHub Release。

旧的 Windows `dist/<版本>/` 或平铺产物可用 `python tools/windows/organize-packages.py` 预览迁移，确认后加 `--apply` 移入平台目录。
