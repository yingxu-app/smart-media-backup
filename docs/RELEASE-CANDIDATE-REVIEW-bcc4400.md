# v1.0.40 / iPhone PWA 候选审阅记录

核对时间：2026-10-20。此文记录 PR #4 `bcc440072159504aaf899c2a318cac4559155a4c` 的代码、产物、站点差异和回退边界。该分支仍为 OPEN/DRAFT，不能视为公开发行。

## 当前范围

- iPhone 仅维护 Safari PWA；本阶段不制作原生 iOS 包，不申请 Apple Developer 会员、不做 TestFlight 或 App Store。
- Android 真机验收因暂无设备而暂缓。Android CI debug APK 只作内部候选，不作正式发布包。
- Firebase 验证继续进行；真实账户密码只能由用户在本机输入，不从聊天内容读取或保存。
- 网站只维护静态官网、下载页、隐私页和 Pocket PWA；浏览器在线备份、远程原文件传输和小程序不属于本阶段。

## 代码与 CI

- PR #4：OPEN/DRAFT、mergeable；分支 `codex/v1.0.39-miniprogram-lan-tcp`，HEAD `bcc440072159504aaf899c2a318cac4559155a4c`。
- Reliability PR `39275732826`、Reliability push `39275655797`、macOS 候选 `39275733038`、Windows 预览 `39275732800` 均 success。
- Pocket run `39275732818` 于 2026-10-19 15:59 UTC 终态 `completed/success`；JS/CNG/check 与 Android debug job 均成功。Android job 单项 API 之后仍返回旧的 `in_progress`，但其 Build、Artifact upload、Complete job 步骤均显示 success，且 run 汇总为 success。没有重启该 run。
- 本地此前已核验桌面 108 项通过、2 项 Windows-only 跳过；PWA Node 7/7；mobile lint/typecheck/28 项通过。它们不替代账号、设备或线上验收。

## 候选产物

| 平台 | 候选 | 包体核验 | 发布限制 |
|---|---|---|---|
| macOS | v1.0.40，artifact `12197447373` | ZIP 21,077,308 bytes，SHA-256 `009e05b568341650e06d136c2f0e76710fbcebafeaac51231aed11c1dac3f176`，与 artifact metadata 一致；DMG SHA-256 `c08ab37587d9db5c27d3c820e1db7c225cfabfbfb229786879f22e9bdbdf5c0d` 与包内清单一致。已有的同 head 记录显示 DMG 校验有效、app deep/strict code verification 通过。 | ad-hoc 签名、无 Team ID、未公证；不是面向普通用户的正式发行包。 |
| Windows | v1.0.40 preview，artifact `12196918288` | ZIP 27,874,541 bytes，SHA-256 `b44174d45b0fe68be67c03007708033623a0929f0eec97cd891a8d4a2917d3ed`，与 metadata 一致；EXE SHA-256 `bf77c2f3051fec3988351560982f66c3b7a84757dc2334df8f407a0d35e73f63` 与 `SHA256SUMS.txt` 一致。 | unsigned x64 preview；当前候选未在 Windows 设备安装运行。 |
| Android | artifact `12199136415`，debug APK | ZIP 94,609,050 bytes，SHA-256 `ccb43310fc7f6f5c8bffb63f0c91853ba0fad0d402134b7631bc7e46430b18e1` 与 metadata 一致；内含 269,595,675-byte `app-debug.apk`，SHA-256 `d9eed27a0cc8213d3626dc5b1c3c86975e8357a78703c48b8161aff4830f13dd`，包含 arm64-v8a、armeabi-v7a、x86、x86_64。 | 不是商店包；Android 真机验收因暂无设备而暂缓。 |

## 网站差异与部署状态

