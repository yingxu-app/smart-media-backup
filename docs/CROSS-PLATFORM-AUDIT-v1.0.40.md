# 影序全端闭环状态审计 v1.0.40

审计日期：2026-10-17。范围依据用户目标覆盖 PC 桌面、手机端、网页、小程序、多端测试、部署与上架。本文把源码、CI、安装运行、公开发布和真机验收分别记录；候选构建不等于正式发行。

## 当前证据矩阵

| 端 / 交付项 | 已核实证据 | 结论 | 剩余门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | `/Applications/影序 YINGXU.app` 当前运行；`/api/status` 返回版本 `1.0.40`。`codesign` 显示 arm64、ad-hoc、无 Team ID。`RELEASE-v1.0.40.md` 记录此前真实 SD 卡 828 个素材扫描和候选路由验收。 | 本机候选已安装运行，未达到可公开分发签名状态。 | Apple Developer ID 签名、公证、升级/回滚验证、签名 DMG 正式发布与下载验收。 |
| Windows 桌面 | Windows run `38927983658` 对提交 `393e035` 的可靠性测试、版本解析、PyInstaller、x64 PE/清单校验、artifact 上传均成功；产物 `12057552309`。此前 run `38926884128` 的 artifact `12057256711` 已下载回读，PE x64，EXE SHA-256 `72e9ec1f55b3378e466bdaa273cbe59ed9f1b7422a23a0fa709dcdd0c42057b8` 与包内清单匹配。 | CI 构建和一份 unsigned preview 下载核验通过；Windows 实机未验收。 | 在真实 Windows PC 安装、Defender、读卡器、素材备份/转移、拔盘和中断恢复；签名和正式发布。 |
| 手机端 / Pocket PWA | 源码包含独立 Pocket 页面、manifest、Service Worker 和状态/历史/备注 API。v1.0.40 页面在 LAN HTTP 明示离线缓存不可用，在安全上下文尝试注册缓存。当前 `/api/status` 返回 1.0.40。 | 桌面提供的移动网页能力已存在；手机浏览器安装、断网与跨网验收不成立。 | iPhone 与 Android 同 Wi-Fi 配对、主屏幕入口、锁屏/后台、休眠恢复、离线和网络切换实测；明确是否还需原生 iOS/Android 商店应用。 |
| 微信小程序 | `miniprogram/` 有页面、TCP 客户端与 Node 测试；桌面 TCP bridge 默认关闭。项目配置仍为占位 `touristappid`。PR #4 是 draft，正式连接方式未定。 | 原型代码存在，尚未成为可预览、可提审或可上架的小程序。 | 确认局域网 TCP / 微信云托管中继 / 备案域名 HTTPS/WSS；准备真实 AppID、开发者工具编译、真机配对、隐私审核和线上发布。 |
| 官网 / 网页 | 当前 GitHub Pages 首页与 `/download/` 带校验参数回读 HTTP 200；页面写明公开 Windows v1.0.34、macOS v1.0.40 候选未公开。 | 静态介绍与下载站已部署；浏览器在线备份产品范围未确认。 | 继续验证隐私页线上地址和无缓存访问；决定交付静态官网、在线网页应用或两者。在线备份若纳入范围，还需账户/数据/存储/隐私架构。 |
| 公开发行 | GitHub Latest Release API 当前返回 `v1.0.34`，资产仅 `YINGXU-Windows-v1.0.34.exe` 与 `SHA256SUMS.txt`。 | v1.0.40 未发布。 | 完成平台真机验收、签名、公证/商店资料、版本升级回滚与公开下载入口验证后发布。 |

## 本轮代码与 CI 进展

