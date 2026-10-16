# v1.0.40 本机开发候选验收记录

日期：2026-10-16。公开 GitHub Release 仍为 v1.0.34；v1.0.40 是本地与 CI 候选，未公开发行。

## 改动

- Pocket 页面根据浏览器安全上下文显示 Service Worker 与离线页面缓存状态。局域网 HTTP 下明确说明离线缓存不可用；安全上下文下尝试注册页面缓存。实时状态、历史与拍摄信息仍需要桌面端在线。
- 桌面应用版本、安装元信息、设置页、控制台和 changelog 统一为 1.0.40。

## 自动化与候选包

- Reliability runs `38922348166` 与 `38922337611` 对提交 `ac83bdaca436652a009d1cfe3b21950582526ad3` 均成功；macOS / Ubuntu 24.04 / Windows × Python 3.11 / 3.12 六矩阵全部通过。
- macOS candidate run `38922352506` 成功。DMG 大小 22,254,798 bytes，SHA-256 `9ea1047e284cdae75f5c8520b347f42065f174ae50268496e77753e12f98d546`；随包 SHA256SUMS、`hdiutil verify` 通过。只读挂载后两个 Info.plist 版本字段均为 1.0.40，主程序为 arm64；`codesign --verify --deep --strict` 通过。签名为 ad-hoc、无 Team ID、未公证。
- Windows preview run `38922372204` 成功。下载 artifact 是 PE32+ x86-64 GUI，SHA-256 `72165f83f39263e5617e9ba76314e50e5d89796269bb214f6add64f35bdc92be`，与 SHA256SUMS 匹配。它是 unsigned CI preview，未在 Windows 真机安装或运行。

## 安装与运行

- 安装前完整备份 v1.0.39 到 `/tmp/yingxu-installed-v1.0.39-backup-before-1.0.40-2026-10-16/`，附有恢复说明；候选 v1.0.40 已安装到 `/Applications/影序 YINGXU.app` 并启动。
- `/api/status` 返回 `version=1.0.40`。实际 SD_Card 扫描出 828 项：784 张照片、44 个视频，共 29,545,956,809 字节。首页、`/transfer`、`/history`、`/settings`、`/pocket/`、manifest 和 Service Worker 路由均返回 HTTP 200。此次只读扫描没有向存储卡写入或删除文件。
- `/api/pocket/tcp-settings` 返回 `enabled=false, running=false`，符合默认关闭。
- 实际安装包浏览器 smoke test：访问 `http://192.168.31.172:8080/pocket/` 显示局域网 HTTP 下离线缓存不可用；访问 `http://127.0.0.1:8080/pocket/` 显示页面缓存就绪。后者使用本机浏览器 loopback，不是 iPhone/Android 真机或同 Wi-Fi 验收；没有执行手机配对和网络切换。
- 本机完整 Python 测试 76 项通过，2 项为 Windows 条件跳过；微信小程序 Node 测试 4 项通过。新代码浏览器状态提示的两种安全上下文也已用真实浏览器分别验证。

## 仍未完成

- Windows 真机安装、读卡器、SD 卡转移、拔盘和中断恢复；正式签名与 Windows 公开发行。
- macOS Developer ID 签名、公证、公开 macOS Release 和下载端验收。
- iPhone / Android 同 Wi-Fi、主屏幕入口、后台/锁屏、离线/切网与 Pocket 配对验收；原生 iOS/Android 工程及商店包尚不存在。
- 微信小程序真实 AppID、正式连接路线、开发者工具预览、真机、隐私审核和上架。当前路线待用户决定。
- 网页产品范围（官网/下载页或浏览器在线备份）待用户决定。

## Windows preview 后续复核（2026-10-16）

- 提交 `977058bc1b05687c5ca9ae3864ab7755379417ce` 修复 Windows 默认代码页下的报告读取和 AI 诊断输出；本机完整 Python 测试 78 项通过、2 项 Windows 条件跳过，小程序 Node 测试 4 项通过。
- Windows preview run `38926884128` 的可靠性套件、版本解析、PyInstaller、x64 PE 校验、SHA-256 清单读回和 artifact 上传全部成功。
- 实际下载 artifact `12057256711` 后再次独立检查：内含 `影序 YINGXU.exe`（27,759,001 bytes）和 `SHA256SUMS.txt`；PE machine 为 `0x8664`（x64）；EXE SHA-256 `72e9ec1f55b3378e466bdaa273cbe59ed9f1b7422a23a0fa709dcdd0c42057b8` 与清单逐字匹配。artifact ZIP SHA-256 `30e3d47e67ebe25767a268897e38705bd5c33cf57d7e9ccfeab0703897cbd566`。
- 这是可下载、可校验的 unsigned preview，仍未在 Windows 真机安装或运行，也未作为正式 Release 发布。

## 2026-10-17 最新分支候选复核（ff4d177）

- 当前候选代码分支 `codex/v1.0.39-miniprogram-lan-tcp` 的 HEAD 为 `ff4d17744f08b4ed873f3eddac91ec5cd85201b3`，工作区干净。Python 测试通过 79 项、Windows 条件跳过 2 项；小程序 Node 测试 5 项通过，JS/JSON 静态解析与 `git diff --check` 通过。
- 最新 Reliability run `38932408213` 六矩阵成功；Windows preview run `38932408167` 成功。其 artifact `12060016185` 下载后核实为 x64 PE EXE，27,759,055 bytes，SHA-256 `d5b252b8b7a1004d5a0ad917cececf2a6ee777ba202d8a9434f942bdd191f9af`，包内清单校验匹配。artifact 为 unsigned preview，尚无 Windows 实机安装证据。
- 当前安装版仍是 `/Applications/影序 YINGXU.app` v1.0.40、arm64、ad-hoc、无 Team ID；主程序 SHA-256 `8235e90d0b168bf0113dcb6d2c26e38b9427b80300bf61b7cb234ef8b0ea864c`。本次本机 API 状态为 idle，桌面主页面、转移、历史、设置、Pocket、Pocket manifest/service worker 路由和状态 API 均返回 200；没有插卡，本次不代表真实媒体读写验收。
- 公开 GitHub Release 仍为 v1.0.34（Windows EXE 和校验文件）。v1.0.40 未公开发行；PR #4 仍为 OPEN/DRAFT。签名、公证、Windows 实机、移动设备、微信 AppID/编译/审核和商店发布仍未完成。
