# 影序 Pocket 移动端构建与商店交付

`mobile/eas.json` 保存 Expo Application Services（EAS）的可复用构建档案：

| 档案 | 用途 | 输出 |
| --- | --- | --- |
| `development` | 原生开发客户端 | 内部分发；依赖 `expo-dev-client` |
| `preview` | Android 设备安装与验收 | 内部分发 APK |
| `production` | 商店候选 | Android AAB；iOS 默认生成商店发行构建 |

iOS 按正式发行路线交付：使用 EAS 云端构建并签名，再上传 App Store Connect，通过 TestFlight 邀请测试者，完成审核后发布 App Store。用户无需在自己的电脑安装 Xcode；EAS 的远程构建环境负责 iOS 原生构建。TestFlight 和 App Store 分发需要 Apple Developer Program 会员以及 App Store Connect 应用记录。无签名 IPA 不能通过设备上的“信任开发者”设置直接安装；本项目不再生成 AltStore/免费个人签名侧载包。

用户电脑不需要安装 Xcode；EAS 在云端执行原生构建。TestFlight 分发依赖 Apple Developer Program 与 App Store Connect，不需要逐台登记测试设备。

提交档案目前只指定 Google Play 内部测试轨道。EAS 项目已绑定到 Expo 账号 `nanyu-lu`；iOS App Store Connect 应用记录、Apple Developer Program 团队与签名凭据、Google Play 服务账号仍未配置。不得把当前 CI debug APK 或 EAS preview APK 当作商店包。正式 iOS 发行须由项目所有者先完成 Apple Developer Program 注册与协议；我们不代持或索取账号密码、验证码、私钥。

## EAS 项目已绑定；后续构建与发行

EAS 项目为 [`@nanyu-lu/yingxu-pocket`](https://expo.dev/accounts/nanyu-lu/projects/yingxu-pocket)，ID `e83a97a0-f588-4068-a66d-f3e38782bcc1`，已写入 `mobile/app.json`。本仓库使用 pnpm；构建命令统一使用 `pnpm dlx`：

```sh
cd mobile
pnpm dlx eas-cli@latest account:login
pnpm dlx eas-cli@latest account:view
pnpm dlx eas-cli@latest build --profile development --platform all
pnpm dlx eas-cli@latest build --profile preview --platform android
pnpm dlx eas-cli@latest build --profile production --platform all
```

完成 Apple / Google 商店凭据与应用记录设置后，才可提交商店审核。Android 内测提交可使用：

```sh
pnpm dlx eas-cli@latest submit --profile production --platform android
```

首次提交前须在 Play Console 确认包名 `com.yingxuapp.pocket` 已由目标发行账号持有，并确保 EAS 上传的 AAB 与商店应用记录匹配。iOS 需先由账号所有者完成 Apple Developer Program 注册、创建 App Store Connect 应用记录，并在 EAS 中配置团队签名凭据；不在仓库中保存私钥、服务账号 JSON 或令牌。完成后执行 `pnpm dlx eas-cli@latest build --profile production --platform ios`，通过 TestFlight 验收后再提交 App Review。

## 验收边界

- EAS 配置文件不等于已绑定 Expo 项目、构建成功、签名成功或商店上架。
- 正式 iOS 路线没有 7 天免费签名刷新；它依赖付费 Apple Developer Program 会员。当前账号/团队未配置，因此暂不能产出可供 TestFlight 安装的签名包。
- 历史上曾有一次 Expo CLI `whoami` 返回 `Not logged in`；该状态已由后续项目所有者 OAuth 登录解决。EAS 项目和构建已实证成功，见下方记录。
- 生产构建前仍须完成 iPhone/Android 真机安装、局域网配对、权限、后台/切网恢复验收。
- 商店提交必须核对应用版本、隐私说明、截图、支持网址、分级与审核资料；公开发布后再从商店链接安装回读。

## 2026-10-19 EAS Android preview 构建记录

- EAS Android preview build `2926409f-7f75-454f-91a8-37ebf4dc2a66` 已完成（`FINISHED`）；构建详情：[Expo build](https://expo.dev/accounts/nanyu-lu/projects/yingxu-pocket/builds/2926409f-7f75-454f-91a8-37ebf4dc2a66)。profile `preview`，app version `1.0.0` / build `1`，包名 `com.yingxuapp.pocket`，来源提交 `2b1c89b`。
- APK 已下载到本机并完成 SHA-256 与 ZIP 完整性核验：`/Users/nanyu/Downloads/影序Pocket-Android-preview-1.0.0-build1.apk`，92,264,537 bytes，SHA-256 `9783f71f24c0105d8d22457e8f7715fbe2d61d6599d63ba578730f3e7b1cba64`；APK ZIP 测试通过，包含 `arm64-v8a`、`armeabi-v7a`、`x86`、`x86_64`，二进制 Manifest 中可见包名。此为内部 preview 构建，尚无 Android 真机安装验收；本地计算的 SHA-256 不是 Expo 发布的独立校验和。
- 同提交 GitHub Actions Pocket run `39205982845` 成功，JS/CNG/check、Android debug 和 iOS Simulator jobs 均成功；Actions 仅提供 Android debug artifact，没有 iOS Simulator app artifact 或 IPA。
- iPhone 真机分发仍需 Apple Developer Program 账户、App Store Connect 应用记录及签名配置。Simulator build 和 Android APK 均不构成 iPhone 可安装包。
