# 影序 YINGXU · 交接与维护说明

> 面向接手这个仓库的人（和 AI 助手）。产品说明在 [README.md](README.md)，文档入口在 [docs/README.md](docs/README.md)。

## 一句话

插存储卡 → 读设备与日期 → 用户填事件名 → 按「设备 / 事件 / 照片-视频」分类复制 → SHA-256 校验 → 写入历史并出报告。本地优先，百度网盘与云端 AI 都是可选项。

## 运行环境

- 作者本机：MacBook Air M3 / 16 GB / macOS Sequoia，外置盘 11 TB「回忆」；Sony A7 + DJI 素材。
- Windows 侧验证在 GitHub Actions 的 `windows-latest` 和一台真机上进行，没有长期可用的 Windows 开发机。
- Python 3.11 / 3.12（CI 矩阵），Node + pnpm 用于 `mobile/`。

## 仓库结构

```text
smb/           Python 核心包（server / backup / organizer / verifier / db / baidu / pocket*）
desktop/       桌面壳（pywebview）与 PyInstaller 配置：smb.spec（macOS）、smb-win.spec（Windows）
mobile/        Expo 原生壳（Android / iOS），pnpm 管理
miniprogram/   微信小程序局域网 TCP 原型（占位 AppID）
site/          GitHub Pages：官网、下载页、Pocket PWA
scripts/       构建、打包、上传、图标生成、Windows 端到端与冒烟检查、文档链接检查
tests/         unittest 回归套件 + Node 端 Pocket 测试
docs/          文档（结构见 docs/README.md）
dist/          PyInstaller 输出目录，不入库
```

打包产物统一出到仓库根的 `dist/`；`desktop/dist/` 只在 macOS 本地打包时出现。

## 核心流程

**备份**

```text
detector 发现卷 → organizer 扫描 + EXIF → 前端按日期预览目录
→ 用户填事件名、选目标 → backup 逐文件 copy2 + SHA-256
→ db 写历史 → 报告 JSON / CSV / Markdown → 可选百度网盘后台上传
```

**转移老内容**（用户显式触发）：扫描已归档素材 → 分类命名 → 复制到目标 → 校验 → 校验通过才移除源文件；取消或失败一律保留源文件。Windows 上的删除走回收站，回收站不可用时整个流程失败退出。

**Pocket**：`site/pocket/`（HTTPS PWA，走 Firebase 看云端进度）与桌面端局域网 `/pocket/`（6 位一次性配对码，同 Wi-Fi）是两条不同入口，别混。局域网页面上传走「计划 → 分块 → 完成」的 inbox 接口，桌面端复核 SHA-256 后才落盘。

## 接口

全部路由都在 `smb/server.py`（Flask + SocketIO），按前缀分组：

| 前缀 | 用途 |
| --- | --- |
| `/api/status`、`/api/volumes`、`/api/sources`、`/api/scan`、`/api/preview/` | 来源探测与扫描预览 |
| `/api/start_backup`、`/api/cancel_backup`、`/api/pause_backup`、`/api/cleanup_sd` | 备份控制 |
| `/api/transfer/*` | 转移老内容工作区 |
| `/api/history*`、`/api/sync/*` | 归档记录与多设备元数据同步 |
| `/api/baidu/*`、`/api/ai/*` | 百度网盘、AI 服务配置与状态 |
| `/api/pocket/*`、`/pocket/` | 手机协作台（配对、状态、备注、inbox 上传） |

新增路由请顺手补 `tests/` 里的对应用例；`server.py` 里的表是这个仓库唯一可信的接口清单，不要再往文档里抄一份。

## 配置与数据位置

| 内容 | 位置 |
| --- | --- |
| 应用配置 | `~/.config/smb/config.json`（`SMB_CONFIG_DIR` 可覆盖，测试与 CI 都靠它隔离） |
| 配置 schema 版本 | 同目录 `config.schema.json`（独立记录，方便旧版回退） |
| 历史数据库 | `~/.config/smb/backup_history.db` |
| 百度网盘凭证 | `~/.config/smb/baidu_settings.json` + `baidu_token.json` |
| AI 服务密钥 | 系统钥匙串 / 凭据库，不落明文配置 |

## 当前状态（2026-10）

- 公开 Release 最新是 v1.0.34，只有 Windows 包；macOS 与 Android 只有候选/预览。
- v1.0.40 是当前开发版本，本机 macOS 验收通过，Windows 只有 unsigned CI preview。
- 真实账号的 Firebase 跨设备同步、iPhone 真机配对、Android 真机安装仍未完成。
- 逐版本细节见 [docs/releases/](docs/releases/)。

## 已知问题

1. 百度网盘 quota 接口曾返回 0，已改为带 `checkfree`/`checkexpire` 读取 `total`/`used`，真实账号仍待复核。
2. Windows 打包只能在 Windows 上做，本地无 Windows 机器时依赖 Actions。
3. `ai_namer` 依赖 Pillow 处理缩略图；缺少 ExifTool 时退化为文件名 + 修改时间启发式（会有明显误差，不要当成 EXIF 解析）。
4. 物理拔卡、断电、大容量卡压力三项没有真实环境验收记录，不要在文案里写成“已支持”。

## 常用命令

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v     # 回归套件
python -m compileall -q smb desktop tests   # 语法检查
python scripts/check_links.py               # 文档相对链接检查
smb                                         # 启动本地面板（localhost:8080）

cd desktop && pyinstaller smb.spec --noconfirm        # macOS
pyinstaller desktop/smb-win.spec --noconfirm          # Windows
```

## 维护约定

这几条是整理仓库时定下的，请保持：

1. **文档分层**：使用说明留在 `docs/*.md`，版本记录进 `docs/releases/`，过程与审计进 `docs/reports/`，比赛材料进 `docs/product/`。新增文档前先看 [docs/README.md](docs/README.md) 放对位置。
2. **不留副本**：改文件不要生成 `*.before-*`、`*.orig` 之类的副本再提交；要留证据就在 `docs/reports/` 写一份记录，旧内容交给 git 历史。`.gitignore` 已经把这些扩展名挡住了。
3. **二进制不进库**：安装包、APK、DMG 一律放 GitHub Releases 或 Actions artifact，`dist/` 已在 `.gitignore` 里。
4. **链接要能点**：移动或改名文档后跑 `python scripts/check_links.py`，CI 的 `Reliability tests` 也会跑这一步。
5. **状态要诚实**：CI 跑通 ≠ 本机装过 ≠ 真机验收。写 README、官网、Release note 时按实际情况标注。
