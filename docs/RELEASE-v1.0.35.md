# v1.0.35 本地候选验收记录

状态：本地候选，尚未提交、推送、发布或部署。候选基于当前工作树的转移老内容功能和后续本地改动。

## 构建产物

- Apple Silicon App：`/tmp/yingxu-v1035-build/dist/影序 YINGXU.app`
- DMG：`release/v1.0.35/YINGXU-macOS-v1.0.35.dmg`（24 MB）
- DMG SHA-256：`b8f8380b96753c0d854cc0703362fb980583b4261aa131c353c3f5283f9354ac`
- App 版本：`1.0.35`（Info.plist 与 `/api/status` 一致）
- App 深度签名校验：`codesign --verify --deep --strict` 通过（ad-hoc 签名）
- DMG 完整性：`hdiutil verify` 通过；只读挂载后确认 App 与 `/Applications` 快捷方式存在，包内 App 版本为 `1.0.35`。

## 验收证据

- 自动化测试：56 项运行，54 项通过、2 项 Windows 条件跳过。
- `git diff --check` 与 `zsh -n scripts/package_macos_release.sh` 通过。
- 候选 App 启动后 `/api/status` 返回 HTTP 200、版本 `1.0.35`；桌面首页和 `/transfer` 在原生窗口内可访问。
- 已将 v1.0.35 安装到 `/Applications/影序 YINGXU.app`；当前实际运行进程路径为 `/Applications/影序 YINGXU.app/Contents/MacOS/影序 YINGXU`，`/api/status` 返回 1.0.35。原安装版 v1.0.33 保存在 `/tmp/yingxu-installed-1.0.33-backup-2026-10-16`，附有恢复说明。
- 在临时目录运行的同版 v1.0.35 候选中，`SD_Card` 自动扫描完成并在首页显示 828 个文件、784 张照片和 44 个视频；扫描期间首页会即时显示“正在读取存储卡”。
- 通过候选 App 的真实 HTTP 接口，在 `/tmp/yingxu-v1035-transfer-e2e` 隔离目录完成 1 个虚拟 JPG 的扫描、分析、转移；目标副本与预期字节一致，源测试文件在校验后移除。未对用户素材执行转移。
- 修正了一项过期测试夹具：接口已使用 `list_candidate_source_volumes`，测试此前只 mock 旧的 `list_removable_volumes`，导致自动发现真实 SD 卡并产生假失败；现在 mock 当前使用的卷枚举函数。

## 未完成的发布门槛

- 当前 GitHub 最新发布仍是 `v1.0.34`，只含 `YINGXU-Windows-v1.0.34.exe` 与 `SHA256SUMS.txt`；没有 macOS DMG。
- v1.0.35 尚未提交、推送或创建 GitHub Release；工作树中保留用户原有的转移功能改动。
- 当前 App 仅 ad-hoc 签名，未完成 Apple 公证；Windows v1.0.35 包、Windows 真机测试、iPhone Safari 实机验收和真实外置盘故障场景仍未完成。
- 本次将 App 安装到 `/Applications` 后，首页自动扫描仍超过 1 分钟未返回结果，虽然界面持续显示读取状态且 `/api/status` 正常；需要继续调查真实介质扫描耗时，再确认安装版首启体验。
- 小程序平台、在线网页产品与官网/桌面下载页面的目标范围仍待确认。
