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
