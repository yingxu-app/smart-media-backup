# 影序 YINGXU v1.0.29 发布验收

## 发布内容

- macOS Apple Silicon 桌面应用，版本号 `1.0.29`
- 增量跳过、SHA-256 校验、多目标备份、取消与暂停、失败报告
- JSON、CSV、Markdown 三种报告
- 归档检索、目标盘结果、文件夹层级命名与参考图

## 已完成验证

- 17 项可靠性与 API 安全回归测试全部通过
- macOS App 已由 PyInstaller 构建并完成 ad-hoc 深度签名验证
- App、Info.plist、README、更新日志版本号统一为 `1.0.29`
- 发布目录包含 App 与 Applications 拖拽入口
- DMG 已成功生成，并通过 `hdiutil verify` 完整性校验
- DMG SHA-256：`8d967e49a53ca40a2b8dbe3a6e54659bc173be61ed4fe3b50de72dbb96349e57`

## 发布边界

未购买 Apple Developer 账户，因此本版只能 ad-hoc 签名，无法公证。首次打开需按官网安装说明在“系统设置 → 隐私与安全性”中允许；官网不得把它描述为已通过 Apple 公证。

Windows 实机、iPhone/Android 原始素材后台读取，以及 Apple 公证不属于当前 Mac 与零付费条件下可完成的验收项。
