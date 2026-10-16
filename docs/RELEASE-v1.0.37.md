# v1.0.37 候选验收记录

状态：候选已构建并安装到本机；真实存储卡启动扫描未通过验收，故不是公开发行版。GitHub 最新正式 Release 仍为 v1.0.34。

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
- Windows preview artifact 已读取并检查为 PE32+ GUI、x86-64，27,449,139 bytes；SHA-256 `d83e9c4eab18f60b852c29b5d102b1af4604e32282972b497e2b40f3e8fa26bc`。无 Windows 真机运行证据。
- macOS 候选 workflow run `38856971672` 成功，生成 arm64 DMG `YINGXU-macOS-main.dmg`；SHA-256 `25328ce6d13484cc1bf421f81faef058922b1530fa81c263955c506011710f7b`，`hdiutil verify` 通过。挂载后 App `CFBundleShortVersionString=1.0.37`，`codesign --verify --deep --strict` 通过，签名为 ad-hoc，未公证。
- 候选已安装到 `/Applications/影序 YINGXU.app`；Info.plist 为 1.0.37 arm64，安装路径深度签名校验通过。启动后 `/api/status` 返回版本 1.0.37，`/`、`/transfer`、`/settings`、`/api/health` 均返回 HTTP 200，原生窗口显示工作台。
- 使用隔离目录启动已安装的冻结 App，载入无 schema sidecar 的 19 字段配置，且保留 Pocket 已关闭及 6 小时会话值；调用设置保存后创建 `config.schema.json` v2，主 `config.json` 不含 `schema_version`，并保留原 Pocket 值。验证期间没有改动用户真实配置。
- 当前真实挂载的 SD 卡令 v1.0.37 首页持续显示“正在读取存储卡”；扫描请求超过 1 分钟未完成。相同主机、相同介质上用 v1.0.36 备份副本复核也出现停滞；两个版本的进程采样均看到 `statfs` 与目录打开系统调用等待。**根因尚未确认**，可能是当前挂载介质 I/O；不能据此通过真实素材扫描验收。两个验证进程已正常退出，1.0.37 保持安装。
- 更新后的静态下载页已部署；缓存校验 URL 返回 HTTP 200，页面显示 v1.0.37 候选且未公开下载。

## 设备与发布边界

- 当前 `/Applications/影序 YINGXU.app` 是 v1.0.37；v1.0.36 副本保存在 `/tmp/yingxu-installed-1.0.36-backup-2026-10-16/影序 YINGXU.app` 与 `/tmp/yingxu-previous-install-1.0.36-2026-10-16.app`，恢复说明在前一个目录 `RESTORE.txt`。
- Windows 仍无真机安装和读卡器验收证据。
- Apple Developer ID 签名、公证、公开 GitHub Release 和下载页版本更新尚未完成。
- 外置盘拔出/强退恢复、iPhone/Android 实机连接、微信小程序、商店上架仍需独立验证。
