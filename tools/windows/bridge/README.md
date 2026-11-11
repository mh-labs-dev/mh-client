# Pinned bridge input

`bridge-upstream.zip` is the `bridge-artifact` artifact (ID `13725909613`) from the official RustDesk [CI run 42735021293](https://github.com/rustdesk/rustdesk/actions/runs/42735021293), built at commit `1fbb7f7b436a05e38bbfe8720ab8d81c91b50a51`.

SHA-256: `15cb37d5b94554f1d5b965eae99de33219b5864b9aa633dbd65e53322eab9221`. The original archive is retained as a reproducible build input under the upstream license.

The pinned client interface predates the final `login_method` argument of `session_add_sync`. `prepare-bridge.py` aligns the Rust, C and Dart signatures and extracts the four native bridge files. The expected LF-normalized interface SHA-256 is `400191f6761117e67562a68bb02cf0adb834e8e01134cbfc47ed0b634fa9d607`.

Recheck interface compatibility and archive hashes when updating the upstream revision.