- 相对 `origin/main`，网站改动涉及 `site/index.html`、`site/download/index.html`、`site/privacy.html`、`site/README.md`；新增 `site/pocket/` PWA 与两个 PNG 图标。
- 首页和下载页继续把 Windows v1.0.34 标为唯一公开桌面版；macOS v1.0.40 仍标为未公开候选。新增 Pocket 入口指向 `../pocket/`，隐私文案说明 PWA 同步云端元数据、不读取手机原片。
- GitHub Pages 配置从 `main:/` 发布；`deploy-website.yml` 在 main 的 site 文件变化时部署。最近一次成功部署为 deployment `7122987293`，commit `93588191778f7754dce8bfbc8d5e5bbd23396025`，时间 2026-10-16 15:35 UTC。当前 PR 未合并，因此本分支 PWA 尚未部署。
- 本轮从本机 Python 访问 Pages 时遇到 `CERTIFICATE_VERIFY_FAILED`，没有据此宣称线上路由当前可用或不可用。此前成功 HTTP 200 的检查只代表对应检查时间。
- 2026-10-20 再用浏览器直接打开规范 PWA URL `https://yingxu-app.github.io/smart-media-backup/pocket/`，仍显示站点自定义 404 页面“这个页面暂时找不到”。因此 PWA 线上入口目前未部署，不能引导用户在公开站点登录；本机 localhost 预览仍可用。
- 当前公开 GitHub Release API 仍是 v1.0.34（2026-09-12），只含 `YINGXU-Windows-v1.0.34.exe` 与 `SHA256SUMS.txt`。

## 版本与更新路径

- 桌面源码显示版本为 1.0.40；当前公开 Release 仍是 1.0.34。下载页应继续保留旧公开包，直到新版本的目标平台包、签名策略、公开下载和回退方案全部确认。
- 偏好设置的“检查更新”按钮只查询 GitHub 正式 Release 并打开发行页供用户手动下载、安装；它不是静默自动更新器。
- PWA Service Worker 更新网页壳；Firebase Auth、RTDB 响应不缓存。登录成功后的历史元数据缓存可离线展示，但本轮未用真实账号验证。

## 回退检查

- **网站：**若合并后 PWA 或下载页异常，在从当前 main 建立的回退分支中运行 `git restore --source=93588191778f7754dce8bfbc8d5e5bbd23396025 -- site/`，检查差异只涉及预期站点内容后提交回退 PR；合并后 `deploy-website.yml` 会因 main 的 `site/**` 变化重新部署。若 main 后续已有其他站点更新，应只反向应用本次发布引入的站点差异，避免覆盖后续内容。workflow 的 `workflow_dispatch` 从默认分支运行，不支持指定旧 ref；没有已验证的一键旧 deployment 回滚。
- **Windows：**v1.0.34 当前正式包仍可作为旧版下载入口。新版升级及回退尚未在 Windows 设备实际执行。
- **macOS：**本机旧版 v1.0.39 备份目录未在 `/tmp` 找到，故本轮没有确认可直接恢复的本机旧 app 副本；当前没有公开 macOS 正式旧版可供回退。
- **发布准入：**先决定是否接受 macOS ad-hoc/未公证与 Windows unsigned 的公开分发限制；若不接受，先完成相应生产签名。未完成回退前，不替换 v1.0.34 正式下载入口，也不宣称完成正式发布。

## Firebase 登录交接

- Firebase 项目和 UID 范围规则已配置；先前的只读探测确认 RTDB 拒绝未认证访问，Auth REST endpoint 可达。它们不证明真实账户登录成功。
- 本机 PWA 预览当前已在浏览器打开；邮箱字段已准备，页面仍停留登录表单，没有显示登录成功或失败。密码由用户在本机处理；下一步是在该页输入密码并点“登录并同步”。失败时只需回报页面错误文字；不要把密码发到聊天。
- 登录成功后仍需用实际页面核对实时备份进度、归档历史、同账号第二设备同步、不同 UID 隔离和断网恢复。未登录时缓存/页面壳测试不替代这些验证。

### 桌面端 Firebase 错误诊断补充（2026-10-20）

- 修正桌面登录接口把未分类 Firebase 响应一律折叠为通用报错的问题：未知 Firebase 错误只显示经过字符白名单处理的错误码与 HTTP 状态；网络超时、TLS、连接失败和系统凭据库写入失败分别提示下一步检查方向，不把底层异常详情、密码或令牌返回给界面。
- Pocket PWA 登录对未分类 Firebase 响应也显示经过白名单处理的错误码与 HTTP 状态，避免手机页把项目限制或未知拒绝信息隐藏为通用提示。
- 离线页面壳缓存版本递增到 `v2`，激活时清理旧壳缓存，确保已安装/本机预览 PWA 更新到新的错误诊断脚本。
- 如果 Firebase 已验证账号但钥匙串/系统凭据库不能保存刷新令牌，客户端不进入半登录状态；用户修复凭据库后可重新登录。
- 本地定向验证：`test_firebase_sync.py` 11 项、`test_firebase_server.py` 7 项、PWA cloud sync 8 项通过，`git diff --check` 通过。此处只证明错误处理分支，不证明真实账号登录成功。