- `977058b` 修复 Windows 默认代码页下报告测试读取和 AI 离线诊断写入问题。Windows run `38926884128` 全绿，artifact 下载后独立验收；证据在 [RELEASE-v1.0.40.md](RELEASE-v1.0.40.md)。
- `393e035` 将 Windows preview workflow 增加到主分支相关文件推送和 PR 变更触发，并纳入 `tests/**` 与工作流自身变更；YAML 解析和 diff 检查通过，手动运行 `38927983658` 全绿。
- 与 main 同步发现官网首页和 README 存在内容冲突；先备份 PR 分支原文到 `docs/site-history/2026-10-17-pre-main-sync/`，再保留 main 上 Pocket/手机发布状态与下载页更新，并保留 PR 分支 macOS Releases 直达链接。首页、下载页、隐私页和 404 页的本地相对链接检查通过。合并提交为 `84fc951`。
- PR head `84fc951` 的自动 `pull_request` Windows preview run `38928587103` 和 Reliability run `38928587182` 全部成功，确认 PR 自动打包门禁已生效。随后只改审计文档的 head `b20027d` 再次触发 Windows preview run `38928977165`（全步骤成功）与 Reliability run `38928976854`（六矩阵成功）。PR #4 仍为 OPEN/DRAFT、可合并但未合并。
- 本机 Python 测试 78 项通过、2 项 Windows 条件跳过；小程序 Node 测试 4 项通过。该结果不替代 iPhone、Android 或 Windows 真机验收。

## 影响全端实现的待决项

1. **手机交付**：以可安装 PWA 为主，还是同时建设原生 iOS/Android 应用并上架？
2. **小程序连接**：同一局域网 TCP（无云端）、微信云托管中继（远程可用、增加云数据路径），或备案域名 HTTPS/WSS？
3. **网页范围**：静态介绍/下载页、在线浏览器备份应用，还是两者都做？

小程序真实 AppID、微信控制台配置和手机真机测试需要用户侧操作。当前 iPhone 镜像已连接 Safari，但手机状态栏显示 5G、无 Wi-Fi；需由用户让 iPhone 与 Mac 接入同一 Wi-Fi 后再进行 Pocket 局域网验收。不得索取 AppSecret、密码或验证码。

## 发行边界

- Windows artifact 为 unsigned CI preview；下载/哈希/架构核验不等于安装运行或用户验收。
- macOS 候选为 ad-hoc 签名且无 Team ID；不能据此宣称已公证或可安全分发。
- Pages 展示候选状态；官方 Release 仍以 GitHub Latest Release 为准。
- 全端目标保持进行中，任何未解决项都不能由本审计文档或通过 CI 替代。

## 2026-10-17 续核记录

- 当前分支 `codex/v1.0.39-miniprogram-lan-tcp` 的 HEAD 为 `32b9686d42731c52d185b629b3584ac7b9c9883c`，工作区起始时干净。Python 完整测试运行 78 项，76 项通过、2 项 Windows 条件跳过；小程序 TCP 客户端 Node 测试 4 项通过。
- 已安装 `/Applications/影序 YINGXU.app` 的 `http://127.0.0.1:8080/api/status` 返回 `version=1.0.40`、`status=idle`；进程监听 `*:8080`。这只证明 Mac 本机服务可用，不证明手机 LAN 访问。
- GitHub PR #4 仍为 OPEN / DRAFT、可合并，head 与本地 `32b9686` 一致；当前列出的 Windows preview 和可靠性矩阵检查均成功。Latest Release 仍为 `v1.0.34`，仅有 Windows EXE 与 `SHA256SUMS.txt`，故尚无 v1.0.40 正式发布。
- Pages 当前首页、`/download/` 和实际隐私页 `/privacy.html` 均返回 HTTP 200；`/privacy/` 返回 404，但源码导航链接指向 `/privacy.html`，因此 `/privacy/` 不是本项目配置的规范路由。
- iPhone 镜像现已显示 Safari，但状态栏为 5G、无 Wi-Fi 指示。未访问 Mac 局域网 URL，也未更改手机网络；iPhone/Android 同 Wi-Fi、配对、主屏幕安装、离线和网络切换仍待实机验收。
- Windows preview run `38930466820` 对提交 `5089fd0` 成功；回读 artifact `12058054414` 后确认 EXE 为 x64 PE，SHA-256 `73cf68485808898c4608858085ef5ddcabaa89f6701cfd5cbd18e532d438a7b3` 与包内清单一致。Reliability runs `38930457711`、`38930467148` 均成功。该产物仍是 unsigned preview，不是 Windows 实机安装验收。
- 原生签名/构建环境复核：钥匙串仅发现自签名 `Smart Media Backup Developer`（OU=Development，非 Apple Developer ID）；`xcode-select` 指向 Command Line Tools，`xcodebuild` 要求完整 Xcode；本机无 `adb`，`ANDROID_SDK_ROOT` 未设置。当前主机不能完成 iOS/Android 原生构建或 Apple 公证发行。

