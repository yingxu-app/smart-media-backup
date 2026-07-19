# 🖼 Smart Media Backup — 完整项目交接文档

## 项目一句话
插 SD 卡到电脑 → 自动读设备/日期 → 用户输入事件名 → 按 设备→事件→照片/视频 分类 → Web 面板可视化 → 可选百度网盘自动上传

---

## 用户信息
- 姓名：陆冠霖（冠霖兄）
- 微信：通过微信与Hermes沟通
- 设备：MacBook Air M3 + 16GB RAM, macOS Sequoia
- 摄影师/视频创作者，Sony A7 + DJI，11TB外置盘"回忆"
- GitHub: luguanlin20050927
- Gitee: luguanlin
- 百度网盘已注册开发者（App ID: 123996589）

---

## 项目目录结构
```
~/smart-media-backup/
├── smb/                          # Python 核心包
│   ├── __init__.py               # 包入口, 版本号
│   ├── __main__.py               # python -m smb 入口
│   ├── server.py                 # Flask + SocketIO Web 服务（主入口）
│   ├── backup.py                 # 备份引擎（扫描→元数据→拷贝→校验+百度触发）
│   ├── detector.py               # SD 卡检测（macOS /Volumes, Win盘符, Linux挂载点）
│   ├── organizer.py              # EXIF 元数据提取 + 分类整理
│   ├── verifier.py               # SHA256 校验
│   ├── config.py                 # JSON 配置管理（~/.config/smb/）
│   ├── db.py                     # SQLite 历史记录
│   ├── baidu.py                  # 百度网盘 OAuth + 分片上传
│   ├── ai_namer.py               # AI 自动命名（Ollama / OpenAI）
│   ├── cli.py                    # 命令行接口
│   ├── templates/                # HTML 模板
│   │   ├── base.html             # 基础布局（侧边栏+状态栏）
│   │   ├── dashboard.html        # 主仪表盘（检测+操作+进度）
│   │   ├── history.html          # 备份历史
│   │   └── settings.html         # 设置（含百度网盘+AI配置）
│   └── static/
│       ├── css/app.css           # 深色主题样式
│       ├── js/app.js             # 全局JS
│       └── img/icon.svg          # SVG图标
├── desktop/                      # 桌面 App 打包
│   ├── smb.spec                  # macOS PyInstaller 配置
│   ├── smb-win.spec              # Windows PyInstaller 配置
│   ├── app.py                    # macOS .app 启动入口
│   ├── setup.py                  # py2app 配置（已弃用，保留参考）
│   ├── icon.icns                 # 应用图标（相机+SD卡）
│   └── dist/                     # 打包输出
├── website/                      # 官网
│   └── index.html                # 单页官网（含下载+安装教程）
├── .github/workflows/
│   ├── deploy-website.yml        # 部署 GitHub Pages
│   ├── build-windows.yml         # Windows .exe 自动构建
│   └── sync-gitee.yml            # 同步到 Gitee
├── vercel.json                   # Vercel 部署配置
├── setup.py                      # pip install 配置
├── requirements.txt              # Python 依赖
└── AGENTS.md                     # 本文件
```

---

## 核心业务流程

### 备份流程（完整）
```
用户插SD卡 → detector.py自动检测到新卷
  → organizer.py扫描卡内文件（按扩展名筛选RAW/照片/视频）
  → 批量提取EXIF元数据（相机型号、拍摄日期、GPS）
  → 按设备分类 → 前端显示检测结果
  → 用户输入事件名 → 选择备份目标盘
  → 点开始备份
  → backup.py: 逐文件shutil.copy2到目标
    目标路径: {backup_root}/{设备名}/{事件名}/照片/ 或 视频/
    保留原始文件名
  → verifier.py: SHA256校验每个拷贝的文件
  → db.py: 写入SQLite历史记录
  → 自动触发 baidu.py: 后台线程上传到百度网盘
  → WebSocket实时推送到前端（进度条/速度/队列）
```

### 目录结构（备份后的文件）
```
{备份盘}/
├── Sony ILCE-7M4/
│   └── 2025年8月漫展/           ← 用户输入的事件名
│       ├── 照片/
│       │   ├── DSC01234.ARW    ← 保留原始文件名
│       │   └── checksums.json  ← SHA256校验清单
│       └── 视频/
│           ├── C0001.MP4
│           └── checksums.json
└── DJI Mavic 3/
    └── 2025年8月漫展/
        └── 视频/
            └── ...
```

### 百度网盘上传流程
```
备份完成 → _trigger_baidu_upload() 后台线程
  → 检查 baidu.is_configured() && baidu.is_authorized()
  → 遍历备份目录所有文件（跳过checksums.json）
  → baidu.mkdir() 创建远程目录
  → baidu.upload_file() 上传
    小文件(<4MB): 直接POST上传
    大文件: precreate → 分片upload → create合并
```

