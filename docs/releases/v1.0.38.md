# v1.0.38 候选验收记录

状态：本机候选已构建并安装，首页读取真实存储卡仍未通过验收；不是公开发行版。GitHub 最新正式 Release 仍为 v1.0.34。

## 本轮改动

- macOS 来源发现按卷名优先级探测；当 SD 卡名称与根目录 `DCIM` 同时匹配时立即选中，不再继续打开其他卷根目录。
- macOS App 的 `Info.plist` 增加 `NSRemovableVolumesUsageDescription`，说明读取相机卡与外接盘的用途。
- 版本统一为 1.0.38。

## 已核实

- 新增自动来源发现回归测试，模拟 1TB 外置 SSD 排在 `SD_Card` 前；测试确认 SD 卡先被选择、无关卷根目录不被打开。
- 完整本机测试：67 项运行，65 项通过，2 项 Windows 平台条件跳过；`git diff --check` 通过。
- 候选提交 `62566eb7ff87f320bc1ceed3cfeb75e34dfa8ddd` 的可靠性矩阵 run `38895391564` 在 macOS、Windows、Ubuntu × Python 3.11/3.12 共 6 组全部通过。Windows 预览构建 run `38895398482` 成功；下载 artifact 为 PE32+ x86-64 GUI EXE，27,448,932 字节，SHA-256 `a2d2a860a67456d60543f0415633465750eacdd0521fa44de0bc29624a8a3306`，未签名；仍需真实 Windows 安装与设备验收。
- 当前挂载卷顺序确为 `SAMSUT7固态硬盘`、`SD_Card`。修改后的源码自动选择 `SD_Card` 约 0.003 秒；源码自动扫描 828 个文件约 0.1 秒。
- 用 LaunchServices 启动的 v1.0.37 与 v1.0.38 原生工作台均显示“正在读取存储卡”；同一冻结包在命令行启动时，自动 GET 扫描 828 个文件约 0.264 秒。通过 LaunchServices 启动候选时，首页扫描请求仍停在 `os_scandir`/`open` 系统调用；显式 API 请求也超时。
- 本机 TCC 数据库中的可移动卷许可对应旧 ad-hoc 代码签名要求；当前候选签名不同。v1.0.38 已加入可移动卷用途说明，但本轮没有出现可见授权弹窗，权限与原生扫描仍待用户及系统状态共同确认。这是目前的证据关联，根因尚不能断言为 TCC。
- arm64 App 版本为 1.0.38，深度签名校验通过。候选 DMG：`/tmp/yingxu-v1.0.38-release/YINGXU-macOS-v1.0.38.dmg`；`hdiutil verify` 通过；SHA-256 `dd5e1f317b06f504306f72ffa0bb4a565bfd35e83022a1077a2ace05aaabc3c4`。签名为 ad-hoc、未公证。
- `/Applications/影序 YINGXU.app` 当前为 v1.0.38；v1.0.37 完整回退副本和说明保存在 `/tmp/yingxu-installed-1.0.37-backup-2026-10-16/`。用户配置及历史数据库未迁移或修改。

## 官网状态

- 主仓库静态官网下载页已更新至 v1.0.38 候选状态，并明确未公开下载。提交 `dc833ea3d4f5dac304631880356ab3e5a8963ea3`；Pages workflow run `38895097709` 成功。带提交号缓存参数回读的首页、下载页、隐私页均 HTTP 200。正式 Release 仍为 v1.0.34，只有 Windows EXE 与 SHA256SUMS。

## 尚未验收

- LaunchServices 原生窗口读取真实 SD 卡及完成备份闭环。
- Apple Developer ID 签名、公证、公开 macOS DMG；Windows 真机；iPhone/Android 实机配对；微信小程序上线与商店上架。
- v1.0.38 尚未作为正式 Release 发布；官网只更新了候选状态说明，没有公开候选包。

## 下一步

在“系统设置 → 隐私与安全性 → 文件与文件夹 / 可移动宗卷”检查并授权影序访问可移动卷；若授权列表未显示当前代码签名身份，需要用户确认是否重置影序的可移动卷授权后重新启动。确认授权后，用安装版重新验证首页扫描和原生备份流程；若仍停滞，再继续定位 LaunchServices 与终端启动的差异。