## 2026-10-17 Pocket TCP 会话加固

- 小程序 TCP 配对令牌现在绑定到建立配对的 TCP socket；其他 socket 即使拿到令牌也不能复用，连接关闭时桌面端自动撤销会话。小程序收到连接错误后关闭失效 socket、清除旧会话并回到配对界面。
- 新增真实本机 TCP 回归，验证跨连接令牌拒绝及异常断开后令牌撤销。Python 完整测试 79 项：77 通过、2 项 Windows 条件跳过；小程序 Node 测试 5 项通过。微信开发者工具仍因占位 `touristappid` 返回 code 10，未编译/预览。

## 2026-10-17 全端续核（提交 ff4d177）

- 当前工作树干净，分支 `codex/v1.0.39-miniprogram-lan-tcp`，HEAD `ff4d17744f08b4ed873f3eddac91ec5cd85201b3`。本机 `.venv/bin/python -m unittest discover -s tests -v`：79 项运行，77 通过、2 项 Windows 条件跳过；`node --test miniprogram/tests/*.test.cjs`：5 项通过；小程序 JS 语法、JSON 解析和 `git diff --check` 通过。系统 Python 缺少 Flask 的首次尝试不作为项目测试结果。
- 对 `ff4d177` 的 GitHub Reliability run `38932408213`（六矩阵）和 Windows preview run `38932408167` 均为 success；PR 自动检查与 push 检查均完成。
- 从 run `38932408167` 下载 artifact `12060016185` 并独立读取：`影序 YINGXU.exe` 是 x64 PE（machine `0x8664`），大小 27,759,055 bytes，SHA-256 `d5b252b8b7a1004d5a0ad917cececf2a6ee777ba202d8a9434f942bdd191f9af`，与包内 `SHA256SUMS.txt` 一致。该包为 unsigned preview，未在 Windows 实机安装或运行；本机副本位于 `/tmp/yingxu-windows-preview-ff4d177/`。
- 当前 `/Applications/影序 YINGXU.app` 仍运行 1.0.40；安装主程序 SHA-256 `8235e90d0b168bf0113dcb6d2c26e38b9427b80300bf61b7cb234ef8b0ea864c`，arm64、ad-hoc、无 Team ID。实时 API 返回 `status=idle`、`version=1.0.40`；`/`、`/transfer`、`/history`、`/settings`、`/pocket/`、`/pocket/manifest.webmanifest`、`/pocket/sw.js`、`/api/status` 均 HTTP 200。此次没有插入素材卡，故不把该次启动计为素材扫描验收。
- GitHub Pages 规范首页、`/download/`、`/privacy.html` 当前均 HTTP 200。Latest Release 仍为 `v1.0.34`，资产仅 Windows EXE 与 `SHA256SUMS.txt`。PR #4 仍 OPEN/DRAFT、mergeable，head 为 `ff4d177`；没有合并或发布。
- 本轮仍未完成：Windows 真机、iPhone/Android Pocket、原生 iOS/Android 工程与商店包、真实微信 AppID/工具编译/真机/审核、Developer ID 与公证、v1.0.40 正式 Release。网页在线备份服务也没有定义或部署；静态网站 200 不代表在线备份功能已完成。

