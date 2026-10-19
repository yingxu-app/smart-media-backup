# 影序全端闭环状态审计 v1.0.40

审计日期：2026-10-17（当前核对至 PR head `72831641945f44c0786c8c5a405614dc9b74e8f8`；产品源码基线仍为 `9bbae707f51575a862693de4349b33de4135843d`）。范围依据用户目标覆盖 PC 桌面、手机端、网页、小程序、多端测试、部署与上架。本文把源码、CI、安装运行、公开发布和真机验收分别记录；候选构建不等于正式发行。

## 当前证据矩阵

| 端 / 交付项 | 已核实证据 | 结论 | 剩余门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | 当前 PR head `7283164` 的 candidate run `39034625447` success；artifact `12100988661` ZIP 20,953,121 bytes，SHA-256 `455c649de611e345b83ab78a29bbbe22fa71d5eb076067839a879fe6993ca991` 与 GitHub metadata 一致。内含 v1.0.40 DMG SHA-256 `303bfb155072dcc052ae4268017e60d7e539284a7d3dddd0c91c6cbf244529fe` 与清单一致；`hdiutil verify` VALID，app deep/strict codesign 通过、Mach-O arm64。签名仍 ad-hoc、无 Team ID，未公证。 | 当前 head 的候选包体与签名封装完整性已核验；这不是 Developer ID 签名、公证、另一台 Mac 安装或公开发行。 | Developer ID 签名与公证；正式 Release、下载页及另一台 Mac 安装回读。 |
| Windows 桌面 | 当前 PR head `7283164` 的 preview run `39034625416` success；artifact `12101762525` ZIP 27,493,734 bytes，SHA-256 `516d9e50360da16056f54c7808b63e1d7466d91ae4bc6814b162e7a6dd17a5e1` 与 GitHub metadata 一致。内含 x86-64 PE EXE SHA-256 `4a3de3bc73d2d8314707e4cc4fde9c2b34e0413b84e5ce6a2d51cc11ca9011d5`，与包内 `SHA256SUMS.txt` 一致。 | CI preview 构建与包体清单通过；仍无 Windows 真机安装、运行、Defender、读卡器或断盘恢复证据。 | 在真实 Windows PC 安装并逐项操作；测试 SD 卡、目标盘、恢复与升级；签名后发布正式安装包并从公开链接回读。 |
| 原生 iOS / Android | `mobile/` 有 Expo Router Pocket 客户端与 TCP 服务。当前 PR head `7283164` 的 Pocket run `39034625528` 三个 job 全部 success：JS/CNG/check、Android debug、iOS Simulator build。Artifact 列表仅 Android debug APK `12101758334`；ZIP 94,576,845 bytes，SHA-256 `99007e5f87030719f683f5c3cbaaa434c72a2cf0e331577f4892d919581a2eb7` 与 GitHub metadata 一致；内含 269,562,399-byte APK，本机 SHA-256 `a903ea33e7ea8657443eca249fbda9ef89ac9568cc109c4100b84ae462e39be3`，包含 arm64-v8a、armeabi-v7a、x86、x86_64；没有 iOS Simulator 包或 IPA。 | 当前 head 原生编译通过，Android debug APK 的 ZIP digest、APK 内容完整性和 ABI 已核验；仍未签名、未在实体 iPhone/Android 安装，无 LAN 授权或桌面 TCP 真机配对证据。本机无 Android SDK/adb 与完整 Xcode。 | 在真机完成安装、授权、配对、切网和重连；配置正式签名构建与商店资料，产出并检查签名 IPA/AAB、提审及上架。Expo SDK 58 默认 targetSdk 36，达到当前 Google Play 新应用 target API 门槛；未来升到 targetSdk 37 时须处理 Android 17 的 `ACCESS_LOCAL_NETWORK` 运行时权限。 |
| 手机端 / Pocket PWA | 源码包含独立 Pocket 页面、manifest、Service Worker 和状态/历史/备注 API。v1.0.40 页面在 LAN HTTP 明示离线缓存不可用，在安全上下文尝试注册缓存。当前 `/api/status` 返回 1.0.40。 | 桌面提供的移动网页能力已存在；手机浏览器安装、断网与跨网验收不成立。 | iPhone 与 Android 同 Wi-Fi 配对、主屏幕入口、锁屏/后台、休眠恢复、离线和网络切换实测；明确是否还需原生 iOS/Android 商店应用。 |
| 微信小程序 | `miniprogram/` 页面与 LAN TCP 客户端已补充非对象响应拒绝、切后台关闭会话；本机 Node 测试 7 项通过。桌面 TCP bridge 默认关闭。微信开发者工具 CLI 打开项目时，`touristappid` 返回 code 10“不存在此 AppID”。 | 原型代码通过本机测试，但 DevTools 编译未开始，尚无真实 AppID、真机或审核证据。正式连接方式未定。 | 配置真实 AppID 并通过开发者工具编译；确认局域网 TCP / 微信云托管中继 / 备案域名 HTTPS/WSS；真机配对、隐私审核和线上发布。 |
| 官网 / 网页 | 规范 Pages URL `https://yingxu-app.github.io/smart-media-backup/` 的首页、`/download/` 与 `/privacy.html` 本轮均 HTTP 200；privacy 首次 curl 遇 TLS 握手错误，紧接的 Python urllib 请求返回 200。下载页显示正式 Windows v1.0.34；Release API 列出 EXE 和 SHA256SUMS。旧组织根 URL 返回 GitHub Pages 404；Vercel 根页为旧内容，下载与隐私子路由 404。 | 静态介绍与下载页已在规范 Pages 路径部署；单次 TLS 错误属本次探测抖动，不证明线上故障；浏览器在线备份范围未确认。 | 若网页在线备份纳入范围，还需账户/数据/存储/隐私架构。 |
| 公开发行 | GitHub Latest Release 最近核验为 `v1.0.34`，资产仅 Windows EXE 与 `SHA256SUMS.txt`。PR #4 head `7283164` 为 OPEN/DRAFT、mergeable；Reliability PR `39034625439`、push `39034622595`、macOS candidate `39034625447`、Windows preview `39034625416`、Pocket `39034625528` 均 success。 | v1.0.40 未发布，v1.0.40 候选不构成公开正式发行。 | 完成平台真机验收、签名、公证/商店资料、版本升级回滚与公开下载入口验证后发布。 |

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

