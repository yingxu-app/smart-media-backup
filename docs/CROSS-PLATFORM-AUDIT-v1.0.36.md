# 影序多端闭环差距审计 v1.0.36

审计日期：2026-10-16。此文记录当前工作树和远端可复核的证据，不把候选包、CI 预览或模拟测试写成商店发布、真机验收或用户接受。

## 当前状态

| 端 / 交付项 | 已有证据 | 当前结论 | 仍需通过的门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | v1.0.36 Apple Silicon DMG 已构建；`codesign --verify --deep --strict`、`hdiutil verify` 通过；已安装到 `/Applications/影序 YINGXU.app`；原生首页识别真实 SD 卡 828 个文件；隔离目录单文件转移通过 SHA-256 | 本地候选运行闭环已验收 | Windows/macOS 多版本配置迁移、外置盘拔出与中断恢复；Apple Developer 签名、公证与公开 Release |
| Windows 桌面 | `2941a30` 在 GitHub Actions Windows runner 构建成功；unsigned preview EXE 为 PE32+ x86-64，27,744,013 bytes，SHA-256 `1765a491845d0a94ec02ab395e35ef6a124a8c99c9863f33c70bc08e6f6abbcb`；同提交 Windows Python 3.11/3.12 测试通过 | 当前源码可在 Windows runner 构建；仍无 Windows 真机运行证据，预览包未签名 | Windows 真实 PC 安装、Defender、读卡器、备份/转移和拔盘恢复验收；正式签名与公开发布 |
| iPhone / Android | 当前只有 Pocket 局域网网页：配对、状态、历史与拍摄备注；4 项 API/权限测试覆盖配对及访问隔离 | 移动网页能力存在；没有原生 iOS/Android 工程、安装包或商店版 | 明确原生 App / PWA 交付范围；实际 iPhone Safari 与 Android 浏览器配对测试；后台与网络切换验证；若要商店上架，补齐对应签名和商店资料 |
| Pocket 安全上下文 | 桌面生成的配对地址为 `http://<局域网地址>:<端口>/pocket/`；页面尝试注册 Service Worker，失败会静默忽略 | HTTP 页面与配对接口已有源码；离线缓存、安装体验未在真实手机验证 | 真实 iPhone/Android 在同 Wi-Fi 验收；确认当前 HTTP 环境下的主屏幕与离线行为，并决定是否需要受信任 HTTPS |
| 官网 / 网页产品 | `https://yingxu-app.github.io/smart-media-backup/` 当前返回 200；现场 HTML 的 macOS 下载仍写 v1.0.12 并指向 Vercel 地址，Windows 链接指向旧账号 v1.0.0；`https://yingxu-app.github.io/` 返回 404，项目路径 `/download` 也返回 404。旧官网源码副本在 `01_当前源码/yingxu-app.github.io`，工作树干净、HEAD `571816e`，本地文案仍以 v1.0.31/1.0.33 为主；对应 `yingxu-app/yingxu-app.github.io` 仓库 API 返回 404 | 项目子路径上仍有公开旧站，但下载入口与版本信息不可用或过时；“官网+下载页”与“在线网页产品”范围待定 | 修复网站入口、路由、版本说明和下载资产；确定是否同时提供在线网页产品；部署后从新用户入口验收 |
| 小程序 | 当前源码没有微信/其他小程序工程或发布配置；本机安装 WeChat DevTools 36.6.0 | 尚无小程序实现、真机验收或上架证据 | 按用户确认的平台推进；完成登录/配对、隐私审核、真机、审核和发布验收 |
| 公开发行版 | GitHub 最新 Release 仍为 v1.0.34；v1.0.36 macOS DMG SHA-256 为 `cff0d1ba5b7cad595f2b82337c9229bc30766d1cd4f1214cdbd8f171af7ce432`；源代码已推送到 `main` 的 `2941a30` | macOS 1.0.36 未公开且未公证；Windows CI 包只是 unsigned preview | 完成 macOS 签名/公证、Windows 真机验收、版本安装升级和用户下载入口检查后再发布；保留旧版回滚 |

## 当前主机的构建能力

- 已验证可构建 Apple Silicon macOS App/DMG。
- `xcode-select -p` 指向 Command Line Tools；`xcodebuild -version` 报告需要完整 Xcode，当前没有可用 Xcode 工程构建环境。
- 本机没有 Android SDK / `adb` / Gradle；`java` 命令提示找不到 Java Runtime。
- Windows PyInstaller 规格只能在 Windows 环境构建；提交 `2941a30` 的 GitHub Windows runner 构建已成功，产物已下载检查为 PE32+ x86-64。当前主机仍无 Windows 设备，无法以此替代安装与运行验收。
- 已安装 WeChat DevTools 36.6.0；当前源码目录没有小程序项目配置或 `app.json`，真实 AppID 与账号发布权限仍需核实。

## 版本与备份证据

- macOS 候选、安装与扫描验收：[RELEASE-v1.0.36.md](RELEASE-v1.0.36.md)。
- 本轮替换前的 v1.0.35 安装包副本：`/tmp/yingxu-installed-1.0.35-backup-2026-10-16/影序 YINGXU.app`。
- 当前源码分支 `main` HEAD 为 `2941a30cc1a1b24e4e42467e090c4a2b369df8e7`；此前转移功能和 v1.0.36 相关代码已提交并推送。测试工作流在 macOS、Windows、Ubuntu × Python 3.11/3.12 的 6 个矩阵任务均通过，Windows unsigned preview 构建通过。

## 需要用户确定的范围

1. 小程序目标：微信小程序、仅完善 Pocket PWA，或多平台小程序。
2. 网页目标：官方介绍与下载页、在线网页产品，或两者都做。

在选择到达前，继续推进桌面候选和已有 Pocket 的可验证质量；不把未选择的平台宣称为已交付。