## 2026-10-17 macOS PR 构建门禁

- `.github/workflows/release-macos.yml` 新增 PR 触发，覆盖 `desktop/**`、`smb/**`、`tests/**`、`requirements.txt`、`setup.py` 和工作流自身；手动构建与 `v*` tag 路径保留。
- 提交 `0b3e45f5cd46de175114303575e8fb70c8f07e61` 的 PR Reliability run `38934253354`、Windows preview run `38934253479`、macOS candidate run `38934253353` 均成功。证明该 PR 现在自动经过六矩阵测试、Windows x64 预览构建和 macOS DMG 构建。
- macOS artifact `12059024846`（20,814,632 bytes）下载后独立核验：artifact ZIP digest `d3ca1aca82cb913aba3df412ee5819fc65fd4f35f9267ffa1ad6eda703e70f6c`；DMG SHA-256 `b159d6f10ae4b6fadd142000c062fa7db6eac954b6efa9cccf81b9c6a6cd976d`，随包 SHA256SUMS 匹配，`hdiutil verify` valid。挂载包的 App 版本为 1.0.40、Mach-O arm64，`codesign --verify --deep --strict` 通过；签名仍 ad-hoc、无 Team ID、未公证。
- 这是 PR 候选构建门禁，不是公开发行或终端用户安装验收。PR #4 仍为 OPEN/DRAFT；Windows 真机、Apple 公证、移动端和小程序真机、商店审核仍未完成。
- 将该 CI DMG 解出到 `/tmp/yingxu-ci-candidate-0b3/` 后，以隔离配置与临时端口 `18182` 实际启动：API 返回 `version=1.0.40`、`status=idle`；`/`、`/transfer`、`/history`、`/settings`、`/pocket/`、`/pocket/manifest.webmanifest`、`/pocket/sw.js` 均 HTTP 200。测试配置使用空挂载点且未插入素材卡，没有执行素材读写；结束后已停止 PID `78683` 并确认临时端口不再响应。这验证了下载 DMG 的包内运行时路由，不等于物理素材验收或公证。

## 2026-10-17 续核（提交 04ce9d1）

- 当前分支为 `codex/v1.0.39-miniprogram-lan-tcp`，HEAD `04ce9d1bece4f5300fe1f378d03cf1b0b4be0f22`；除未跟踪的 `mobile/` 基础脚手架外，未见其他工作区改动。
- 本机复跑 `.venv/bin/python -m unittest discover -s tests -q`：79 项运行，77 通过、2 项 Windows 条件跳过。复跑 `node --test miniprogram/tests/pocket-client.test.cjs`：5 项通过。
- PR #4 仍 OPEN/DRAFT、mergeable，head 为 `04ce9d1`。对应 Reliability run `38998932307`、Windows preview run `38998932368`、macOS candidate run `38998932403` 均为 success。它们证明 CI 门禁通过，不证明 Windows 实机安装或终端用户验收。
- 新增的 `mobile/` 仅为 Expo SDK 58.0.14 / React Native 0.88.0 / React 19.3.0 基础脚手架，尚无 Router 页面、Pocket TCP 连接服务或 iOS/Android 安装包。尝试按 Expo 匹配版本安装 Router、AsyncStorage 与开发客户端时，npm registry 多次 `ECONNRESET`/超时；离线安装因缺少缓存元数据失败，停止继续重试。该脚手架不计为原生端功能完成。
- 当前主机 `xcode-select -p` 为 `/Library/Developer/CommandLineTools`，没有完整 Xcode；未发现 `adb` 或 Android SDK 环境变量。原生构建、签名和商店提交仍需对应工具链与账号。
- 本轮没有进行 Windows、iPhone、Android、微信开发者工具或真实 SD 卡验收；公开 Release 状态也没有在本轮从 GitHub API 重新确认。原有平台和发行门槛继续有效。

