# 影序全端闭环计划 v1.0.40

核对日期：2026-10-17。此计划把“功能完成、平台验证、部署、公开发行”拆开记录；CI、模拟环境或候选包不能代替实机和线上验收。

## 当前交付面与权威证据

| 交付面 | 当前实现 / 已有证据 | 当前状态 | 闭环门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | v1.0.40 arm64 DMG run `38922352506`；SHA-256 `9ea1047e284cdae75f5c8520b347f42065f174ae50268496e77753e12f98d546`。本机从 `/Applications/影序 YINGXU.app` 启动并识别真实 SD_Card 828 项（784 照片、44 视频）；PR head `04ce9d1` 的候选构建 run `38998932403` 成功。 | 本机候选安装、版本 API 与实卡扫描通过；ad-hoc 签名、无 Team ID、未公证，不是公开发行。 | Developer ID 签名与公证；正式 Release、下载页及另一台 Mac 安装回读。 |
| Windows 桌面 | Windows preview run `38922372204` 成功，x64 PE 检查、UTF-8 SHA256 manifest 回读及 artifact 上传通过。v1.0.40 artifact SHA-256 `72165f83f39263e5617e9ba76314e50e5d89796269bb214f6add64f35bdc92be`；PR head `04ce9d1` 的 preview run `38998932368` 成功。 | CI 构建产物为 unsigned preview；没有 Windows 实机安装、运行、Defender、读卡器或断盘恢复证据。 | 在真实 Windows PC 安装并逐项操作；测试 SD 卡、目标盘、恢复与升级；签名后发布正式安装包并从公开链接回读。 |
| 手机 PWA | Pocket 页面、状态、历史和拍摄备注接口及 manifest / Service Worker 已有源码；v1.0.40 在安装版真实浏览器中通过 HTTP LAN 显示离线限制、loopback 显示页面缓存就绪。 | Mac 浏览器 runtime 已核验；没有 iPhone/Android 同 Wi-Fi 实测、主屏幕安装、后台/切网/离线验收。LAN HTTP 下 Service Worker 不可用，不能把离线缓存记为已交付。 | 在 iPhone 与 Android 真机完成配对、状态、历史、备注、锁屏唤醒、网络切换、离线与撤销验收；为需离线能力的 PWA 配置受信任 HTTPS，或由原生客户端承接；明确 PWA 是否构成最终移动交付。 |
| 原生 iOS / Android | `mobile/` 已有 Expo Router Pocket 客户端和 TCP 服务；SDK 58.0.14、React Native 0.88.0、React 19.3.0、`react-native-tcp-socket` 6.4.3。TypeScript、lint、协议测试及 iOS/Android JS bundle 均通过；CNG 预构建成功。新增 `.github/workflows/mobile.yml`，本机复核 workflow 的冻结安装、兼容检查、lint、typecheck、5 项单测、prebuild 和两端 bundle export 全通过；远端 Action 尚未触发。尚未生成安装包。当前机器缺完整 Xcode、CocoaPods 和 Android SDK/adb。 | 源码与 JS bundle 通过本机检查；native module 标记为 New Architecture 未测试，真机兼容性和局域网连接未验收。 | 核对 GitHub PR workflow 真实运行结果；完成 iOS/Android 原生构建与双端真机配对/断线恢复；配置签名、隐私资料和商店提审。Expo SDK 58 默认 targetSdk 36，达到当前 Google Play 新应用 target API 门槛；未来升到 targetSdk 37 时须处理 Android 17 的 `ACCESS_LOCAL_NETWORK` 运行时权限（[Google Play target API 要求](https://support.google.com/googleplay/android-developer/answer/11926878)、[Android 局域网权限](https://developer.android.com/privacy-and-security/local-network-permission)）。 |
| 微信小程序 | `miniprogram/` 页面和 TCP 客户端已存在；桌面 TCP bridge 默认关闭，用户启用后监听 `18080`。本轮 Node 测试 5 项通过；占位 `touristappid` 尚不能作为真实开发者工具/AppID 验收。 | 原型源码通过测试；没有真实 AppID、开发者工具运行态、真机或审核证据。当前代码路线为同一局域网直连，但正式数据路径待确认。 | 确认正式连接架构；使用真实 AppID 编译预览；iPhone/Android 微信真机测配对、前后台、切网、过期/撤销；补隐私指引并提交审核，核对线上版本。 |
| 官网与浏览器产品 | 主仓库 `site/` 有首页、隐私页和下载页；规范 Pages 路径为 `https://yingxu-app.github.io/smart-media-backup/`。本轮首页和下载页返回 HTTP 200；此前已核实隐私页 `/privacy.html`。下载页只链接正式版 Windows v1.0.34。 | 静态官网/下载站已部署；浏览器在线备份功能范围未定义。 | 确认网页只需官网/下载还是还需浏览器内导入/备份；正式发行后通过 main 部署，检查 canonical URL、下载、校验文件及缓存刷新。在线备份若纳入范围，还需账户/数据/存储/隐私架构。 |
| 正式发布与售后回滚 | 本轮 `gh release list` 确认 latest 为非草稿、非预发行 `v1.0.34`（2026-09-12）；PR #4 仍 OPEN/DRAFT，head `04ce9d1`，当前列出的 CI 检查通过。 | v1.0.40 macOS 本机候选和 Windows unsigned preview 均未公开发布，不可称作全平台正式版。 | 所有要求平台通过各自发行门禁；同步版本说明、隐私与下载页；验证升级/回滚与安装后路径；记录每个平台真实上线版本和链接。 |

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