## 尚待关闭

1. 用户在本机 PWA 登录页输入密码并点“登录并同步”；随后验证同账号多端历史/进度、不同 UID 隔离、断网缓存与恢复。
2. Android run 已终态成功并验证 artifact；Android 真机验收继续暂缓，等有设备再做。
3. 在 iPhone Safari 验收 HTTPS PWA 添加到主屏幕、离线壳、已同步历史、刷新和恢复；不做原生 iOS 验收。
4. 在 Windows 实机验收当前候选安装、备份、升级与回退；Android 设备验收等有设备后再做。
5. 在真实 Firebase 登录验证后，部署 Pages PWA 路由并用 iPhone Safari 实测；完成正式 Release 及下载校验。签名策略、Windows 用户设备验收和最终发布确认未完成前保持候选状态。

## 最新头部与产物边界（2026-10-19 16:30 UTC）

- 当前 PR #4 head 为 `196c287945657241e114aa174bcee4aa64598624`，仍为 OPEN/DRAFT、mergeable；新增提交 `74b1e0a`、`da07f20`、`196c287` 修复桌面/PWA 登录诊断并递增 PWA Service Worker cache version。
- 最新本地定向验证：桌面 Firebase sync 11/11、Firebase server 7/7、PWA cloud sync 8/8，`node --check site/pocket/sw.js` 与 `git diff --check` 通过。
- 最新 head 的 Reliability PR run `39284960337`：Ubuntu 3.11、Ubuntu 3.12、macOS 3.11 已 success；macOS 3.12 与 Windows 3.11/3.12 在本次记录时仍 queued。最新 macOS candidate、Windows preview、Pocket runs `39284960188`、`39284960305`、`39284960287` 也尚未产出本 head 的新 artifact。GitHub status 同时将 Actions 与 Pages 标记为 degraded_performance，incident 仍在调查：<https://stspg.io/nrv2k8s68bwn>。未重启这些任务。
- 表格中的桌面包体哈希仍来自产品候选 head `bcc4400`，不是 `196c287` 的构建产物。由于 Firebase 登录诊断代码已经变化，在 `196c287` 对应桌面构建完成并核验前，不将旧包称作最新发布候选。
- 当前本机预览 `http://127.0.0.1:8766/pocket/` 返回 HTTP 200，Service Worker shell 为 v2；GitHub Pages `/pocket/` 返回 HTTP 404，故真实账号测试只能通过本机预览。正式 GitHub Release 仍为 v1.0.34。

## 2026-10-20 exact-head 候选与 Firebase 排障更新 — `42a3a8d`

- PR #4 当前 head `42a3a8d7638cbcc93cda204fe21b581ec2fa5964`，分支 `codex/v1.0.39-miniprogram-lan-tcp`，OPEN/DRAFT、mergeable、worktree clean。产品代码 HEAD 为 `196c287945657241e114aa174bcee4aa64598624`；`42a3a8d` 只更新审阅证据，不改产品源码。此次用户范围：iOS 仅 PWA，Android 真机验收暂缓；原生 iOS、Android 实机、小程序、网页原文件云备份不纳入当前发布验收。
- Exact-head Reliability PR `39286333411`、Reliability push `39286323855`、macOS candidate `39286333386`、Windows preview `39286333390` 均 success。Pocket run `39286333378` 的 PWA JS/CNG/check job `118173541732` success；Android debug job `118173541355` 仍在 `Build debug APK`，未重启该 run。Android 真机验收因无设备暂缓，该 CI 构建不是用户发行验收。