### AI 自动命名流程
```
SD卡扫描完成 → ai_namer.suggest_event_name(sample_images)
  → 取前5张照片
  → 根据backend选择分析方式
    ollama: POST /api/chat → llava模型
    openai: OpenAI SDK → gpt-4o-mini
  → 返回2-6字中文短语 → 自动填入事件名输入框
```

---

## API 路由完整清单

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 仪表盘页面 |
| `/history` | GET | 历史记录页面 |
| `/settings` | GET | 设置页面 |
| `/website` | GET | 官网landing page |
| `/api/status` | GET | 当前状态+进度 |
| `/api/volumes` | GET | 所有可用磁盘（过滤系统卷） |
| `/api/scan` | GET/POST | 扫描SD卡，返回设备列表+文件+AI建议名 |
| `/api/start_backup` | POST | 开始备份，body: {mount_point, event_name, backup_root} |
| `/api/cancel_backup` | POST | 取消当前备份 |
| `/api/history` | GET | 备份历史列表（limit/offset分页） |
| `/api/history/<id>` | GET | 单条历史详情+文件列表 |
| `/api/baidu/status` | GET | 百度网盘配置/授权状态 |
| `/api/baidu/settings` | POST | 保存百度API Key/Secret |
| `/api/baidu/auth_url` | GET | 获取OAuth授权URL |
| `/api/baidu/exchange` | POST | 兑换授权码，body: {code} |
| `/api/baidu/quota` | GET | 网盘容量 |
| `/api/ai/status` | GET | AI命名配置状态 |
| `/api/ai/settings` | POST | 保存AI命名配置 |
| `/download/macos` | GET | 下载 macOS DMG |

---

## 配置位置
- 百度网盘凭证: `~/.config/smb/baidu_settings.json` + `baidu_token.json`
- AI 命名设置: `~/.config/smb/ai_settings.json`
- 应用配置: `~/.config/smb/config.json`
- 历史数据库: `~/.config/smb/backup_history.db`

---

## 当前状态（2025-07-19）

### ✅ 已完成
| 模块 | 说明 |
|------|------|
| 核心引擎 | SD检测→EXIF→按设备/事件/照片-视频分类→SHA256校验→SQLite |
| Web面板 | Flask+SocketIO, Chart.js图表, 暗色主题 |
| macOS App | PyInstaller打包, 自签名, DMG安装包, 桌面双击可用 |
| Windows App | GitHub Actions自动构建, Release可下载 |
| 官网 | GitHub Pages + Vercel 双线部署, 含下载链接+安装教程 |
| AI命名 | 支持Ollama本地(llava) / OpenAI(gpt-4o-mini), 默认Ollama |
| 百度网盘 | OAuth已授权, 分片上传, 备份完自动触发 |
| GitHub | 代码全部推送, 含CI/CD工作流 |
| Gitee | Actions自动同步（Pages服务已下线） |
| 项目文档 | AGENTS.md供AI参考 |

### ⏳ 待办/可优化
- [ ] 百度网盘 quota API 返回为0（可能需要调试接口）
- [ ] 增量备份（第二次只拷新文件）
- [ ] 树莓派镜像
- [ ] Apple开发者证书($99)彻底去掉Gatekeeper弹窗
- [ ] 自定义域名（smartbackup.app等）

---

## 关键命令
```bash
# 本地开发
cd ~/smart-media-backup
pip install -e .        # 安装（已安装则跳过）
smb                     # 启动 Web 面板（localhost:8080）
smb scan               # 快速扫描 SD 卡

# 打包 macOS .app
cd desktop
pyinstaller smb.spec --noconfirm
cp -R dist/Smart\ Media\ Backup.app ~/Desktop/

# 打包 Windows .exe（在Windows上跑）
pyinstaller smb-win.spec --noconfirm
```

---

## 已知问题
1. **百度网盘 quota API** 返回0——可能是个人版API端点与文档不同，需调试
2. **Windows构建** 依赖GitHub Actions，本地需Windows环境
3. **ai_namer.py** 依赖PIL(Pillow)处理图片base64，需确保安装
4. **exiftool** 是可选依赖，没有它则用文件修改时间+文件名启发式

---

## 部署
- GitHub Pages: https://luguanlin20050927.github.io/smart-media-backup
- Vercel: https://smart-media-backup.vercel.app （国内可访问）
- Windows下载: https://github.com/luguanlin20050927/smart-media-backup/releases/download/v1.0.0/SmartMediaBackup-Windows.exe
- macOS下载: https://github.com/luguanlin20050927/smart-media-backup/releases/download/v1.0.0/SmartMediaBackup-macOS.dmg
