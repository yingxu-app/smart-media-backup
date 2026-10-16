# v1.0.39 小程序局域网直连原型记录

状态：独立开发分支中的未安装、未发布候选；桌面 TCP 服务默认关闭。正式连接路线、真实 AppID、微信预览和 iPhone/Android 真机验收仍未完成。

## 改动

- 新增 `smb/pocket_tcp.py`：默认不监听；启用后在 `18080` 提供 newline-framed TCP 协议，只开放配对、状态、历史摘要、拍摄备注和断开。
- 新增设置接口 `/api/pocket/tcp-settings` 与偏好设置开关；启用状态写入配置文件，应用重启时按配置启动。
- 设置接口只允许本机调用并要求严格布尔值；若配置保持启用但启动时监听器未运行，设置页会显示故障状态而不会误报“已关闭”。
- 新增 `miniprogram/`：私有 IPv4 输入、一次性配对码、状态/历史摘要、拍摄备注编辑；单个长连接复用，不周期性新建 socket。
- 小程序 TCP 客户端限制每一条返回帧的长度，遇到超长或无效协议帧立即断开并拒绝未完成请求。
- 新增版本号 `1.0.39` 和本地候选说明。

## 安全边界

- 新增 `pocket_tcp_enabled` 默认为 `false`；只有用户在桌面设置里明确打开后才绑定 `0.0.0.0:18080`。
- 请求严格限制在 allowlist；不接受备份/删除/文件读取命令；状态响应过滤绝对路径、当前文件、错误详情和清理能力；历史仅返回目标目录名。
- 每个连接最大请求 8 KiB、响应 256 KiB，最多 8 个并发 TCP 客户端；每个来源在 10 分钟窗口内最多尝试 5 次错误配对。
- 原型 TCP 没有 TLS，仅限可信局域网；不得在路由器上做公网端口转发。

## 已验证

- 完整 Python 测试：76 项运行、74 项通过、2 项平台条件跳过；`compileall` 与 `git diff --check` 通过。
- `tests/test_pocket_tcp.py` 5 项通过；新增 4 项 Pocket API 测试覆盖 TCP 设置的 loopback 限制、严格输入、持久化、真实监听器启停与状态。
- 小程序 Node 测试 4 项通过，覆盖 UTF-8 往返、错误响应、超长帧和无效协议帧；三份 JS 文件语法检查及全部 JSON 配置解析通过。
- GitHub Reliability run `38897911009` 在 macOS/Ubuntu/Windows × Python 3.11/3.12 六矩阵全部成功。
- Windows preview run `38897916810` 成功；下载回读的 unsigned x86-64 PE32+ EXE 为 27,757,920 字节，SHA-256 `fc7b67573af5e2a4bab51fa0274e85ed981da791401591dd01bee93dca14fd39`。未在 Windows 真机安装或运行。
- macOS Apple Silicon 隔离构建成功，生成 47 MB `.app`；Info.plist 两个版本字段均为 1.0.39，PyInstaller 归档中含 `smb.server`、`smb.pocket_tcp`、`smb.transfer`，`codesign --verify --deep --strict` 通过。签名为 ad-hoc、无 Team ID；本机候选未安装或运行。
- macOS candidate run `38898226636` 成功；DMG SHA-256 `df39b52afd67e7f6503e5870f94cb8506ab27712872bb2461ef3cf08163c95e3`，`hdiutil verify`、随包 SHA256SUMS、只读挂载和 App `codesign --verify --deep --strict` 均通过，Info.plist 两字段为 1.0.39。没有安装候选 App。
- GitHub Pages 项目首页与下载页均 HTTP 200，仍显示正式版 Windows v1.0.34；本候选没有发布到公开下载页或 GitHub Release。
- 微信开发者工具 36.6.0 CLI 启动正常，但打开占位 AppID 项目失败，返回 `AppID 不存在 (code 10)`；没有小程序运行态或真机证据。

## 构建过程问题

- macOS run `38898040431` 的 App 构建和 ad-hoc 签名通过，但 DMG 步骤失败：手动 dispatch 的 `GITHUB_REF_NAME` 是带斜杠的功能分支名，被直接用于输出文件路径。工作流现从 `smb.__version__` 生成安全文件名；修正后的 run `38898226636` 成功完成 DMG 与 artifact 上传。

## 待验收