| 平台 | Exact-head artifact | 包体校验 | 发行/验收限制 |
|---|---|---|---|
| macOS | artifact `12203465990`，20,952,035 bytes，GitHub digest `sha256:d188e1f23e5b4e11c953e0c0d43b865d5ef70d4534b87aec2facd6bbc50d5de5` | GitHub 通过 `gh run download` 解包到本机，故没有对原始 ZIP 字节另算 SHA-256。DMG 22,802,690 bytes，SHA-256 `149a6b87e1a3db7ea66e7e5fa635e9e965186dcee395d5c7ad261dfdf90e11c9`，与包内清单一致；`hdiutil verify` 为 VALID。app 版本 1.0.40、arm64，`codesign --verify --deep --strict` 通过。 | ad-hoc 签名、无 Team ID、未公证；不是可直接面向普通用户的签名发行包。 |
| Windows | artifact `12203281642`，27,876,640 bytes，GitHub digest `sha256:86a02497efcc2add837f9245a611ce1db8a5c84f69e5699ebdd09cf635a3ad06` | ZIP 经 Actions 下载工具解包；未对原始 ZIP 字节另算 SHA-256。EXE 28,178,223 bytes，SHA-256 `89ad2e43b5c468c78fc884e50f257184dbb632971374204f2b084eb45149d457`，与 `SHA256SUMS.txt` 一致；文件为 PE32+ GUI x86-64。 | unsigned preview；未在 Windows 实机安装运行。 |
| Android | Exact-head run `39286333378` 尚未结束，artifact 尚未列出 | 无本轮包体证据。此前版本的 debug APK 不代表此 head。 | Android 实机验收暂缓；debug CI 包也不等于商店包。 |

### 官网与版本核对

- 当前 PR 站点差异相对 `origin/main`：修改 `site/index.html`、`site/download/index.html`、`site/privacy.html`、`site/README.md`；新增 `site/pocket/` PWA 客户端、Firebase web client、manifest、Service Worker 和两个图标。
- 当前规范 Pages `/smart-media-backup/pocket/` 现场返回 HTTP 404；因此不可让 iPhone 用户从公开站点开始真实 Firebase 登录。必须先发布站点差异并复核 HTTPS 路由，再做 iPhone Safari PWA 验收。
- GitHub 最新正式 Release API 仍为 `v1.0.34`，发布日期 2026-09-12；包含 Windows v1.0.34 EXE 与 SHA256SUMS。v1.0.40 桌面候选尚未发布。正式下载页仍保留 v1.0.34，不以预览包替换。
- 回退仍按前述“网站”段：以原 Pages 部署提交 `93588191778f7754dce8bfbc8d5e5bbd23396025` 为恢复参照，合并后仅反向应用本次 `site/**` 差异并通过 Pages workflow 重部署；若 main 已有后续站点改动，不整目录覆盖。Windows 旧正式 v1.0.34 可保留下载；macOS 没有已核实的公开旧正式包，须在发布前另存并验证可恢复副本。

### Firebase 安全诊断与本机交接

- 只读探测 Firebase Identity Toolkit project-config endpoint 返回 HTTP 200，确认仓库 web API key 可识别项目 `yingxu-73c7b`；匿名读取 RTDB 返回 HTTP 401 `Permission denied`，与未登录拒绝规则一致。该探测未提交邮箱/密码，也不能证明 Email/Password provider 已启用或目标账号密码正确。
- 旧桌面服务 PID `23554` 于 2026-10-19 启动，早于 Firebase 错误诊断修复提交 `74b1e0a`（2026-10-20 00:20 +08:00），因此页面仍可能载入旧的通用错误处理。已确认备份状态 idle 后，结束旧进程并用项目 `.venv/bin/python` 重启本地服务；`/api/status` 返回 HTTP 200、版本 1.0.40、idle，`/api/firebase/settings` 报告 configured=true、signed_in=false。当前未尝试真实登录。
- **唯一需用户输入凭据的步骤：**在本机打开或刷新 `http://127.0.0.1:8080/settings`，在密码框输入密码并点“登录并同步”。若失败，仅回报页面上新的具体错误文字/错误代码；不要把密码发到聊天。接下来可根据错误码定位 provider、邮箱账号状态、网络/TLS 或系统凭据库问题。
- 成功登录后仍须验证同账号第二设备的进度/历史、不同 UID 隔离、离线缓存与恢复、令牌续期。页面没有真实账号的情况下不伪造这些验收结果。

### 当前停止条件

- 候选已完成源码基线、exact-head 桌面 artifact 元数据及内层包体校验、版本/API 核对、站点差异与回退路径记录；仍不具备公开发布条件：PR 未合并、公开 PWA 路由 404、Firebase 真实账号未登录、macOS 未公证/无 Team ID、Windows unsigned 且无设备验收。
- 只有真实 Firebase 同步与目标范围内的设备验收完成，并具备签名/公证策略与最终发布授权后，才可替换公开 Release。iOS 原生及 Android 真机不属于本轮门禁。
