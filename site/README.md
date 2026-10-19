# 影序官网静态页面

这是影序主仓库中的 GitHub Pages 站点，使用纯 HTML/CSS，不依赖第三方运行时或跟踪脚本。

- 首页：`index.html`
- 正式版下载页：`download/index.html`
- 桌面版升级和回退说明：`update/index.html`
- 隐私说明：`privacy.html`
- iPhone Safari PWA：`pocket/`（已部署到 HTTPS；Firebase 元数据同步、浏览器本机缓存；真实账号和 iPhone 安装/离线恢复仍待验收）
- 发布入口：`https://yingxu-app.github.io/smart-media-backup/`
- 发布工作流：`.github/workflows/deploy-website.yml`

下载页只链接正式公开版本。用户已决定不配置 macOS Developer ID、Windows Authenticode 身份签名或 Apple 公证；macOS arm64 包保留无身份的 ad-hoc 技术签名以兼容系统启动要求，Windows 包保持未签名。未公开候选仍不会被列为下载。iOS 采用 Safari PWA，不开发原生 iOS App；Android 真机验收因无设备暂缓，微信小程序已停止开发。Pocket PWA 已部署到 HTTPS，真实 Firebase 账号和 iPhone 安装/离线恢复尚未验收。若 GitHub Releases 更新，需同步核对下载链接、版本、校验文件、升级回滚流程和文案。
