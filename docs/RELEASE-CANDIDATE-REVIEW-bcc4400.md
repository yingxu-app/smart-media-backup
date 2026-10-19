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
- 如果 Firebase 已验证账号但钥匙串/系统凭据库不能保存刷新令牌，客户端不进入半登录状态；用户修复凭据库后可重新登录。
- 本地定向验证：`test_firebase_sync.py` 11 项、`test_firebase_server.py` 7 项、PWA cloud sync 8 项通过，`git diff --check` 通过。此处只证明错误处理分支，不证明真实账号登录成功。

## 尚待关闭

1. 用户在本机 PWA 登录页输入密码并点“登录并同步”；随后验证同账号多端历史/进度、不同 UID 隔离、断网缓存与恢复。
2. Android run 已终态成功并验证 artifact；Android 真机验收继续暂缓，等有设备再做。
3. 在 iPhone Safari 验收 HTTPS PWA 添加到主屏幕、离线壳、已同步历史、刷新和恢复；不做原生 iOS 验收。
4. 在 Windows 实机验收当前候选安装、备份、升级与回退；Android 设备验收等有设备后再做。
5. 在真实 Firebase 登录验证后，部署 Pages PWA 路由并用 iPhone Safari 实测；完成正式 Release 及下载校验。签名策略、Windows 用户设备验收和最终发布确认未完成前保持候选状态。
