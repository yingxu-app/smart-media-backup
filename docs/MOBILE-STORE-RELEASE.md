# 影序 Pocket 移动端构建与商店交付

`mobile/eas.json` 保存 Expo Application Services（EAS）的可复用构建档案：

| 档案 | 用途 | 输出 |
| --- | --- | --- |
| `development` | 原生开发客户端 | 内部分发；依赖 `expo-dev-client` |
| `preview` | Android 设备安装与验收 | 内部分发 APK |
| `production` | 商店候选 | Android AAB；iOS 默认生成商店发行构建 |

GitHub Actions 另有 `ios-device-unsigned` 候选 job：使用 GitHub macOS runner 构建 iPhoneOS `.app`，封装成未签名 IPA 并附 SHA-256。该包不能直接安装到 iPhone；需要用户自行使用 AltStore Classic / AltServer 等侧载工具，用自己的 Apple Account 在安装时签名。免费个人签名会过期并要求定期刷新，且有同时安装数量限制。这个路径用于个人设备测试，不是公开发行渠道，也不等于 App Store 签名或审核。

用户电脑不需要安装 Xcode；Xcode 仍在 GitHub 的 macOS 构建 runner 中执行。若希望官方 EAS 内测链接直接安装到 iPhone，仍需 Apple Developer Program 和注册设备。

提交档案目前只指定 Google Play 内部测试轨道。iOS App Store Connect App ID、开发者团队、Apple 签名、Google Play 服务账号、EAS 项目 ID 均未配置；不得把当前 CI debug APK 或模拟器 App 当作商店包。

## 账号绑定后执行

在项目所有者控制的终端登录 Expo 并绑定 EAS 项目，使用官方 CLI 将项目 ID 写入 `mobile/app.json` 的 `expo.extra.eas.projectId`。本仓库使用 pnpm；本机 npm 启动器有依赖加载错误，因此操作命令统一使用 `pnpm dlx`：

```sh
cd mobile
pnpm dlx eas-cli@latest account:login
pnpm dlx eas-cli@latest account:view
pnpm dlx eas-cli@latest project:init
pnpm dlx eas-cli@latest build --profile development --platform all
pnpm dlx eas-cli@latest build --profile preview --platform android
pnpm dlx eas-cli@latest build --profile production --platform all
```

完成 Apple / Google 商店凭据与应用记录设置后，才可提交商店审核。Android 内测提交可使用：

```sh
pnpm dlx eas-cli@latest submit --profile production --platform android
```

首次提交前须在 Play Console 确认包名 `com.yingxuapp.pocket` 已由目标发行账号持有，并确保 EAS 上传的 AAB 与商店应用记录匹配。iOS 需先取得实际 App Store Connect App ID 和团队配置；不在仓库中保存私钥、服务账号 JSON 或令牌。

## 验收边界

- EAS 配置文件不等于已绑定 Expo 项目、构建成功、签名成功或商店上架。
- 本机曾用已缓存的 `pnpm dlx eas-cli@latest whoami` 做只读查询，返回 `Not logged in`。该查询不创建 EAS 项目；项目所有者登录后再执行 `project:init`。
- 生产构建前仍须完成 iPhone/Android 真机安装、局域网配对、权限、后台/切网恢复验收。
- 商店提交必须核对应用版本、隐私说明、截图、支持网址、分级与审核资料；公开发布后再从商店链接安装回读。
