# v1.0.36 本地候选验收记录

状态：本地候选，未提交、未推送、未创建 GitHub Release。产品源码仍保留本机已有的“转移老内容”未提交改动。

## 构建产物

- Apple Silicon App：`/tmp/yingxu-v1036-final/dist/影序 YINGXU.app`
- DMG：[release/v1.0.36/YINGXU-macOS-v1.0.36.dmg](../release/v1.0.36/YINGXU-macOS-v1.0.36.dmg)
- DMG SHA-256：`cff0d1ba5b7cad595f2b82337c9229bc30766d1cd4f1214cdbd8f171af7ce432`
- App 版本：`1.0.36`；Info.plist、健康 API 与运行中的安装版一致。
- `codesign --verify --deep --strict` 通过（ad-hoc）；`hdiutil verify` 通过；只读挂载确认 App 和 `/Applications` 快捷方式存在。

## 本轮实现与验收

- 旧版首启扫描挂起时，系统采样显示扫描线程在每个文件的相机/拍摄日期/GPS读取中反复尝试启动 ExifTool；本机没有安装该程序。冻结 App 上的失败进程启动开销累积，安装版曾超过 6 分钟未返回扫描结果。
- `smb/organizer.py` 现在缓存 ExifTool 的一次性路径探测。未安装时直接走原有文件名设备识别与文件修改时间回退，避免为每个文件启动不存在的进程；已安装时仍调用 ExifTool。
- 新增 2 项 ExifTool 有无两种路径的回归测试。完整测试：58 项运行，56 项通过、2 项 Windows 条件跳过；`git diff --check` 通过。
- 当前工作树在 SD 卡上扫描 828 个媒体文件和提取元数据耗时约 4 秒。
- v1.0.36 干净构建与 `/Applications/影序 YINGXU.app` 安装版启动后，首页扫描均返回 828 个文件：大疆设备 528 个（484 张照片、44 个视频），未知设备 300 张照片。原生窗口辅助信息显示“已插入 SD 卡”和“使用已保存的扫描结果”；安装版健康 API 返回 HTTP 200、版本 1.0.36。
- 安装版 `/api/sources` 返回 HTTP 200，来源列表识别出外置 SSD 的 2774 个文件和 SD 卡的 828 个文件；`/transfer` 返回 HTTP 200。
- 通过安装版 HTTP 接口在隔离临时目录中完成 1 个虚拟 JPG 的扫描、分析和转移。目标字节 SHA-256 一致，校验完成后源测试文件才被移除；未对真实用户素材执行转移。

## 回滚与未完成门槛

- 替换前的 1.0.35 安装包副本：`/tmp/yingxu-installed-1.0.35-backup-2026-10-16/影序 YINGXU.app`，同目录含恢复说明；更早的 1.0.33 副本仍在 `/tmp/yingxu-installed-1.0.33-backup-2026-10-16`。
- DMG 目前仅 ad-hoc 签名，未完成 Apple 公证或 notarization staple。
- 尚未构建并验收 Windows 安装包，Windows 真机、iPhone Safari/安装体验与外置盘拔出、目标盘中断等真实故障场景仍待完成。
- GitHub 最新公开版本仍需现场复核；本轮没有推送产品仓库或创建公开发行版。
- 官网/在线产品范围和小程序平台尚未确认，相关部署及上架不作完成声明。
