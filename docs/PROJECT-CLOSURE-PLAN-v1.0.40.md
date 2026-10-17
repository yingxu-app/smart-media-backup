# 影序全端闭环计划 v1.0.40

核对日期：2026-10-17。此计划把“功能完成、平台验证、部署、公开发行”拆开记录；CI、模拟环境或候选包不能代替实机和线上验收。

## 当前交付面与权威证据

| 交付面 | 当前实现 / 已有证据 | 当前状态 | 闭环门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | v1.0.40 arm64 DMG run `38922352506`；SHA-256 `9ea1047e284cdae75f5c8520b347f42065f174ae50268496e77753e12f98d546`。本机从 `/Applications/影序 YINGXU.app` 启动并识别真实 SD_Card 828 项（784 照片、44 视频）；PR head `04ce9d1` 的候选构建 run `38998932403` 成功。 | 本机候选安装、版本 API 与实卡扫描通过；ad-hoc 签名、无 Team ID、未公证，不是公开发行。 | Developer ID 签名与公证；正式 Release、下载页及另一台 Mac 安装回读。 |
| Windows 桌面 | 最新 PR head `f80408f` 的 Windows preview run `39004002505` success；artifact `12090117584` (`YINGXU-Windows-v1.0.40-unsigned-preview`) 已下载。ZIP 内 EXE 27,788,887 bytes，PE machine `0x8664`（x64）；SHA-256 `cf67ea1a097c7b5d2fcb57828144cb1763f4d4b032aa7fcda86b76b946e8dfd8` 与包内 `SHA256SUMS.txt` 一致。 | CI unsigned preview 构建和清单匹配已核实；仍无 Windows 真机安装、运行、Defender、读卡器或断盘恢复证据。 | 在真实 Windows PC 安装并逐项操作；测试 SD 卡、目标盘、恢复与升级；签名后发布正式安装包并从公开链接回读。 |
| 手机 PWA | Pocket 页面、状态、历史和拍摄备注接口及 manifest / Service Worker 已有源码；v1.0.40 在安装版真实浏览器中通过 HTTP LAN 显示离线限制、loopback 显示页面缓存就绪。 | Mac 浏览器 runtime 已核验；没有 iPhone/Android 同 Wi-Fi 实测、主屏幕安装、后台/切网/离线验收。LAN HTTP 下 Service Worker 不可用，不能把离线缓存记为已交付。 | 在 iPhone 与 Android 真机完成配对、状态、历史、备注、锁屏唤醒、网络切换、离线与撤销验收；为需离线能力的 PWA 配置受信任 HTTPS，或由原生客户端承接；明确 PWA 是否构成最终移动交付。 |
| 原生 iOS / Android | `mobile/` 已有 Expo Router Pocket 客户端和 TCP 服务；SDK 58.0.14、React Native 0.88.0、React 19.3.0、`react-native-tcp-socket` 6.4.3。Pocket workflow run `39001877447` 对 PR head `bb4cdb5` 的 JS/CNG job、iOS Simulator 原生编译和 Android debug APK 构建均 success；iOS job `117306339650` 用时 18m6s，Android job `117306339938` 用时 22m26s。Artifact `12089997551` 的 universal debug APK 为 269,562,283 bytes，SHA-256 `e92dbb426b647b9c1d77ddc41e1e64aa9d6edf0f5aa3485716bc2cc9572329b5`，包含 arm64-v8a、armeabi-v7a、x86、x86_64 四种 ABI。 | 首次 cloud native builds 通过，New Architecture 的编译兼容风险已降低；APK 是 unsigned/debug CI 产物，不是商店包。没有 iPhone/Android 真机安装、局域网授权或桌面 TCP 配对证据；本机仍无完整 Xcode 与 Android SDK/adb。 | 在真机完成安装、授权、配对、切网和重连；配置正式签名构建与商店资料，产出并检查签名 IPA/AAB、提审及上架。Expo SDK 58 默认 targetSdk 36，达到当前 Google Play 新应用 target API 门槛；未来升到 targetSdk 37 时须处理 Android 17 的 `ACCESS_LOCAL_NETWORK` 运行时权限（[Google Play target API 要求](https://support.google.com/googleplay/android-developer/answer/11926878)、[Android 局域网权限](https://developer.android.com/privacy-and-security/local-network-permission)）。 |
| 微信小程序 | `miniprogram/` 页面和 TCP 客户端已存在；桌面 TCP bridge 默认关闭，启用后监听 `18080`。本地 Node 测试现为 7 项通过，包含非法响应帧拒绝和切后台清理；小程序脚本语法与配置 JSON 解析通过。 | 微信开发者工具 CLI 实际打开项目时因占位 AppID `touristappid` 返回 code 10“不存在此 AppID”，尚未进入编译；没有真实 AppID、真机或审核证据。当前源码路线为同一局域网直连，正式数据路径仍待确认。 | 配置真实 AppID 后完成开发者工具编译预览；确认正式连接架构；iPhone/Android 微信真机验收配对、前后台、切网、过期/撤销；补隐私指引并提交审核，核对线上版本。 |
| 官网与浏览器产品 | 主仓库 `site/` 有首页、隐私页和下载页；规范 Pages 路径为 `https://yingxu-app.github.io/smart-media-backup/`。本轮首页和下载页返回 HTTP 200；此前已核实隐私页 `/privacy.html`。下载页只链接正式版 Windows v1.0.34。 | 静态官网/下载站已部署；浏览器在线备份功能范围未定义。 | 确认网页只需官网/下载还是还需浏览器内导入/备份；正式发行后通过 main 部署，检查 canonical URL、下载、校验文件及缓存刷新。在线备份若纳入范围，还需账户/数据/存储/隐私架构。 |
| 正式发布与售后回滚 | GitHub Latest Release 正式版仍为 `v1.0.34`，资产仅 Windows EXE 与 `SHA256SUMS.txt`。PR #4 当前 OPEN/DRAFT，head `3dd71c8`；Pocket workflow run `39003760346` 的 JS/CNG/check job success，Android debug 与 iOS Simulator 原生 job 查询时仍在运行。 | v1.0.40 macOS 候选、Windows preview 与 Pocket debug/simulator builds 都不是多平台正式发行。 | 完成 Windows/mobile 真机验收和签名；准备隐私及商店资料；发布正式 Release、更新下载页，验证新用户下载、安装、升级与回滚。 |

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