- Windows 真机安装/操作；macOS 候选首次启动和 Pocket 端口启停；Apple Developer ID 签名与公证。
- 微信开发者工具使用真实 AppID 编译预览，并在 iPhone、Android 连接本地桌面服务。
- 桌面设置开关实际绑定/释放端口、端口占用恢复、防火墙提示、会话过期/撤销和网络切换。
- macOS LaunchServices 首次读卡停滞问题仍未解决；此原型不能视作该问题的修复或正式发布。

## 本机安装与真实存储卡验收（2026-10-16，后续补充）

本节更新上方“未安装/未运行”及“LaunchServices 停滞仍未解决”的历史状态。之前的 1.0.38 LaunchServices 问题不能再描述为 1.0.39 未验证；本节只覆盖当前这台 Apple Silicon Mac 与当前插入的 SD 卡。

- 从 macOS candidate run `38898226636` 下载 DMG，SHA-256 为 `df39b52afd67e7f6503e5870f94cb8506ab27712872bb2461ef3cf08163c95e3`；`hdiutil verify`、随包 SHA256SUMS 与只读挂载检查通过。
- 安装前将 v1.0.38 App 完整备份到 `/tmp/yingxu-app-1.0.38-backup-2026-10-16/`，附有恢复说明；随后从 `/Applications/影序 YINGXU.app` 启动 v1.0.39。
- `/api/status` 返回版本 `1.0.39`；原生首页显示 SD_Card 已扫描完成。`/api/sources` 实际读到 828 个文件、784 张照片、44 个视频，共 29,545,956,809 字节。首页、`/transfer`、`/history`、`/settings`、`/pocket/` 均返回 HTTP 200。
- 活动进程路径为 `/Applications/影序 YINGXU.app/Contents/MacOS/影序 YINGXU`；应用监听 `*:8080`。`/api/pocket/tcp-settings` 返回 `enabled=false, running=false`，TCP 端口 18080 未监听，符合默认关闭。
- 本次没有向 SD 卡写入、备份或转移文件；Windows、其他 Mac、手机与小程序仍未验收。应用仍是 ad-hoc 签名、无 Team ID，不能称为公证或公开发行版本。

## 转移流程运行时验收补充（2026-10-16）

- 通过已安装 v1.0.39 对真实 SD 卡只读扫描，转移页扫描器得到 828 项（784 张照片、44 个视频）。对 6 张照片只运行废片/相似度分析，结果为 5 项“正常”、1 项“过暗”、0 项相似；目标目录为空，因此这次分析不构成真实归档库重复率验收。未向 SD 卡写入或删除。
- 随后从 SD 卡读取两张小于 8 MiB 且 SHA-256 不同的照片，只复制到 `/tmp` 隔离测试源目录；在隔离目标目录预置其中一张的完全相同副本。实际运行时先识别 1 项精确重复，再执行转移：API 最终状态 `done`，`total=2, done=2, copied=1, duplicates=1, failed=0`。复制结果 SHA-256 与两份原始样本相符，临时来源文件均按转移规则移除；整个 `/tmp` 测试目录随后删除。
- 以上验证覆盖应用打包运行时的扫描、重复分析、SHA-256 校验复制和重复项处理；真实 SD 卡只读，尚未在用户的实际归档目标上转移任何文件。

## Pocket 手机协作页与 PWA 资源检查（2026-10-16）

- 已安装 v1.0.39 运行时的 `/pocket/`、`/pocket/manifest.webmanifest`、`/pocket/sw.js`、`/api/pocket/status` 和 `/api/pocket/history` 均返回 HTTP 200。Manifest 的 `display` 为 `standalone`；Service Worker 脚本缓存 Pocket 页面、manifest 与图标 shell，并将 `/api/` 请求排除在缓存之外。
- 本机浏览器页面可打开并显示桌面状态；macOS 防火墙处于开启状态，影序安装路径已列为允许入站连接，服务监听 `*:8080`。这些证据只说明本机服务和浏览器资源可用。
- 已尝试检查 iPhone 镜像；系统提示 iPhone 17 Pro 正在使用，需设备空闲才会连接。本轮未完成真实 iPhone/Android 同 Wi-Fi 访问、主屏幕安装、离线缓存、休眠唤醒或网络切换验收；不得把 localhost 页面测试视作手机实测。

## iPhone 镜像复核（2026-10-16，后续状态更新）

- iPhone Mirroring 后续已连上 iPhone 17 Pro。当前 Safari 的状态栏显示 5G，没有 Wi-Fi 标志，因此设备当前不具备与 Mac 同一局域网的已核实条件。
- 本轮没有更改 iPhone 网络设置，也没有提交配对码、备注或其他数据。Safari 停留在此前打开的页面；没有完成 Pocket LAN 请求。
- 下一步需在设备接入与 Mac 相同 Wi-Fi 后，实测 Pocket 打开、配对、状态/历史、备注、离线与网络切换。当前结果是环境条件未满足，不代表应用端 LAN 连接成功或失败。