## 2026-10-17 原生 Pocket 首个可运行代码闭环

- `mobile/` 已安装 Expo Router、AsyncStorage、Expo Dev Client、`expo-system-ui` 与 `react-native-tcp-socket` 6.4.3；Expo SDK 58 匹配依赖检查通过。应用标识为 `yingxu-pocket`，iOS/Android bundle/package ID 暂用 `com.yingxuapp.pocket`；上线前仍需确认该标识可注册并属于发行账号。
- 新增原生 Pocket 页面和 TCP 客户端：校验私有 IPv4 与 6 位配对码；使用与桌面/小程序一致的 percent-encoded JSON newline 协议、端口 18080；支持桌面状态、进度、最近历史、拍摄备注读写；每 15 秒刷新。配对码和会话 token 只在内存中，AsyncStorage 仅保存电脑地址；应用切入后台时关闭 socket，使桌面端撤销该连接令牌。
- 新增 5 项 Node 协议测试，覆盖 UTF-8 字段往返、服务器错误、断线失败所有等待请求、超长帧/非法帧关闭、请求帧大小限制；5/5 通过。TypeScript `tsc --noEmit`、Expo lint 通过。
- Expo CNG `prebuild --no-install --platform all` 成功；Android 与 iOS Metro bundle 分别导出至 `/tmp/yingxu-pocket-android-export` 与 `/tmp/yingxu-pocket-ios-export`，各自打包约 2.6 MB。这里只证明 JS 编译和 native 项目生成，不证明 IPA/APK 构建、设备安装或 TCP 实机连通。
- `expo-doctor` 报告 14/20 项通过、6 项未通过：Expo config schema 检查因访问 Expo API 时 TLS 断开；若干依赖树检查的 `npm explain` 子命令失败；本机缺 CocoaPods；React Native Directory 将 `react-native-tcp-socket` 标为未验证 New Architecture。后者是明确的 iOS/Android 原生兼容风险，须通过 native build 与真机排除；本机又缺完整 Xcode、Android SDK/adb，当前无法完成该项。
- Expo SDK 58 默认 Android targetSdk 为 36，符合截至 2026-08-31 Google Play 新应用 target API 36 的当前提交门槛。Android 17 / targetSdk 37 开始要求直接 LAN TCP 声明并在运行时申请 `ACCESS_LOCAL_NETWORK`；SDK 58 的 target 36 暂不应提前请求该权限。参见[Google Play target API 政策](https://support.google.com/googleplay/android-developer/answer/11926878)与[Android 局域网权限说明](https://developer.android.com/privacy-and-security/local-network-permission)。
- 移动端仍未在 iPhone/Android 安装、未连真实桌面桥接、未完成锁屏/切网/重连验收；也未签名或上架。Expo Doctor 检查和 Android 运行时权限风险仍需在后续 SDK/发行门禁复核。

## 2026-10-17 Pocket 移动端 CI

- 新增 `.github/workflows/mobile.yml`：针对 `mobile/**` 的 PR 和 main push 运行；使用 Node 24、pnpm 11.25.0 和 frozen lockfile，执行 Expo 依赖兼容检查、lint、TypeScript、协议单测、CNG prebuild 以及 iOS/Android bundle export。
- 本机按该 workflow 命令顺序复核成功：锁文件安装、Expo install check、lint、typecheck、5 项 Node 测试、iOS/Android prebuild 及两端约 2.6 MB JS bundle export 均通过。尚未触发 GitHub Actions，因此远端 CI 结果待提交后核对。
- 这条 workflow 不构建签名 APK/IPA，也不证明 native module 在设备上的兼容性；完整 Xcode、Android SDK、设备安装及 Pocket 真机 TCP 仍未验收。
