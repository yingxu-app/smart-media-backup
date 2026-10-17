# 影序全端闭环计划 v1.0.40

核对日期：2026-10-17（当前核对至 PR head `9bbae707f51575a862693de4349b33de4135843d`）。此计划把“功能完成、平台验证、部署、公开发行”拆开记录；CI、模拟环境或候选包不能代替实机和线上验收。

## 当前交付面与权威证据

| 交付面 | 当前实现 / 已有证据 | 当前状态 | 闭环门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | 当前 PR head `9bbae70` 的候选 run `39015108870` success；artifact `12094134210` ZIP SHA-256 `86473cfafdf3b7b347aa992d52da89f47cc78f8654546c4d945c6b9d95f8a846` 与 GitHub metadata 一致。内含 v1.0.40 DMG SHA-256 `a88570c2c321948df22f73bac3830f26048dedab4a1c98a0e129f4402da7ff19` 与包内清单一致；`hdiutil verify` VALID，app deep/strict codesign 通过、Mach-O arm64。签名仍 ad-hoc、无 Team ID，未公证。 | 当前 head 的候选包体与签名封装完整性已核验；不是 Developer ID 签名、公证、另一台 Mac 安装或公开发行。 | Developer ID 签名与公证；正式 Release、下载页及另一台 Mac 安装回读。 |
| Windows 桌面 | 当前 PR head `9bbae70` 的 preview run `39015108802` success；artifact `12093584501` ZIP SHA-256 `b5aeb2413f3524391c29a282c7687a85eec6c276549bce2d9e037b19cdd8a51a` 与 GitHub metadata 一致。内含 x86-64 PE EXE SHA-256 `e90892aebfa686e1531ae1fadf77dab189c1a4710f89a61f19d30c640c609132`，与包内 `SHA256SUMS.txt` 一致。 | CI preview 构建与包体清单通过；仍无 Windows 真机安装、运行、Defender、读卡器或断盘恢复证据。 | 在真实 Windows PC 安装并逐项操作；测试 SD 卡、目标盘、恢复与升级；签名后发布正式安装包并从公开链接回读。 |
| 手机 PWA | Pocket 页面、状态、历史和拍摄备注接口及 manifest / Service Worker 已有源码；v1.0.40 在安装版真实浏览器中通过 HTTP LAN 显示离线限制、loopback 显示页面缓存就绪。 | Mac 浏览器 runtime 已核验；没有 iPhone/Android 同 Wi-Fi 实测、主屏幕安装、后台/切网/离线验收。LAN HTTP 下 Service Worker 不可用，不能把离线缓存记为已交付。 | 在 iPhone 与 Android 真机完成配对、状态、历史、备注、锁屏唤醒、网络切换、离线与撤销验收；为需离线能力的 PWA 配置受信任 HTTPS，或由原生客户端承接；明确 PWA 是否构成最终移动交付。 |
| 原生 iOS / Android | 当前 PR head `9bbae70` 的 Pocket run `39015108799` 三个 job 全部 success：JS/CNG/check、Android debug、iOS Simulator build。Artifact 仅 Android debug APK `12094239285`，SHA-256 `b9017bc68e8145e52855e03504c9fab4df9d0cdae2d8456d3cd7ec2256edd640`，包含 arm64-v8a、armeabi-v7a、x86、x86_64；没有 iOS Simulator 包或 IPA。 | 当前 head 原生编译通过，Android debug APK 已核验；仍未签名、未在实体 iPhone/Android 安装，也无 LAN 授权或桌面 TCP 真机配对证据。 | 在真机完成安装、授权、配对、切网和重连；配置正式签名构建与商店资料，产出并检查签名 IPA/AAB、提审及上架。Expo SDK 58 默认 targetSdk 36，达到当前 Google Play 新应用 target API 门槛；未来升到 targetSdk 37 时须处理 Android 17 的 `ACCESS_LOCAL_NETWORK` 运行时权限。 |
| 微信小程序 | `miniprogram/` 页面和 TCP 客户端已存在；桌面 TCP bridge 默认关闭，启用后监听 `18080`。本地 Node 测试现为 7 项通过，包含非法响应帧拒绝和切后台清理；小程序脚本语法与配置 JSON 解析通过。 | 微信开发者工具 CLI 实际打开项目时因占位 AppID `touristappid` 返回 code 10“不存在此 AppID”，尚未进入编译；没有真实 AppID、真机或审核证据。当前源码路线为同一局域网直连，正式数据路径仍待确认。 | 配置真实 AppID 后完成开发者工具编译预览；确认正式连接架构；iPhone/Android 微信真机验收配对、前后台、切网、过期/撤销；补隐私指引并提交审核，核对线上版本。 |
| 官网与浏览器产品 | 主仓库 `site/` 的规范 Pages 路径为 `https://yingxu-app.github.io/smart-media-backup/`；首页、`/download/`、`/privacy.html` 本轮复核均 HTTP 200（privacy 的 curl 探测曾遇 TLS 错误，随后 Python urllib 请求返回 200）。下载页列出正式 Windows v1.0.34。 | 静态官网与下载页已部署；浏览器在线备份范围未定义。 | 确认网页是否还需浏览器内导入/备份；在线备份若纳入范围，还需账户/数据/存储/隐私架构。 |
| 正式发布与售后回滚 | GitHub Latest Release 为 `v1.0.34`，资产仅 Windows EXE 与 `SHA256SUMS.txt`。PR #4 当前 head `9bbae70` OPEN/DRAFT、mergeable；Reliability PR/push、macOS candidate、Windows preview、Pocket run 均 success。 | v1.0.40 候选包和 debug/simulator build 不是多平台正式发行。 | 完成 Windows/mobile 真机验收和签名；准备隐私及商店资料；发布正式 Release、更新下载页，验证新用户下载、安装、升级与回滚。 |

