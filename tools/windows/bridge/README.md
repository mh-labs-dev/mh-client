# 固定版本桥接输入

`bridge-upstream.zip` 来自官方 `rustdesk/rustdesk` 的 [CI run 42735021293](https://github.com/rustdesk/rustdesk/actions/runs/42735021293)，artifact ID `13725909613`，名称 `bridge-artifact`，构建提交 `1fbb7f7b436a05e38bbfe8720ab8d81c91b50a51`。

原始 ZIP SHA-256：`15cb37d5b94554f1d5b965eae99de33219b5864b9aa633dbd65e53322eab9221`。该文件保持下载原样，用于避免 CI artifact 过期后丢失构建输入；内容沿用上游许可证。

当前客户端固定基线的导出接口与该构建的差异是 `session_add_sync` 尚没有最后的 `login_method` 参数。`prepare-bridge.py` 同时对齐 Rust 实现、C 导出和 Dart 方法/FFI 函数签名，只取本机所需的四个文件，不使用其中的 Web 桥接。接口源码按 LF 规范化后的 SHA-256 为 `400191f6761117e67562a68bb02cf0adb834e8e01134cbfc47ed0b634fa9d607`。

更新上游源码时必须重新核对导出接口及桥接输入。不能去掉哈希检查后盲目沿用这份桥接。
