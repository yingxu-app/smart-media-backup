# 影序多端闭环差距审计 v1.0.36

审计日期：2026-10-16。此文记录当前工作树和远端可复核的证据，不把候选包、CI 预览或模拟测试写成商店发布、真机验收或用户接受。

## 当前状态

| 端 / 交付项 | 已有证据 | 当前结论 | 仍需通过的门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | v1.0.36 Apple Silicon DMG 已构建；`codesign --verify --deep --strict`、`hdiutil verify` 通过；已安装到 `/Applications/影序 YINGXU.app`；原生首页识别真实 SD 卡 828 个文件；隔离目录单文件转移通过 SHA-256 | 本地候选运行闭环已验收 | Windows/macOS 多版本配置迁移、外置盘拔出与中断恢复；Apple Developer 签名、公证与公开 Release |
| Windows 桌面 | 有 `desktop/smb-win.spec`、Windows CI 测试矩阵和 unsigned preview 工作流；远端最新公开 Release 为 v1.0.34，仅含 `YINGXU-Windows-v1.0.34.exe` 与校验文件 | 有构建入口，当前 v1.0.36 未在 Windows runner 构建，也未做 Windows 设备验收 | 用 v1.0.36 源码触发 Windows 构建；安装、Defender、读卡器、备份/转移和拔盘恢复真机验收；正式签名与发布 |
| iPhone / Android | 当前只有 Pocket 局域网网页：配对、状态、历史与拍摄备注；4 项 API/权限测试覆盖配对及访问隔离 | 移动网页能力存在；没有原生 iOS/Android 工程、安装包或商店版 | 明确原生 App / PWA 交付范围；实际 iPhone Safari 与 Android 浏览器配对测试；后台与网络切换验证；若要商店上架，补齐对应签名和商店资料 |
| Pocket 安全上下文 | 桌面生成的配对地址为 `http://<局域网地址>:<端口>/pocket/`；页面尝试注册 Service Worker，失败会静默忽略 | HTTP 页面与配对接口已有源码；离线缓存、安装体验未在真实手机验证 | 真实 iPhone/Android 在同 Wi-Fi 验收；确认当前 HTTP 环境下的主屏幕与离线行为，并决定是否需要受信任 HTTPS |
| 官网 / 网页产品 | 本地官网副本在 `01_当前源码/yingxu-app.github.io`，工作树干净、HEAD `571816e`；页面文案仍引用 v1.0.31；该同名 GitHub 仓库 API 返回 404 | 有静态网站副本，没有可核实的当前公开部署；“官网+下载页”与“在线网页产品”范围待定 | 选择部署形态；恢复/迁移可写入的托管仓库；更新版本、下载资产、隐私和多语言页面；部署后从新用户入口验收 |
| 小程序 | 当前源码没有微信/其他小程序工程或发布配置 | 未开始实现或上架 | 确认微信小程序、仅完善 PWA 或多平台；完成登录/配对、隐私审核、真机、审核和发布验收 |
| 公开发行版 | GitHub 最新 Release 为 v1.0.34；v1.0.36 本地 DMG SHA-256 为 `cff0d1ba5b7cad595f2b82337c9229bc30766d1cd4f1214cdbd8f171af7ce432` | macOS 1.0.36 未公开；代码仍在本地未提交；未公证 | v1.0.36 多平台构建与检查通过后，发布说明、校验和、签名/公证、下载与升级验收；部署前进行最终审阅 |

## 当前主机的构建能力

- 已验证可构建 Apple Silicon macOS App/DMG。
- `xcode-select -p` 指向 Command Line Tools；`xcodebuild -version` 报告需要完整 Xcode，当前没有可用 Xcode 工程构建环境。
- 本机没有 Android SDK / `adb` / Gradle；`java` 命令提示找不到 Java Runtime。
- Windows PyInstaller 规格只能在 Windows 环境构建；当前仓库已有 GitHub Windows runner 工作流，但这轮没有把未提交代码上传触发构建。

## 版本与备份证据

- macOS 候选、安装与扫描验收：[RELEASE-v1.0.36.md](RELEASE-v1.0.36.md)。
- 本轮替换前的 v1.0.35 安装包副本：`/tmp/yingxu-installed-1.0.35-backup-2026-10-16/影序 YINGXU.app`。
- 当前源码分支仍在 `main`，基线 HEAD `7856289d61c5d8c93fa1c909bc1d93827b2f7a63`；v1.0.36 及转移功能相关文件保留为未提交本地改动。

## 需要用户确定的范围

1. 小程序目标：微信小程序、仅完善 Pocket PWA，或多平台小程序。
2. 网页目标：官方介绍与下载页、在线网页产品，或两者都做。

在选择到达前，继续推进桌面候选和已有 Pocket 的可验证质量；不把未选择的平台宣称为已交付。