## 共同完成门槛

1. **功能**：从“复制新内容”和“转移老内容”两条主流程逐项验收；转移包含废片、重复、分类命名、暂停/取消、校验失败保护与可恢复结果。
2. **数据安全**：原素材读写边界、重名不覆盖、哈希校验、拔盘/进程中断恢复、隐私最少化；任何删除来源动作都需在实际设备上验证。
3. **平台矩阵**：Windows、macOS、iPhone、Android、微信开发者工具和真机分别给出证据；平台间共享源码或 CI 绿灯不替代终端体验验证。
4. **部署/发行**：候选构建、签名包、商店审核、线上公开下载/安装、版本读回分别记录；一端上线不代表其他端完成。
5. **回滚**：每次正式替换保留旧安装包/版本和恢复说明；数据库升级需证明旧历史可读。

## 待用户一次性决定的范围

1. 手机端：是否同时交付 PWA 与原生 iOS/Android，还是 PWA 即为移动正式交付；若需原生上架，确认可接受的开发者账号/签名和商店资料准备。
2. 微信小程序：同一局域网 TCP（无云数据路径、仅本地网络）或微信云托管中继（可远程、需配置云环境）；也可分阶段支持两种路线。
3. 网页：只维护产品官网/下载站，还是增加浏览器在线备份产品；后者需重新定义文件访问、安全与浏览器兼容范围。

## 可并行推进

- 持续维护桌面主功能、测试与 Windows/macOS 候选证据；优先补 Windows 真机与现有 Pocket 真机网络验收。
- 复核正式网站与下载页，不把候选直接部署为正式下载。
- 不公开发布、不启用云付费服务、不索要任何账号密码或验证码；等架构决定后再开发依赖该决定的端侧集成。

## 2026-10-17 current verification checkpoint — PR head `9bbae70`

