# 影序全端闭环计划 v1.0.40

核对日期：2026-10-17。此计划把“功能完成、平台验证、部署、公开发行”拆开记录；CI、模拟环境或候选包不能代替实机和线上验收。

## 当前交付面与权威证据

| 交付面 | 当前实现 / 已有证据 | 当前状态 | 闭环门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | 产品代码 head `970bb32` 的 candidate run `39007205435` success；artifact `12090943061`（ZIP 20,952,624 bytes，metadata digest `sha256:b0c95d01f9fb06a4d26dc4d335ae699687b784bf7f7cdd975c691015e44fda7b`）。DMG SHA-256 `45f72f544dcefb5f77ea554256273a7d7f9633d4c18e61a04c1e52357c3e47a8` 与包内清单一致；`hdiutil verify` VALID，app deep/strict `codesign` 通过，v1.0.40 arm64、ad-hoc、无 Team ID。当前本机 `/Applications/影序 YINGXU.app` health/database 均 ok；此前只读识别真实 SD_Card 828 项（784 照片、44 视频）。 | 本机候选可启动并扫描实卡；包仍为 ad-hoc 签名、无 Team ID、未公证，不是公开发行。 | Developer ID 签名与公证；正式 Release、下载页及另一台 Mac 安装回读。 |
| Windows 桌面 | 产品代码 head `970bb32` 的 preview run `39007205420` success；artifact `12090374866`（ZIP 27,492,898 bytes，metadata digest `sha256:62f4c0475c50d0f22738ff8dca15067291a3f0173c0d9777a44eb75dc4d05f32`）。EXE 27,790,294 bytes，PE32+ x86-64；SHA-256 `b0b7b5085fd9d0bb74bb5675b06ce11c1fd29346e38e1b74a7fb16750e278add` 与 `SHA256SUMS.txt` 一致。 | CI unsigned preview 构建和清单匹配已核实；仍无 Windows 真机安装、运行、Defender、读卡器或断盘恢复证据。 | 在真实 Windows PC 安装并逐项操作；测试 SD 卡、目标盘、恢复与升级；签名后发布正式安装包并从公开链接回读。 |
| 手机 PWA | Pocket 页面、状态、历史和拍摄备注接口及 manifest / Service Worker 已有源码；v1.0.40 在安装版真实浏览器中通过 HTTP LAN 显示离线限制、loopback 显示页面缓存就绪。 | Mac 浏览器 runtime 已核验；没有 iPhone/Android 同 Wi-Fi 实测、主屏幕安装、后台/切网/离线验收。LAN HTTP 下 Service Worker 不可用，不能把离线缓存记为已交付。 | 在 iPhone 与 Android 真机完成配对、状态、历史、备注、锁屏唤醒、网络切换、离线与撤销验收；为需离线能力的 PWA 配置受信任 HTTPS，或由原生客户端承接；明确 PWA 是否构成最终移动交付。 |
| 原生 iOS / Android | `mobile/` 已有 Expo Router Pocket 客户端和 TCP 服务；SDK 58.0.14、React Native 0.88.0、React 19.3.0、`react-native-tcp-socket` 6.4.3。当前 PR head `970bb32` 的 Pocket run `39007205403` completed/success：Pocket JS/CNG/lint/typecheck/protocol tests、iOS Simulator job `117321996805`（18m32s）、Android debug job `117321996746`（21m59s）均成功。Artifact `12092136782`（`yingxu-pocket-android-debug-5451c2af07b6fc0b48c49bc92d566e32c15fa026.zip`）大小 94,576,842 bytes，GitHub digest `sha256:b670b777a07efc6532fdbc7906b442d7f63821ca5d075fe1ec079c9771a8f1d1`；本机回读 ZIP digest 一致。内含 269,562,399-byte `app-debug.apk`，SHA-256 `adcd086a677906b54c2482fe124d4fa40f3896c959c29ee1f1124790270532a0`，包含 `arm64-v8a`、`armeabi-v7a`、`x86`、`x86_64`。APK 是 debug/universal 构建，不是商店签名包。此次成功再次验证 `c6a45d4` 的 4 GB Gradle heap 修复。 | 当前 PR head 的 Android debug 与 iOS Simulator 原生编译通过，artifact 已下载并核验；没有 iPhone/Android 真机、局域网授权或桌面 TCP 配对证据。本机无 Android SDK/adb 与完整 Xcode。 | 在真机完成安装、授权、配对、切网和重连；配置正式签名构建与商店资料，产出并检查签名 IPA/AAB、提审及上架。Expo SDK 58 默认 targetSdk 36，达到当前 Google Play 新应用 target API 门槛；未来升到 targetSdk 37 时须处理 Android 17 的 `ACCESS_LOCAL_NETWORK` 运行时权限（[Google Play target API 要求](https://support.google.com/googleplay/android-developer/answer/11926878)、[Android 局域网权限](https://developer.android.com/privacy-and-security/local-network-permission)）。 |
| 微信小程序 | `miniprogram/` 页面和 TCP 客户端已存在；桌面 TCP bridge 默认关闭，启用后监听 `18080`。本地 Node 测试现为 7 项通过，包含非法响应帧拒绝和切后台清理；小程序脚本语法与配置 JSON 解析通过。 | 微信开发者工具 CLI 实际打开项目时因占位 AppID `touristappid` 返回 code 10“不存在此 AppID”，尚未进入编译；没有真实 AppID、真机或审核证据。当前源码路线为同一局域网直连，正式数据路径仍待确认。 | 配置真实 AppID 后完成开发者工具编译预览；确认正式连接架构；iPhone/Android 微信真机验收配对、前后台、切网、过期/撤销；补隐私指引并提交审核，核对线上版本。 |
| 官网与浏览器产品 | 主仓库 `site/` 有首页、隐私页和下载页；规范 Pages 路径为 `https://yingxu-app.github.io/smart-media-backup/`。本轮首页和下载页返回 HTTP 200；此前已核实隐私页 `/privacy.html`。下载页只链接正式版 Windows v1.0.34。 | 静态官网/下载站已部署；浏览器在线备份功能范围未定义。 | 确认网页只需官网/下载还是还需浏览器内导入/备份；正式发行后通过 main 部署，检查 canonical URL、下载、校验文件及缓存刷新。在线备份若纳入范围，还需账户/数据/存储/隐私架构。 |
| 正式发布与售后回滚 | GitHub Latest Release 复核仍为 `v1.0.34`，资产仅 Windows EXE 与 `SHA256SUMS.txt`。PR #4 的 `a6de5f4` 检查快照中，PR 为 OPEN/DRAFT、merge state CLEAN；Reliability、macOS candidate、Windows preview、Pocket JS/CNG 已通过，Android debug 与 iOS Simulator 构建当时仍 pending。 | v1.0.40 macOS 候选、Windows preview 与 Pocket debug/simulator builds 都不是多平台正式发行。 | 完成 Windows/mobile 真机验收和签名；准备隐私及商店资料；发布正式 Release、更新下载页，验证新用户下载、安装、升级与回滚。 |

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

## PWA 安全上下文依据

- [MDN Secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts) 说明普通安全上下文需 HTTPS；`localhost`/loopback 是开发例外，局域网 IP 不因此自动获得例外。
- [MDN Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) 说明 Service Worker 仅在 secure context 可用。当前 Pocket 通过 `http://<桌面局域网 IP>:8080/pocket/` 配对；在未完成真实 iPhone/Android 验证前，离线缓存和主屏幕体验均保持未验收。

## 2026-10-17 配对地址修复后的当前进度

Pocket 配对地址误选 VPN 已在 PR #4 head `d223dfe` 修正：本机 `_local_ip()` 返回活动 Wi-Fi 地址 `192.168.31.172`，接口级、配对 API、桌面全套、移动端和小程序自动检查通过。新 head 的 Pocket、macOS candidate 与 Windows preview 仍待 CI 终态；因此尚不能安装新候选做真实 iPhone/Android 局域网配对。旧 head `5d17e14` 的 iOS Simulator 与 Android debug 构建仍在运行，完成后可作为该旧 head 的构建证据，不能替代新 head 检查。

下一步按顺序：读取新 head 三条 CI 终态；检查新 macOS/Windows 候选并保留可回滚安装版本；在同 Wi-Fi 手机验证 Pocket 页面、配对、状态/历史/备注、锁屏/切网恢复；对原生客户端复核 iOS 权限和 Android TCP 后台行为。Windows 实机、真实微信 AppID/开发者工具/审核、移动商店签名/账号、在线网页产品范围仍分别缺证据或配置。

## 2026-10-17 Candidate package runtime check

The macOS artifact from run `39009788643` was checksum-verified, passed `hdiutil verify` and deep/strict ad-hoc codesign checks, then ran from its read-only DMG under isolated config/port. Health/database were OK; pairing advertised the Wi-Fi IP; the Pocket page returned HTTP 200 through that address; an unpaired status API request returned 403. The candidate was stopped and unmounted; the installed v1.0.40 app stayed healthy. This verifies packaged runtime behavior on the same Mac, not a phone over Wi-Fi.

The Windows unsigned preview from run `39009837297` built successfully; its artifact ZIP and EXE manifest hashes match, and the EXE is PE32+ x86-64. Latest head `f7e5c8a` still has Reliability macOS matrix, Pocket Android/iOS native builds and macOS candidate workflow pending. Windows real-device install, phone pairing, WeChat DevTools/real AppID, formal signing and public release remain open.
