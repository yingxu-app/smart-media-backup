# v1.0.37 候选验收记录

状态：构建与安装验收进行中；不是公开发行版。GitHub 最新正式 Release 仍为 v1.0.34。

## 本轮改动

- 配置 schema v1→v2 迁移，为旧配置补齐 Pocket 默认值。
- schema 版本单独写入 `config.schema.json`，保持 `config.json` 与 v1.0.34 的 19 个字段兼容，避免旧版回退时拒绝未知字段。
- 保存配置采用同目录临时文件和原子替换；读取旧配置不会立即写盘；拒绝高于当前支持范围的 schema。
- 增加 6 项配置迁移回归测试。

## 已有验证

- 本机完整测试：66 项运行、64 项通过、2 项 Windows 条件跳过。
- `git diff --check` 通过。
- 当前配置字段名与 v1.0.34 逐项对照：19 项完全一致。
- 源码和版本显示统一到 v1.0.37；commit `25d3deddf23ad737f00fafd1b734878dcc1eefe9` 对应的六平台 Reliability run `38856965187`、Windows preview run `38856965117`、GitHub Pages deploy run `38856965210` 均成功。
- macOS 候选 workflow run `38856971672` 成功，生成 arm64 DMG `YINGXU-macOS-main.dmg`；SHA-256 `25328ce6d13484cc1bf421f81faef058922b1530fa81c263955c506011710f7b`，`hdiutil verify` 通过。挂载后 App `CFBundleShortVersionString=1.0.37`，`codesign --verify --deep --strict` 通过，签名为 ad-hoc，未公证。
- 新候选尚未从 `/Applications` 启动验收；安装版当前仍为 v1.0.36。

## 设备与发布边界

- 当前 `/Applications/影序 YINGXU.app` 是 v1.0.36；替换前副本保存在 `/tmp/yingxu-installed-1.0.36-backup-2026-10-16/影序 YINGXU.app`，恢复说明在同目录 `RESTORE.txt`。
- Windows 仍无真机安装和读卡器验收证据。
- Apple Developer ID 签名、公证、公开 GitHub Release 和下载页版本更新尚未完成。
- 外置盘拔出/强退恢复、iPhone/Android 实机连接、微信小程序、商店上架仍需独立验证。