- Refreshed repository state: branch `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `9bbae707f51575a862693de4349b33de4135843d`, worktree clean. PR #4 is OPEN/DRAFT and mergeable.
- On this head, Reliability PR run `39015108813`, Reliability push run `39015105206`, macOS candidate `39015108870`, Windows preview `39015108802`, and Pocket run `39015108799` all completed successfully.
- macOS artifact `12094134210` ZIP SHA-256 `86473cfafdf3b7b347aa992d52da89f47cc78f8654546c4d945c6b9d95f8a846` matches GitHub metadata. Its v1.0.40 DMG SHA-256 `a88570c2c321948df22f73bac3830f26048dedab4a1c98a0e129f4402da7ff19` matches its manifest; `hdiutil verify` returned VALID. The app is arm64 and passes deep/strict codesign verification, but its ad-hoc signature has no Team ID and it is not notarized.
- Windows artifact `12093584501` ZIP SHA-256 `b5aeb2413f3524391c29a282c7687a85eec6c276549bce2d9e037b19cdd8a51a` matches GitHub metadata. The bundled x86-64 EXE SHA-256 `e90892aebfa686e1531ae1fadf77dab189c1a4710f89a61f19d30c640c609132` matches its manifest. The preview has not been installed on a Windows PC.
- Pocket run `39015108799` passed JS/CNG/check, Android debug and iOS Simulator builds. Artifact `12094239285` is an Android debug APK only; local SHA-256 `b9017bc68e8145e52855e03504c9fab4df9d0cdae2d8456d3cd7ec2256edd640`, ABIs arm64-v8a, armeabi-v7a, x86 and x86_64. No iOS Simulator app or IPA artifact was uploaded.
- Canonical Pages home, `/download/` and `/privacy.html` returned HTTP 200. One curl TLS error on privacy was followed by Python urllib HTTP 200. Latest Release remains `v1.0.34`, with only Windows EXE and `SHA256SUMS.txt`; the download page displays v1.0.34.
- **Open closure gates:** Windows/iPhone/Android real-device acceptance; real Mini Program AppID/DevTools/preview/device review/submission; EAS owner login and project; formal platform signing, Apple notarization, store submission, public release and upgrade/rollback; user decision on browser online-backup scope. CI, source checks, and candidate package hashes do not replace these gates.

## Follow-up verification — docs head `7039ca8`, product source `9bbae70`

- Re-read the current checkout: branch `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `7039ca8f0b8c9ada22c0064db3353cce1d0f9f9c`. The delta from product-source head `9bbae70` is audit/closure documentation plus pre-edit snapshots only.
- Local regression on this checkout: Python unittest ran 82 cases, 80 passed and 2 Windows-only cases skipped; Mini Program Node tests passed 7/7; Pocket mobile Node tests passed 5/5; Expo lint and TypeScript no-emit typecheck both exited successfully. The desktop suite logged an expected offline Ollama connection-refused diagnostic while returning exit code 0.
- The macOS v1.0.40 CI candidate from artifact `12094134210` was launched from its read-only DMG with an isolated config and port 18184. Health/database were OK, version 1.0.40 and idle; loopback desktop/Pocket routes returned 200. LAN `/api/status` returned 403 and unpaired LAN `/api/pocket/status` returned 401. TCP bridge was disabled and port 18080 had no listener. No media was copied or deleted; the process was stopped, port 18184 was released, and the DMG was detached. This is same-Mac runtime evidence only.
- Live GitHub check found a new Pocket run `39033010125` for docs head `7039ca8`: Pocket JS/CNG/check job passed, while Android debug APK and iOS Simulator build jobs remained in progress at the last poll. Do not rerun it; record terminal results only after polling this same run.
- Public status recheck: canonical Pages home and `/download/` returned HTTP 200. `curl` failed TLS on `/privacy.html`; system `/usr/bin/python3` urllib then returned HTTP 200. GitHub Latest Release API reports `v1.0.34`, published 2026-09-12, with only `YINGXU-Windows-v1.0.34.exe` and `SHA256SUMS.txt`.
- Product source remains unchanged. Real-device, WeChat AppID/DevTools/review, EAS owner project/login, signed/notarized packages, store submission, public release/upgrade/rollback, and the browser online-backup scope are still open.

## Correction: Pocket run `39033010125` terminal result

- Re-polled the same run; it completed successfully. Pocket JS/CNG/check job `117397111823`, iOS Simulator build job `117397111736`, and Android debug build job `117397111886` all concluded success.
- The run uploaded Android artifact `12101672408` only (94,576,872-byte ZIP, SHA-256 `0f7ed3e140bc921d6e31bb73d5895ede95692d0e27c399f6e89c63cce220e3a8`). The locally downloaded ZIP hash matches the GitHub artifact metadata.
- ZIP contains `app-debug.apk` (269,562,399 bytes; SHA-256 `15074a39103722de72c66e7102df01bb4ab65023f9946032ce7c66024379d703`) with `arm64-v8a`, `armeabi-v7a`, `x86`, and `x86_64` native libraries. This remains an unsigned debug APK, not device or store acceptance.
- No iOS Simulator app or IPA artifact was uploaded. Simulator build success does not prove iPhone installation or App Store signing.

## PWA 安全上下文依据

- [MDN Secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts) 说明普通安全上下文需 HTTPS；`localhost`/loopback 是开发例外，局域网 IP 不因此自动获得例外。
- [MDN Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) 说明 Service Worker 仅在 secure context 可用。当前 Pocket 通过 `http://<桌面局域网 IP>:8080/pocket/` 配对；在未完成真实 iPhone/Android 验证前，离线缓存和主屏幕体验均保持未验收。

## 2026-10-17 配对地址修复后的当前进度

Pocket 配对地址误选 VPN 已在 PR #4 head `d223dfe` 修正：本机 `_local_ip()` 返回活动 Wi-Fi 地址 `192.168.31.172`，接口级、配对 API、桌面全套、移动端和小程序自动检查通过。新 head 的 Pocket、macOS candidate 与 Windows preview 仍待 CI 终态；因此尚不能安装新候选做真实 iPhone/Android 局域网配对。旧 head `5d17e14` 的 iOS Simulator 与 Android debug 构建仍在运行，完成后可作为该旧 head 的构建证据，不能替代新 head 检查。

