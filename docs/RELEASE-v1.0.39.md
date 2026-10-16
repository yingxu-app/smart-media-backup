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
