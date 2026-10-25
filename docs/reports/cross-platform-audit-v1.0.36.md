# 影序多端闭环差距审计 v1.0.36

审计日期：2026-10-16。此文记录当前工作树和远端可复核的证据，不把候选包、CI 预览或模拟测试写成商店发布、真机验收或用户接受。

## 当前状态

| 端 / 交付项 | 已有证据 | 当前结论 | 仍需通过的门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | 已安装 v1.0.36 Apple Silicon 版识别真实 SD 卡 828 个文件，隔离目录单文件转移通过 SHA-256。提交 `4e191d2` 的 macOS runner 候选 run `38855661312` 成功；DMG SHA-256 `d1123125a64739585b03ddd99ac68ebf102110066438574121c0a7a8e3487350`，挂载确认 App 1.0.36 arm64，`codesign --verify --deep --strict` 通过但为 ad-hoc。配置迁移提交 `5e076e0` 的六平台 CI 全部通过（run `38856575122`），Windows unsigned preview 构建成功（run `38856575189`）；迁移字段与 v1.0.34 完全一致 | 源码、完整测试及 Windows CI 构建已验证；尚无包含 `5e076e0` 的 macOS 候选，也未在 Windows 实机安装。Windows artifact 已生成但本轮下载读取失败 | 配置迁移的 macOS 候选构建/安装验收，Windows artifact/实机安装及外置盘拔出与中断恢复；Apple Developer 签名、公证与公开 Release |
| Windows 桌面 | 提交 `4e191d2` 的 Windows runner unsigned preview 构建成功（run `38855556445`）；EXE 为 PE32+ x86-64，27,745,821 bytes，SHA-256 `6ceaba9d011a4575035fd56a4ecd662f288bc4ad2cb7ae18f6ad83673189efbe`。当前提交在 Windows Python 3.11/3.12 测试均通过 | 当前源码可在 Windows runner 构建；仍无 Windows 真机运行证据，预览包未签名 | Windows 真实 PC 安装、Defender、读卡器、备份/转移和拔盘恢复验收；正式签名与公开发布 |
| iPhone / Android | 当前只有 Pocket 局域网网页：配对、状态、历史与拍摄备注；4 项 API/权限测试覆盖配对及访问隔离 | 移动网页能力存在；没有原生 iOS/Android 工程、安装包或商店版 | 明确原生 App / PWA 交付范围；实际 iPhone Safari 与 Android 浏览器配对测试；后台与网络切换验证；若要商店上架，补齐对应签名和商店资料 |
| Pocket 局域网访问 | `desktop/run.py` 通过 `host_override="0.0.0.0"` 监听；`restrict_lan_surface` 仅开放 Pocket 壳和配对 API，桌面工作台对非本机请求返回 403。当前已安装 v1.0.36 进程实际监听 `*:8080`，localhost `/api/health` 返回 200；macOS 防火墙开启，影序 App 不在允许入站连接列表。同机访问 `192.168.31.172:8080/pocket/` 无响应，且路由走 `lo0` | 源码监听和服务内访问隔离已核实；macOS 入站放行状态及真实手机连通性未验收。`lo0` 请求不能代替同 Wi-Fi 手机测试 | 用户在 macOS 防火墙设置中允许影序入站连接后，用 iPhone/Android 同 Wi-Fi 实测配对、状态、历史、备注；核实失败原因；确认 HTTP 下主屏幕与离线行为，并决定是否需要受信任 HTTPS |
| 官网 / 网页产品 | 旧 Pages 曾返回旧 HTML、浏览器落到 404，旧官网仓库 API 404。本轮主仓库 `site/` 含静态首页、正式版下载页、隐私页与 404；Pages workflow run `38854899713` 于 `5936511` 成功。公网浏览器以缓存校验参数打开首页、下载页、隐私页均显示新内容；下载链接指向 GitHub v1.0.34 安装包及 SHA256 文件 | GitHub Pages 静态介绍与下载站已部署，线上浏览器内容核实；普通首页路径首次打开曾命中旧 404，缓存校验后 canonical 路径和页面加载正常，需继续观察缓存传播 | 观察不同网络/无缓存访问；在线网页产品范围待用户确认 |
| 小程序 | 当前源码没有微信/其他小程序工程或发布配置；本机安装 WeChat DevTools 36.6.0。新增 [微信小程序联通方案](../MINIPROGRAM-ARCHITECTURE.md)，据官方网络约束记录 HTTPS/WSS、局域网 IP、CloudBase/微信云托管两种路线 | 尚无小程序实现、AppID、真机验收或上架证据；云端协作数据路径需用户确认 | 确认微信平台与云端最小数据范围；提供正式 AppID 并在官方控制台配置云环境；完成真机、隐私审核、提交和线上版本验收 |
| 公开发行版 | GitHub 最新 Release 仍为 v1.0.34；v1.0.36 macOS CI DMG 与 Windows CI EXE 均为候选/预览，前者 ad-hoc、后者未签名；最新版源码 `4e191d2` | v1.0.36 尚未作为正式 Release 发布；未完成 Apple 公证或 Windows 真机验收 | 完成 macOS Developer ID 签名/公证、Windows 真机验收、版本安装升级和用户下载入口检查后再发布；保留旧版回滚 |

## 当前主机的构建能力

- 已验证本机及 GitHub macOS runner 可构建 Apple Silicon macOS App/DMG；runner artifact run `38854341034` 已下载、挂载、校验版本/架构/签名并验证 DMG checksum。候选仍 ad-hoc，未公证。
- `xcode-select -p` 指向 Command Line Tools；`xcodebuild -version` 报告需要完整 Xcode，当前没有可用 Xcode 工程构建环境。
- 本机没有 Android SDK / `adb` / Gradle；`java` 命令提示找不到 Java Runtime。
- Windows PyInstaller 规格只能在 Windows 环境构建；提交 `4e191d2` 的 GitHub Windows runner 构建已成功，产物已下载检查为 PE32+ x86-64。当前主机仍无 Windows 设备，无法以此替代安装与运行验收。
- 已安装 WeChat DevTools 36.6.0；当前源码目录没有小程序项目配置或 `app.json`，真实 AppID 与账号发布权限仍需核实。

## 版本与备份证据

- macOS 候选、安装与扫描验收：[v1.0.36.md](../releases/v1.0.36.md)。
- 本轮替换前的 v1.0.35 安装包副本：`/tmp/yingxu-installed-1.0.35-backup-2026-10-16/影序 YINGXU.app`。
- 最新源码 `main` HEAD `4e191d29a1cbcc73a8b4781f3a5b34f98ac49aa4` 已推送；完整工作流 run `38855556416` 的 macOS、Windows、Ubuntu × Python 3.11/3.12 六个任务全部通过，Windows preview run `38855556445` 与 macOS candidate run `38855661312` 均成功。两个最新候选包均已下载并验证格式/校验；尚无 Windows 真机、Apple 公证或公开 v1.0.36 Release。

## 需要用户确定的范围

1. 小程序方案：优先按微信小程序设计；是否启用可选云托管中继、仅同步状态/历史摘要/拍摄备注仍待确认。
2. 网页目标：官方介绍与下载页、在线网页产品，或两者都做。

在选择到达前，继续推进桌面候选和已有 Pocket 的可验证质量；不把未选择的平台宣称为已交付。