下一步按顺序：读取新 head 三条 CI 终态；检查新 macOS/Windows 候选并保留可回滚安装版本；在同 Wi-Fi 手机验证 Pocket 页面、配对、状态/历史/备注、锁屏/切网恢复；对原生客户端复核 iOS 权限和 Android TCP 后台行为。Windows 实机、真实微信 AppID/开发者工具/审核、移动商店签名/账号、在线网页产品范围仍分别缺证据或配置。

## 2026-10-17 Candidate package runtime check

The macOS artifact from run `39009788643` was checksum-verified, passed `hdiutil verify` and deep/strict ad-hoc codesign checks, then ran from its read-only DMG under isolated config/port. Health/database were OK; pairing advertised the Wi-Fi IP; the Pocket page returned HTTP 200 through that address; an unpaired status API request returned 403. The candidate was stopped and unmounted; the installed v1.0.40 app stayed healthy. This verifies packaged runtime behavior on the same Mac, not a phone over Wi-Fi.

The Windows unsigned preview from run `39009837297` built successfully; its artifact ZIP and EXE manifest hashes match, and the EXE is PE32+ x86-64. Latest head `f7e5c8a` still has Reliability macOS matrix, Pocket Android/iOS native builds and macOS candidate workflow pending. Windows real-device install, phone pairing, WeChat DevTools/real AppID, formal signing and public release remain open.

## 2026-10-17 EAS store-build preparation (head `de6f82a`)

- Added `mobile/eas.json` with development-client, Android preview APK, Android production AAB, production iOS build defaults, and Android Play internal-track submit settings. Expo app version source is local; no remote version counter is initialized.
- Added `docs/MOBILE-STORE-RELEASE.md` with owner-side EAS linking/build/submit steps and explicit credential boundaries. Existing app config resolves successfully as slug `yingxu-pocket`, version `1.0.0`, and matching iOS/Android identifier `com.yingxuapp.pocket`.
- Preserved pre-change `mobile/app.json` and `mobile/package.json` in `docs/snapshots/2026-10-17-pre-eas-release-config/`.
- This configuration is not an EAS project link, signed build, store submission, or release. EAS project ID, Apple team/App Store Connect app, Apple signing credentials, and Google Play service account still need owner setup. Do not add secrets to the repository.
- `pnpm dlx eas-cli@latest whoami` ran from the local package cache and returned `Not logged in`; this confirms no usable Expo account session. The setup guide now uses `pnpm dlx` and starts with account login and project initialization. Android/iOS local device tools remain absent on this Mac.

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

- Worktree is clean on `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `3c68fe4583eed8916f7dfe28ce1feafbb2142485`; PR #4 is OPEN/DRAFT and mergeable.
- Current-head PR Reliability `39013794116`, push Reliability `39013788234`, macOS candidate `39013794195`, and Windows preview `39013794501` completed successfully.
- Pocket run `39013794196` has completed the Pocket JS/CNG/check job and Android debug job `117341606796` successfully. Artifact `12093724774` downloaded; GitHub metadata: 94,576,846 bytes, digest `sha256:8f4d6aaad3d965a5a5b84bc90ae95a1a93c8a7ceb03633650b00ba4b5680eeac`. Its `app-debug.apk` is 269,562,399 bytes; local SHA-256 `5f83d2e3b3a1177a087eee0e22aa4122397beea2ae9aa66fff2d517f30969758`; ABIs: arm64-v8a, armeabi-v7a, x86, x86_64. This is a debug artifact, not a store package or device acceptance.
- Pocket run `39013794196` completed successfully. iOS Simulator job `117341606981` completed successfully; the run's artifact list contains only the Android debug APK, no iOS Simulator app or IPA.
- The canonical Pages home, `/download/`, and `/privacy.html` under `https://yingxu-app.github.io/smart-media-backup/` all returned HTTP 200. The legacy org root URL returns a GitHub Pages “Site not found” 404, and API lookup for the old standalone `yingxu-app/yingxu-app.github.io` repo returns 404. Do not publish the stale local clone, which advertises macOS v1.0.31 and Windows v1.0.33.
- GitHub Release API lists the expected Windows v1.0.34 EXE and checksum file, but direct asset downloads from the audit host failed during TLS handshake with EOF; end-to-end public download remains unverified from this host.
- `https://smart-media-backup.vercel.app/` root returns HTTP 200 with older marketing content; `/download/` and `/privacy.html` return 404. It is not a complete current mirror. Pages uses the main repository's workflow; deployment run `38924919861` succeeded.
- Still open: Windows and mobile real-device use, real WeChat AppID/DevTools/review, EAS account/project setup, formal Apple/Google signing, notarization and store release, and the scope of browser-based backup.
