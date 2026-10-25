# 影序 YINGXU

> 摄影师的本地优先素材备份与归档工具：插卡 → 确认 → 备份 → 校验 → 可追溯。

[官网](https://yingxu-app.github.io/smart-media-backup/) · [下载](https://github.com/yingxu-app/smart-media-backup/releases/latest) · [文档索引](docs/README.md) · [更新日志](CHANGELOG.md) · [问题反馈](https://github.com/yingxu-app/smart-media-backup/issues)

## 三步上手

1. **插卡**：插入相机存储卡或读卡器，影序自动识别来源、文件数量、照片与视频，并按拍摄日期给出目录预览。
2. **确认**：填写事件名称，选择备份位置（本地目录、外接硬盘，可同时选多个目标）。
3. **备份**：点“开始备份”。复制完成后逐文件比对 SHA-256，生成可打开的备份报告。

备份默认**只读扫描、复制、校验**，不会自动删除原卡素材。第一次备份保留每一个文件；同一来源再次备份到同一目标时，逐个跳过已完成文件。

## 安全边界

这些规则写在代码里，也写在测试里（见 [测试矩阵](docs/TEST-MATRIX.md)）：

- 原卡始终是源，只读扫描和复制；
- 校验失败、取消、磁盘不可用、空间不足时，不允许清理原卡；
- 只有全部已选目标都完成且校验通过，界面才允许用户主动进入清理流程；
- Windows 上的“清理原卡”走系统回收站，回收站不可用时整个流程失败退出，素材保持原样；
- 素材和历史默认留在本机；百度网盘、云端 AI 都是可选，未配置时不影响本地备份；
- 若设备或地点无法可靠识别，会明确显示“待确认”，不假装猜对。

## 平台现状

最新公开 Release 是 **v1.0.34**，只包含 Windows 安装包。macOS v1.0.40 是 ad-hoc 签名、未公证的本机候选；Android 只有内部 preview；iOS 走 Safari PWA。都不要当成已上线产品宣传。

| 平台 | 交付形态 | 当前状态 |
| --- | --- | --- |
| macOS | `.app` / DMG | v1.0.40 本机候选已安装并扫描真实存储卡；未公开发行，未公证 |
| Windows | 便携 `.exe` | v1.0.40 unsigned CI preview 构建通过；真实读卡器与断电场景未验收 |
| iPhone | Safari PWA | 局域网 Pocket 页可用（需配对）；独立 HTTPS PWA 源码就绪，未部署、未在 iPhone 验收 |
| Android | EAS preview APK | 已构建并校验，无测试机，未公开发布 |
| 微信小程序 | 局域网 TCP 原型 | 占位 AppID，未在微信开发者工具预览 |

仍在等真实设备验证的项：物理拔卡、断电中断、大容量卡压力、Windows 真实读卡器、iPhone 同 Wi-Fi 配对。验收记录都在 [docs/releases](docs/releases/)。

## 功能

| 能力 | 说明 |
| --- | --- |
| 来源扫描 | 识别存储卡、外接盘，显示文件数、照片/视频数与容量统计 |
| 多目标备份 | 一个目标异常不影响其他目标，也不会删除原卡素材 |
| 增量跳过 | 按来源路径、哈希与完成历史判断，不会把同内容不同文件误判为重复 |
| SHA-256 校验 | 复制后比对源与目标，报告和历史都显示校验结果 |
| 中断恢复 | 取消或目标不可用时记录部分完成状态，重跑可继续处理未完成文件 |
| 归档与报告 | 保留每个目标的成功/跳过/失败/校验结果，导出 JSON、CSV、Markdown |
| 转移老内容 | 已归档素材重新分类；目标副本校验通过后才移出源文件 |
| 废片与重复提示 | 本地哈希判完全重复，感知哈希提示相似照片，AI 只做建议 |
| AI 视觉建议 | 可选 Ollama 本地模型，或千问、DeepSeek、OpenRouter 云端视觉服务 |
| 影序 Pocket | 同一 Wi-Fi 下用手机看桌面端进度、历史，填写拍摄信息 |

AI 服务的配置与数据边界见 [AI 模型服务说明](docs/AI-MODEL-SETUP.md) 和 [AI 安全说明](docs/AI-SAFETY.md)。

## 影序 Pocket

Pocket 有两个入口，别混在一起：

- `site/pocket/` 是 HTTPS PWA：登录 Firebase 后可看云端备份进度与历史，页面可缓存，电脑关机时仍能看到缓存的记录。首次打开需要联网。
- 桌面端提供的局域网 `/pocket/` 页面：需要在 Mac 版“偏好设置 → 影序 Pocket”生成 6 位配对码（十分钟内有效、只能用一次），手机与电脑在同一 Wi-Fi 下访问。可以查看实时进度、历史，也能从手机选照片/RAW/视频，按事件分组做 SHA-256 预检后分块传到已配对的电脑。

只有用户主动选取的原始媒体会经局域网传到配对电脑，不会上传到影序云端。浏览器锁屏或切换应用可能中断复制，不承诺后台持续传输。详见 [Pocket 使用说明](docs/POCKET.md)。

## 安装

从 [Releases](https://github.com/yingxu-app/smart-media-backup/releases) 下载与系统对应的安装包，并核对 Release 里提供的 SHA-256。

- macOS：未公证的候选会触发 Gatekeeper 提示，请只对你自己从本仓库下载并核对过哈希的文件放行。
- Windows：当前 v1.0.34 安装包可直接安装；CI preview 是 unsigned 包，用于验收，不作正式分发。

## 开发

```bash
git clone https://github.com/yingxu-app/smart-media-backup.git
cd smart-media-backup
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 -m compileall -q smb desktop tests
```

macOS 打包（项目内虚拟环境）：

```bash
cd desktop
../.venv/bin/python -m PyInstaller smb.spec --noconfirm
```

Windows 端到端与冒烟检查：

```bash
python scripts/e2e_win_check.py
python scripts/smoke_yingxu_win.py
```

## 仓库结构

```text
smb/           Python 核心包：扫描、备份、校验、配置、数据库、Pocket 服务
desktop/       桌面端外壳与 PyInstaller 打包配置
mobile/        Expo 原生壳（Android / iOS）
miniprogram/   微信小程序局域网原型
site/          GitHub Pages 官网、下载页与 Pocket PWA
scripts/       构建、打包、验收脚本
tests/         自动化回归测试
docs/          文档：使用说明、架构、发布验收记录、比赛材料
dist/          构建产物目录（不入库，仅本机生成）
```

文档怎么找，看 [docs/README.md](docs/README.md)。

## 开源

MIT License。上海立达学院学生独立开发作品，欢迎通过 [Issues](https://github.com/yingxu-app/smart-media-backup/issues) 提 Bug、使用建议与素材工作流需求。提交代码前请先读 [CONTRIBUTING.md](CONTRIBUTING.md)。
