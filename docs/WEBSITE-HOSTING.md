# 官网部署

当前网页仅保留以下两处托管，首页、下载、更新、隐私页和 Pocket 控制台使用同一套站点源码。

| 用途 | 平台 | 地址 |
|---|---|---|
| 主站 | GitHub Pages | https://yingxu-app.github.io/smart-media-backup/ |
| 备用站 | ChatGPT Sites | https://yingxu-smart-media-backup.nanyu20050927.chatgpt.site/ |

## 发布来源

- GitHub Pages：本仓库 `main` 分支的 `site/`，由 `.github/workflows/deploy-website.yml` 发布。
- ChatGPT Sites：项目 `appgprj_6ad8ef6842ec8191849ebf0742a4a3f4`，同步 `site/` 静态文件。
- 安装包统一从 [GitHub Releases](https://github.com/yingxu-app/smart-media-backup/releases/latest) 下载。
- Pocket 路径为上述任一站点下的 `pocket/`。