## 2026-10-17 current verification checkpoint — PR head `9bbae70`

- Refreshed repository state: branch `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `9bbae707f51575a862693de4349b33de4135843d`, worktree clean. PR #4 remains OPEN/DRAFT and mergeable.
- On this head, Reliability PR run `39015108813`, Reliability push run `39015105206`, macOS candidate `39015108870`, Windows preview `39015108802`, and Pocket run `39015108799` all completed successfully.
- **macOS candidate:** artifact `12094134210` ZIP SHA-256 `86473cfafdf3b7b347aa992d52da89f47cc78f8654546c4d945c6b9d95f8a846` matches GitHub metadata. DMG SHA-256 `a88570c2c321948df22f73bac3830f26048dedab4a1c98a0e129f4402da7ff19` matches its manifest; `hdiutil verify` returned VALID. Mounted v1.0.40 app is arm64 and passes deep/strict codesign verification; signature is ad-hoc without Team ID, and the app is not notarized.
- **Windows preview:** artifact `12093584501` ZIP SHA-256 `b5aeb2413f3524391c29a282c7687a85eec6c276549bce2d9e037b19cdd8a51a` matches GitHub metadata. EXE is PE32+ x86-64; SHA-256 `e90892aebfa686e1531ae1fadf77dab189c1a4710f89a61f19d30c640c609132` matches the embedded `SHA256SUMS.txt`. It is still a preview and has not been installed on a Windows PC.
- **Pocket:** JS/CNG/check, Android debug build and iOS Simulator build passed. The run uploaded Android debug APK artifact `12094239285` only; local APK SHA-256 is `b9017bc68e8145e52855e03504c9fab4df9d0cdae2d8456d3cd7ec2256edd640`, with ABI directories arm64-v8a, armeabi-v7a, x86 and x86_64. No iOS Simulator package or IPA was uploaded.
- **Website/release:** canonical Pages home, `/download/`, and `/privacy.html` returned HTTP 200. A single curl TLS error on the privacy URL was followed by a successful Python urllib 200 response. Latest Release remains `v1.0.34` with Windows EXE and `SHA256SUMS.txt` only; the download page presents v1.0.34.
- **Remaining:** Windows/iPhone/Android physical-device acceptance; real WeChat AppID, DevTools build, device review and publication; EAS login/project; Developer ID/Apple and Android signing, notarization/store submissions; formal release promotion; and user decision on browser online-backup scope. Do not treat CI or candidate package verification as these acceptance gates.

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
- 本机按该 workflow 命令顺序复核成功：锁文件安装、Expo install check、lint、typecheck、5 项 Node 测试、iOS/Android prebuild 及两端约 2.6 MB JS bundle export 均通过。首轮 PR run `39000546512` 成功，但发现传入 `pnpm/setup@v1` 的 `working-directory` 是不支持的输入；在 `195a608` 移除后，修正 PR run `39000627104` 全步骤通过，且无该告警。
- commit `195a608` 的 PR Reliability run `39000627095` 六矩阵全绿；macOS 候选 run `39000627152` 与 Windows preview run `39000627155` 成功；push Reliability run `39000624271` 六矩阵全绿。该 commit 当前 15 项 PR/push check 均为 success。
- 新增 Android debug APK 与 iOS Simulator 原生构建 jobs。首次 run `39000853629` 的 JS、CNG 和 bundle job 通过；iOS 原生构建因依赖要求 Swift 6.2、`macos-15` runner 提供 Swift 6.1 而失败，已改为 `macos-26`，修正后等待 Action 复核。Android debug 构建仍在该 run 中执行，尚无终态。
- 原生 CI 目标是不签名的 Android debug APK 和 iOS Simulator app；即使 CI 成功，也不证明商店签名包、设备安装、真实局域网 TCP 或其他平台真机验收。

## 2026-10-17 Pocket 原生 CI 终态（PR head `bb4cdb5`）

- Pocket workflow run [`39001877447`](https://github.com/yingxu-app/smart-media-backup/actions/runs/39001877447) completed/success。`pocket` job `117306339821`：Expo install check、lint、TypeScript、5 项 Node 协议测试、CNG prebuild、iOS/Android bundle exports 全部通过，用时 1m16s。
- iOS Simulator job `117306339650` completed/success，Build iOS Simulator app 通过，用时 18m6s。该 run 首次以 `macos-26-arm64` / Xcode 26.6.2 完成 React Native New Architecture 原生编译；这不是签名 IPA 或 iPhone 实机运行。
- Android debug job `117306339938` completed/success，`assembleDebug` 与 artifact upload 均通过，用时 22m26s。artifact `12089997551` / `yingxu-pocket-android-debug-e6b7bda9a7d7dab0a3c64ecfb70180529403fab1.zip` 大小 94,576,763 bytes，ZIP 内含一个 269,562,283-byte `app-debug.apk`；APK SHA-256 为 `e92dbb426b647b9c1d77ddc41e1e64aa9d6edf0f5aa3485716bc2cc9572329b5`，包含 `arm64-v8a`、`armeabi-v7a`、`x86`、`x86_64` 原生库。已下载到本机 `/tmp/yingxu-pocket-app-debug.apk`。这是 universal debug APK，不是 Google Play AAB/签名发行包，也未安装到 Android 真机。
- 该次 run `39001877447` 完成时 PR #4 head 为 `bb4cdb5c0f2c8121e7bdd32525917de5bd21974c`、merge state CLEAN；此为历史快照，不代表当前 PR head。PR checks 通过不等于设备验收或上架。
- 下一步：把该 artifact 用于可接触 Android 真机的安装/配对验收；准备正式 Android AAB、Apple 签名 IPA 和商店材料。iPhone/Android LAN 权限提示、桌面配对、后台/切网恢复仍未在设备上验证。

## 2026-10-17 小程序 Pocket 协议与后台会话加固

- 小程序 TCP 客户端现在要求桌面响应为非空 JSON object；`null`、数组、标量与无效 JSON 均按协议错误关闭连接并拒绝挂起请求。新增测试覆盖 `null`、`[]`、`42` 三种非对象帧。
- 小程序 `App.onHide` 现在调用当前页面的后台清理钩子，关闭活动 TCP socket、清除会话令牌与轮询，并提示返回后重新配对。Tencent Cloud 当前的 [小程序 App 生命周期 API](https://intl.cloud.tencent.com/zh/document/product/1219/61712) 列明 `onHide` 用于监听小程序切换到后台。
- 本地 `node --test miniprogram/tests/*.test.cjs` 7 项通过；移动端与小程序 Node 测试合计 12 项通过；桌面 `.venv/bin/python -m unittest discover -s tests -q` 运行 79 项、77 项通过、2 项 Windows 条件跳过。Expo lint、TypeScript、改动 JS 语法、相关 JSON 配置解析和 `git diff --check` 通过。
- 微信开发者工具已安装。本机 CLI 尝试打开 `miniprogram/`，因项目配置占位 AppID `touristappid` 返回 code 10“不存在此 AppID”，编译未开始；这不是编译失败，也没有产生真实 AppID 预览或真机证据。需要真实 AppID 才能继续开发者工具验收。
- 两个小程序修复提交 `4481450`、`3dd71c8` 已进入 PR #4。针对最新 head `3dd71c8` 的 test matrix 大部分已通过；run `39003760346` 的 Pocket job success，Android debug 与 iOS Simulator job 查询时仍在运行。PR 仍 OPEN/DRAFT，Windows/macOS/移动真机、签名和上架门槛未闭环。

## 2026-10-17 Windows v1.0.40 preview artifact 回读

- Windows preview run `39004002505` 对 PR head `f80408f` completed/success，artifact `12090117584` (`YINGXU-Windows-v1.0.40-unsigned-preview`) 未过期，大小 27,490,393 bytes。
- 下载后 ZIP 含 `SHA256SUMS.txt`（84 bytes）和 `影序 YINGXU.exe`（27,788,887 bytes）。从 ZIP 内直接计算的 EXE SHA-256 为 `cf67ea1a097c7b5d2fcb57828144cb1763f4d4b032aa7fcda86b76b946e8dfd8`，与包内清单逐项匹配；PE machine 为 `0x8664`，确认 x64。
- 该 artifact 是 unsigned preview；当前没有 Windows 实机安装、启动、Defender、读卡器/存储盘操作或拔盘恢复证据。

## 2026-10-17 当前候选复核与 Android D8 内存修复

- 当前仓库原 head `c3f91007357c063e080401742eaa66ced4ca1e62` 的 PR #4 仍为 OPEN/DRAFT。Reliability run `39004375878` 六平台矩阵通过；Windows preview run `39004375737` 成功，artifact `12090406203`（`YINGXU-Windows-v1.0.40-unsigned-preview`）下载回读成功。EXE 大小 27,790,294 bytes，类型 PE32+ x86-64；SHA-256 `d5e64c68527283e6964e1ba9f45c05f96e6a0ec205393670e19a98bea188aa61` 与包内 `SHA256SUMS.txt` 一致。
- macOS candidate run `39004375741` artifact `12090108688` 下载到本机。DMG 为 22,263,629 bytes，SHA-256 `53dd652fec3511899d0ecbdb7ddf17477729115cb199aca03aab3533e6cda25b` 与 ZIP 清单一致；`hdiutil verify` 返回 VALID，挂载内容中 v1.0.40 arm64 app 的 `codesign --verify --deep --strict` 通过。签名为 ad-hoc、无 Team ID、未公证。
- 本机已运行 `/Applications/影序 YINGXU.app`。`/api/health` 返回 version `1.0.40`、database `ok`；`/api/status` 为 idle。只读 `/api/sources` 重新识别 `/Volumes/SD_Card` 共 828 个文件（784 photos、44 videos）。本轮未复制或删除卡内文件。
- Pocket run `39004375789` 的 JS/CNG/lint/typecheck/protocol-tests 与 iOS/Android bundle exports 均成功。Android `android-debug` job `117313709428` 在 `:app:mergeExtDexDebug` 因 `java.lang.OutOfMemoryError: Java heap space` 失败；本地生成的 `android/gradle.properties` 默认 heap 为 2 GB。iOS Simulator job `117313709690` 查询时仍在原生构建。
- 已新增 Expo config plugin `mobile/plugins/withAndroidGradleMemory.js`，把 CNG 生成的 Gradle daemon heap 设为 4 GB；本机 `expo prebuild --no-install --platform android` 后确认生成 `org.gradle.jvmargs=-Xmx4096m -XX:MaxMetaspaceSize=1024m`。后续 PR run `39005227335` 在 Android debug job `117316209599` 完成原生构建与 artifact 上传，iOS Simulator job `117316209492` 也成功；修复在当前 head 获得 CI 验证。此前 Pocket lint/typecheck、5 项 mobile Node tests、7 项 Mini Program Node tests、桌面 unittest 79 项（77 pass、2 Windows-only skip）与 `git diff --check` 均通过。
- 本机没有 Android `adb`，`xcode-select` 指向 Command Line Tools 且没有 `devicectl`；不能在此主机完成 Android/iPhone 真机安装。正式 GitHub Release 仍是 `v1.0.34`（Windows EXE + `SHA256SUMS.txt`）。Android/iOS 商店签名、真机配对、小程序真实 AppID、Windows 真机与正式上架仍未完成。

## 2026-10-17 Pocket 原生 CI 终态（source commit `dc79744`）

- PR #4 在上述候选 CI 期间 head 为 `dc797446c2cf224fd4382b48284c6b3de3fca244`，状态 OPEN/DRAFT。PR Reliability run `39005227361`、push Reliability run `39005224989`、Windows preview run `39005227270`、macOS candidate run `39005227299` 和 Pocket run `39005227335` 均 completed/success。
- Pocket job `117316209594` 完成 Expo package compatibility、lint、TypeScript、协议测试、CNG prebuild 及 Android/iOS JS bundle exports。Android debug job `117316209599` 的 `assembleDebug` 与 artifact upload 均成功；job 用时 20m50s。iOS Simulator job `117316209492` 原生编译成功，用时 21m19s。
- 该 run 中 Android artifact `12091158046`（`yingxu-pocket-android-debug-2625b69f2e6f1a5a15537f14f67124b88557a810`）大小 94,576,874 bytes；GitHub artifact metadata digest 为 `sha256:78c3f2b13e9067f13f62a52475e8a8b68fc4ed06b83a9dad9886d54961f3ab9b`。本机通过 API 下载时速度极低，停止了未完成的本地传输；因此尚未解包并核对 APK 内部 SHA-256 和 ABI。Artifact 的 CI 构建/上传成功不等于设备安装验收。
- 先前 head `c3f9100` 的 Android D8 dex merge 曾因默认 2 GB Java heap OOM。提交 `c6a45d4` 的 Expo config plugin 把 CNG 生成的 `org.gradle.jvmargs` 调至 `-Xmx4096m -XX:MaxMetaspaceSize=1024m`；本机 CNG 验证生成值正确，当前 head 的 Android native build 成功，确认该修复通过这次 runner 验证。
- 当前 head 的 Windows artifact `12090732229` EXE 为 27,790,264 bytes、PE32+ x86-64，SHA-256 `524340c4bf36e7b705b0883b7cb2c290c5bdcffbe08f759a07be1077735db6ac` 与 `SHA256SUMS.txt` 匹配。macOS artifact `12090533009` DMG SHA-256 `894151b19506c7ea97d6e1b08ca196fb63b7df8f6128d5fda77b8f114f600c96` 与包内清单匹配，`hdiutil verify` 和 app deep/strict codesign 通过；仍为 ad-hoc、无 Team ID、未公证。
- GitHub Pages `/`、规范下载路由 `/download/` 与 `/privacy.html` 均 HTTP 200；下载页仍展示正式 Windows v1.0.34。Latest Release 仍 v1.0.34，仅 Windows EXE 与 `SHA256SUMS.txt`。
- 本机无 Android `adb` 和完整 Xcode `devicectl`，尚不能安装到 Android/iPhone 真机。商店正式签名与提审、小程序真实 AppID/编译预览/审核、Windows 实机/读卡器/断盘恢复、PWA 真机及最终平台范围选择均未完成。

## 2026-10-17 Pocket 原生 CI 终态（product head `970bb32`，PR check snapshot `a6de5f4`）

- Pocket run `39007205403` 对应的产品代码 head 为 `970bb3258770729a90b450b0fe6fa3116c91b841`；其终态时 PR #4 为 OPEN/DRAFT、merge state CLEAN，Reliability、macOS candidate、Windows preview、Pocket JS/CNG、iOS Simulator 和 Android debug checks 均通过。随后提交 `a6de5f4384db9ef12473c79c93e945105914e7a4` 只更新审计/计划文档与快照，没有改产品代码。
- 在 `a6de5f4` PR check snapshot 中，PR 为 OPEN/DRAFT；Reliability、macOS candidate、Windows preview 和 Pocket JS/CNG checks 已通过，该次 Pocket run `39008799597` 的 Android debug 与 iOS Simulator jobs 当时仍 pending。
- Pocket run [`39007205403`](https://github.com/yingxu-app/smart-media-backup/actions/runs/39007205403) completed/success。Pocket job `117321996603` 用时 1m5s；iOS Simulator job `117321996805` 用时 18m32s；Android debug job `117321996746` 用时 21m59s。iOS 证据仅为模拟器编译，不是签名 IPA 或 iPhone 真机运行。
- Android artifact `12092136782`，名称 `yingxu-pocket-android-debug-5451c2af07b6fc0b48c49bc92d566e32c15fa026`，大小 94,576,842 bytes，GitHub digest 为 `sha256:b670b777a07efc6532fdbc7906b442d7f63821ca5d075fe1ec079c9771a8f1d1`。通过 GitHub artifact 下载接口保存到本机后，ZIP 重算 digest 相同；ZIP 内 `app-debug.apk` 为 269,562,399 bytes，SHA-256 `adcd086a677906b54c2482fe124d4fa40f3896c959c29ee1f1124790270532a0`，包含 `arm64-v8a`、`armeabi-v7a`、`x86`、`x86_64`。该 APK 为 universal debug 包，不具备 Play 商店签名/发行证明，亦未安装到 Android 真机。
- 本轮在同一 HEAD 复跑桌面 unittest：79 项运行、77 项通过、2 项 Windows 条件跳过；小程序 Node tests 7/7 通过；Pocket lint、TypeScript 和 Node tests 5/5 通过；`git diff --check` 通过。桌面测试打印了本机 Ollama `localhost:1` 连接拒绝的 AI 命名日志，但测试整体退出码为 0。
- 本机 `/Applications/影序 YINGXU.app` 仍运行 v1.0.40；`/api/health` 为 `status=ok`、`database=ok`，`/api/status` 为 idle。GitHub Pages 首页、`/download/`、`/privacy.html` 本轮均 HTTP 200。Latest Release 仍为 v1.0.34；本地当前 PR head 的 macOS/Windows artifact 构建成功仍属于候选包证据。
- GitHub artifact download 通过 MCP 下载接口成功；本机 `/usr/local/bin/gh run download` 对同一 ZIP 运行约 1 分钟仍未产出文件，已中断该下载，不影响 workflow 构建或 MCP 下载得到的 artifact。
- 剩余：Windows 真机安装/读卡器/拔盘恢复；iPhone 与 Android 真机安装/权限/LAN 配对/后台切网；真实微信 AppID、DevTools 编译预览、真机和审核；Apple Developer ID、公证、签名移动包与商店审核；公开发布仍需统一版本、签名、回滚和下载验收。

## 2026-10-17 Pocket 配对地址误选 VPN 的修复（PR head `d223dfe`）

- 本机现场复核发现：旧 `_local_ip()` 通过 UDP 探测 `192.0.2.1` 时走系统默认路由 `utun8`，得到 `198.18.0.1`；本机 Wi-Fi 实际地址是 `192.168.31.172`。因此配对页会广告手机不可用的 VPN 地址。
- `smb/server.py` 现在枚举活动网卡，排除 tunnel/virtual 接口、环回/链路本地/保留网段地址，优先选择 Wi-Fi/Ethernet 私有 IPv4；网卡信息不可用时保留原路由探测作为 fallback。`/api/pocket/pairing` 回归测试覆盖 VPN 默认路由下广告正确 Wi-Fi IP 的行为。
- 源码环境 `_local_ip()` 实测返回 `192.168.31.172`。本轮桌面 unittest 82 项运行、80 项通过、2 项 Windows 条件跳过；Pocket lint、TypeScript 与 Node 协议测试 5/5 通过；小程序 Node 测试 7/7 通过；`compileall` 与 `git diff --check` 通过。
- 修复提交 `d223dfe3045d7c4f502b81acb90fa23f5aef3e68` 已推送至 PR #4。新 head 的 Pocket run `39009722200`、Windows preview `39009722244`、macOS candidate `39009722225` 查询时均为 queued。旧 head `5d17e14` 的 Pocket JS/CNG job 已通过，Android debug 与 iOS Simulator native jobs 仍在运行；这些旧 head 结果不验证本次修复。
- 尚未使用更新后的桌面候选在真实手机上配对；当前记录只证明源码选址与 API 行为，不证明路由器、防火墙、手机同 Wi-Fi、PWA 安装/离线或小程序 TCP 真机链路。待新 head 桌面候选可用后再做实机验收。

## 2026-10-17 LAN address fix: desktop candidate artifacts and runtime

- macOS candidate artifact from run [`39009788643`](https://github.com/yingxu-app/smart-media-backup/actions/runs/39009788643), source commit `33c71a3` (same product source as `d223dfe`; later `f7e5c8a` only strengthens tests): artifact ZIP SHA-256 `aa08012e218f808d18ab413e1e8244ad48044659f9278658d92992766a3fbde4`; contained DMG SHA-256 `ce98fd6f250762d416bc541354a560ff32a524ae3ee8fbefd5c65bee930c7626`, matching its manifest. `hdiutil verify` returned VALID; app deep/strict codesign passed. App is arm64 and ad-hoc signed, without Team ID.
- Ran that candidate directly from its read-only DMG with isolated `SMB_CONFIG_DIR` and port 18081, leaving `/Applications/影序 YINGXU.app` untouched. `/api/health` returned `status=ok`, `database=ok`, version `1.0.40`; `/api/pocket/pairing` returned `tcp_host=192.168.31.172` and `http://192.168.31.172:18081/pocket/`. The Pocket page served HTTP 200 through that host address; unpaired `/api/status` returned 403. Candidate process was stopped and DMG unmounted; installed app remained healthy on port 8080.
- Windows preview run [`39009837297`](https://github.com/yingxu-app/smart-media-backup/actions/runs/39009837297), head `f7e5c8a`, completed build job success. Artifact `12092750483` ZIP SHA-256 `250ff1588e452acdbf2ab50dc249ddff8c57aa693f7f81df28f76398ae0b6e07`; embedded EXE SHA-256 `95049d77e63e87286830d515a19ef12eef5ce57fcb3705e4182a1dbc954e8aaf`, matching `SHA256SUMS.txt`; file inspection confirms PE32+ x86-64. This is an unsigned preview, not Windows runtime acceptance.
- For latest head `f7e5c8a`, Reliability run `39009837275` had Linux and Windows matrix jobs successful while macOS matrix jobs remained queued; Pocket run `39009837265` had its JS/CNG job successful while Android debug and iOS Simulator native jobs remained in progress; macOS candidate run `39009837278` remained queued. PR #4 remained OPEN/DRAFT with checks pending.
- The Mac candidate runtime is stronger evidence than test-client coverage, but it is still a same-host request. Real iPhone/Android on the same Wi-Fi, firewall behavior, PWA install/offline, Mini Program TCP, Windows install, formal signatures and store release remain unverified.

## 2026-10-17 PR #4 candidate validation at head df24115

The following checks refer to the exact current PR head `df2411578a0598d8c82415eef41235860261a01f` (branch `codex/v1.0.39-miniprogram-lan-tcp`, PR #4 OPEN/DRAFT, mergeable). They supersede older CI snapshots above where a newer run exists.

- **macOS candidate:** run `39011334553` completed successfully; artifact `12093236578`, 20,950,217 bytes, GitHub digest `sha256:54ed88b29dda95b2b8198d4178508ca9e0fc3dc70cb4ffe864b266eff15fa757`. Local ZIP SHA-256 matched. Its DMG SHA-256 is `1da55c2eeae9adf4a3ee029bbb30e647f1d525fc93038bc985d2446fc45b8d64`, matching the embedded `SHA256SUMS.txt`; `hdiutil verify` returned VALID. Read-only mounted app reports v1.0.40, Mach-O arm64, and passes `codesign --verify --deep --strict`; signature is ad-hoc with no Team ID. This is a verified candidate, not a notarized or public release.
- **Windows preview:** run `39011334570` completed successfully; artifact `12093300236`, 27,493,031 bytes, GitHub digest `sha256:213ff3361d7f59008684d31ce1b4a0648969ecc2189fca5ab85f4a13cf23a332`. Local ZIP SHA-256 matched. Embedded EXE SHA-256 `f182f3bf0ab4b822bacb0a60a9788ff0f72596911143e81382ac79e485812131` matches the package manifest; PE machine is x86-64. It remains an unsigned preview and has not been installed on a Windows PC.
- **Reliability:** run `39011334711` completed successfully across all six OS/Python matrix jobs.
- **Transfer-old-content regression check:** confirmed `smb/transfer.py`, `smb/templates/transfer.html`, and `tests/test_transfer_safety.py` are tracked in the canonical checkout (feature commit `2941a30`); the focused current-worktree suite ran 10 tests and all passed. This confirms the old-session feature exists in the current repository, while physical Windows/removable-drive recovery remains untested.
- **Pocket:** run `39011334571` Pocket JS/CNG/lint/typecheck/protocol tests and iOS/Android bundle exports completed successfully. At the last live poll, Android debug job `117334323780` was still building the APK and iOS Simulator job `117334323944` was still compiling the app. Do not count either native job as complete until a later terminal poll.
- **Remaining gates:** Windows and phone real-device use, Mini Program real AppID/DevTools/real-device review, Expo owner login and EAS project setup, Apple/Google signing and store submission, and formal public release remain unverified or unconfigured. Latest Release remains v1.0.34 at the last verified checkpoint.

### Same-host runtime check of the df24115 macOS candidate

- Launched the v1.0.40 app from the read-only artifact DMG through LaunchServices with isolated `SMB_CONFIG_DIR` and port 18083; the installed `/Applications/影序 YINGXU.app` was left untouched. `/api/health` returned `status=ok`, `database=ok`, version `1.0.40`.
- Pairing advertised Wi-Fi address `192.168.31.172` and `http://192.168.31.172:18083/pocket/`. Through that LAN address, `/pocket/` returned HTTP 200, unauthenticated `/api/status` returned 403, and `/api/pocket/status` returned 401. A loopback `/api/status` request returned 200 by design because the desktop UI is trusted on loopback; the LAN-path checks are the relevant Pocket exposure check.
- The candidate process was stopped and its DMG detached. This is same-host routing evidence, not a phone-on-Wi-Fi pairing test.

### Current public-site check caveat

- GitHub Latest Release still identifies `v1.0.34`, with assets `YINGXU-Windows-v1.0.34.exe` and `SHA256SUMS.txt`.
- Homepage and privacy page returned HTTP 200 on this check. The download route request ended in TLS/connection EOF from the audit host, so its current response is inconclusive; this transport result does not prove that the deployed route is down or healthy.

## Current verification checkpoint — PR head ae44735

- PR #4 head is `ae4473533f9b87081d57afe81a74d0d2379af2d7`, OPEN/DRAFT and mergeable. This commit contains only the candidate evidence audit and pre-edit snapshots; product code is unchanged from `df24115`.
- macOS run `39012271620` and Windows run `39012271576` completed successfully. Their artifact ZIP hashes matched GitHub metadata; package-internal DMG/EXE hashes matched their manifests. The macOS DMG passed `hdiutil verify`; its v1.0.40 arm64 app passed deep/strict codesign checks. Windows preview is unsigned x86-64. Same-source macOS candidate runtime evidence is recorded above.
- Reliability PR run `39012271555` and push run `39012268735` both completed successfully across all six OS/Python jobs.
- Local current-checkout verification: `.venv` unittest ran 82 tests (80 passed, 2 Windows-conditional skips); Mini Program Node tests passed 7/7; the focused transfer safety tests passed 10/10; `git diff --check` passed. The suite printed an optional local Ollama connection-refused message, but exited 0.
- Current Pocket run `39012271597` completed successfully: JS/CNG/lint/typecheck/protocol, Android debug job `117337141000`, and iOS Simulator job `117337140938` all passed. The artifact list contains only the Android debug artifact; no iOS simulator app or signed IPA artifact was uploaded. Android artifact `12093254859` ZIP (94,576,845 bytes) SHA-256 `36b13b0b8fe6fbdc65985e224715d7d998cc684a62696ac69084c1bf215cc543` matches GitHub metadata. The ZIP contains only `app-debug.apk` (269,562,399 bytes), no SHA256SUMS file; local APK SHA-256 `ed4f2ac38957c6ff5dd17e337fd7639f68a90383afa32bb9cacfc1e0224e471c`, ABI directories `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64`. This is an unsigned debug APK, not a store package or device install.
- Latest Release remains `v1.0.34`. Current home/privacy checks returned HTTP 200, while the download-route request failed at the audit host with TLS/connection EOF and remains inconclusive. Do not treat that transport result as a server outage or a success.

## 2026-10-17 current live recheck — PR head `3c68fe4`

- Current worktree is clean on `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `3c68fe4583eed8916f7dfe28ce1feafbb2142485`. PR #4 remains OPEN/DRAFT and mergeable.
- On this exact head, PR Reliability run `39013794116`, push Reliability run `39013788234`, macOS candidate run `39013794195`, and Windows preview run `39013794501` completed successfully.
- Pocket run `39013794196`: Pocket JS/CNG/check job and Android debug job `117341606796` completed successfully. Android artifact `12093724774` was downloaded: GitHub metadata size 94,576,846 bytes and digest `sha256:8f4d6aaad3d965a5a5b84bc90ae95a1a93c8a7ceb03633650b00ba4b5680eeac`; `app-debug.apk` is 269,562,399 bytes with local SHA-256 `5f83d2e3b3a1177a087eee0e22aa4122397beea2ae9aa66fff2d517f30969758` and ABIs arm64-v8a, armeabi-v7a, x86, x86_64. This is a debug APK, not a Play package or device acceptance.
- Pocket run `39013794196` is now completed/success; iOS Simulator job `117341606981` completed/success. The run uploaded only the Android debug APK artifact; no iOS Simulator app or signed IPA artifact is available.
- Canonical website paths `https://yingxu-app.github.io/smart-media-backup/`, `/download/`, and `/privacy.html` returned HTTP 200. The old organization root URL returned the GitHub Pages “Site not found” 404 page, and API lookup for the old standalone `yingxu-app/yingxu-app.github.io` repo returned 404. Do not restore the stale local standalone-site clone (it advertises macOS v1.0.31 and Windows v1.0.33).
- GitHub Release API lists the expected Windows v1.0.34 EXE and `SHA256SUMS.txt`, but direct asset download from this audit host failed during TLS handshake with EOF; this does not establish whether the asset is unavailable to users. Verify the download from another available network before claiming end-to-end delivery success.
- `https://smart-media-backup.vercel.app/` root returned HTTP 200 but showed older marketing content; `/download/` and `/privacy.html` returned 404. It is not a complete current mirror. The canonical Pages site is configured from the main repository's workflow; deployment run `38924919861` succeeded.
- Remaining release gates include Windows and phone real-device acceptance, real WeChat AppID/DevTools review, EAS account/project setup, formal signing/notarization/store submission, and the final website online-backup scope.

## Follow-up verification — docs head `7039ca8`, product source `9bbae70`

- Current checkout remains on `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `7039ca8f0b8c9ada22c0064db3353cce1d0f9f9c`; product source matches `9bbae707f51575a862693de4349b33de4135843d`, and the intervening changes are documentation/snapshots only.
- Local regression: Python unittest 82 total / 80 passed / 2 Windows-only skipped; Mini Program Node 7/7; Pocket mobile Node 5/5; Expo lint and TypeScript no-emit typecheck succeeded. The optional local Ollama endpoint refused its connection; tests still exited 0.
- Packaged macOS candidate runtime: read-only v1.0.40 DMG, isolated config and port 18184. Health/database OK; desktop idle; Pocket and desktop loopback routes returned 200; LAN management endpoint returned 403; unpaired LAN Pocket status returned 401. TCP bridge disabled/no port 18080 listener. Candidate process stopped, test port released and DMG detached, with no media operations.
- Public recheck: Pages home and `/download/` HTTP 200. The audit host's curl hit TLS error for `/privacy.html`, then `/usr/bin/python3` urllib returned HTTP 200. Latest Release API still reports v1.0.34 with Windows EXE and checksum only.
- Docs-head Pocket run `39033010125`: Pocket JS/CNG/check passed; Android debug and iOS Simulator jobs were still in progress at the last poll. Continue polling this exact run; do not restart it.
- These checks do not close Windows/iPhone/Android device acceptance, WeChat real-AppID/DevTools/review, EAS project and owner login, formal signing/notarization, stores, official release/rollback, or web online-backup scope.

## Correction: Pocket run `39033010125` terminal result on docs head `7039ca8`

- Final live job query shows Pocket JS/CNG/check `117397111823`, iOS Simulator `117397111736`, and Android debug `117397111886` all completed successfully.
- Artifact API lists only Android artifact `12101672408` (94,576,872 bytes). Downloaded ZIP SHA-256 `0f7ed3e140bc921d6e31bb73d5895ede95692d0e27c399f6e89c63cce220e3a8` matches GitHub metadata. It contains `app-debug.apk` (269,562,399 bytes, SHA-256 `15074a39103722de72c66e7102df01bb4ab65023f9946032ce7c66024379d703`) with ABIs arm64-v8a, armeabi-v7a, x86, and x86_64.
- This artifact is a debug APK; it does not establish Android-device acceptance, release signing, or store publication. The successful iOS Simulator build uploaded no iOS app or IPA and is not iPhone acceptance.
- No product source changed. Real device, Mini Program account/review, EAS project/login, signing, store, formal Release, and browser-online-backup-scope gates remain open.

## 2026-10-17 current verification checkpoint — PR head `7283164`

- PR #4 is OPEN/DRAFT and mergeable at `72831641945f44c0786c8c5a405614dc9b74e8f8`; branch `codex/v1.0.39-miniprogram-lan-tcp`. The head contains documentation and snapshots only; product source remains `9bbae707f51575a862693de4349b33de4135843d`.
- Reliability PR `39034625439`, Reliability push `39034622595`, macOS candidate `39034625447`, and Windows preview `39034625416` all completed successfully. Their artifact ZIP and package-internal verification is summarized in the current evidence matrix above.
- Pocket run `39034625528` completed successfully: JS/CNG/check job `117401857804`, Android debug job `117401857937`, and iOS Simulator job `117401858066` all succeeded.
- Android artifact `12101758334` was downloaded. Its ZIP size is 94,576,845 bytes and SHA-256 `99007e5f87030719f683f5c3cbaaa434c72a2cf0e331577f4892d919581a2eb7`, matching GitHub metadata. ZIP integrity check passed. It contains `app-debug.apk` (269,562,399 bytes; SHA-256 `a903ea33e7ea8657443eca249fbda9ef89ac9568cc109c4100b84ae462e39be3`) with `arm64-v8a`, `armeabi-v7a`, `x86`, and `x86_64` libraries. Artifact list contains no iOS Simulator app or IPA.
- This proves exact-head CI builds and Android debug artifact integrity only. It does not prove Android/iPhone installation, LAN pairing/reconnection, production signing, or store distribution. The formal Release remains `v1.0.34`; other real-device, WeChat AppID/DevTools/review, EAS owner/project, signing, notarization/store, and browser online-backup scope gates remain open.