## 跨平台修复与当前候选复验（2026-10-16）

- 修复 Pillow 灰度像素读取仍调用 `Image.getdata()` 触发弃用警告的问题，改用 `gray.tobytes()`；两项废片检测测试通过，明确验证实现不调用 `get_flattened_data()` 或弃用的 `getdata()`。本机完整测试 76 项运行、74 项通过、2 项因 Windows 平台条件跳过；将 `DeprecationWarning` 设为错误后整套测试仍通过。
- CI 工作流固定 Linux runner 为 Ubuntu 24.04；`actions/checkout@v7.0.1`、`actions/setup-python@v7.0.0`、`actions/upload-artifact@v7.0.2`、Pages artifact v5.0.0、deploy-pages v5.0.1 和 configure-pages v6.0.0 已更新。
- PR #4 当前 head `61248912a860d6d44ce3bb500f422ffd1d0c9232` 的 macOS / Ubuntu 24.04 / Windows × Python 3.11 / 3.12 六矩阵 CI 全部成功；小程序 Node 测试 4 项通过。
- Windows unsigned preview run `38918099130` 成功。下载核对文件为 PE32+ x86-64 GUI，27,757,332 bytes，SHA-256 `929781b66ce147483263301371bcd3bd6cabaa87258a6cf3b4e49dc01e17385f`。此项只验证 CI 构建与 artifact，不代表 Windows 真机验收。
- macOS release-candidate run `38918494881` 成功。DMG 为 22,255,777 bytes，SHA-256 `2512cacd14b2648b1c77a42b5267f7921caac17c4ee8d0e9a400667020674346`；`hdiutil verify`、随包 SHA256SUMS 比对、版本 `1.0.39`、Apple Silicon arm64 和深度代码签名验证均通过。签名仍为 ad-hoc、无 Team ID、未公证。
- 已将该 DMG 安装到 `/Applications/影序 YINGXU.app`。替换前旧 1.0.39 App 备份在 `/tmp/yingxu-installed-v1.0.39-before-6124891-2026-10-16/`，含恢复说明。新安装版从 `/Applications` 启动后 `/api/status` 返回 `1.0.39`，原生窗口再次扫描实际 SD_Card 完成：828 个文件、784 张照片、44 个视频、约 28,177.2 MB；本轮未对卡片写入或删除。
- 公网首页与 `/download/` HTTP 200，当前公开 Release 仍为 v1.0.34 Windows 包。Pages 部署工作流已升级，但从候选分支手动 dispatch 在 job 开始前被 `github-pages` 环境策略拒绝；该环境只允许 `main`。没有改动保护策略，本分支 `site/` 与 `origin/main` 一致。

## 当前仍未闭环

- Windows 真实设备安装、启动、SD 卡读写器和转移恢复验收。
- Apple Developer ID 签名/公证、公开 macOS Release 和下载端验收。
- iPhone 当前显示 5G，尚无 Mac 与手机同 Wi-Fi 条件；未做 Pocket 真机配对和网络切换验收。
- 原生 iOS/Android 工程仍未建立。微信小程序使用占位 `touristappid`，正式连接路径未确认；开发者工具预览、iPhone/Android 真机、隐私审核和上架均未完成。

## Windows 预览 artifact 架构与校验补充（2026-10-16）

- 在提交 `a3dc691` 上首次加入 Windows x64 PE 与 SHA-256 manifest 检查时，run `38919632876` 的构建成功，但清单回读失败。根因是 PowerShell ASCII 写入把中文 EXE 文件名替换为 `?`。
- 提交 `f2d9105` 改用 UTF-8 无 BOM 写入并明确以 UTF-8 回读。Windows preview run `38920093241` 全部成功，包括 PyInstaller 构建、x64 PE 检查、清单回读和 artifact 上传；同提交 Reliability tests run `38920081951` 与 `38920092240` 成功，覆盖 macOS / Ubuntu 24.04 / Windows × Python 3.11 / 3.12 六矩阵。
- 下载 artifact 再次验证为 PE32+ x86-64 GUI；`SHA256SUMS.txt` 对应的 `影序 YINGXU.exe` SHA-256 为 `3b6d42350b7eded002baf375edbad6a138ca059ac3de97f761d41a20a61ef44e`，本地清单校验通过。artifact 是 unsigned CI preview，未在 Windows 真机安装或运行。
