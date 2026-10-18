# 影序 Pocket 移动端构建与商店交付

`mobile/eas.json` 保存 Expo Application Services（EAS）的可复用构建档案：

| 档案 | 用途 | 输出 |
| --- | --- | --- |
| `development` | 原生开发客户端 | 内部分发；依赖 `expo-dev-client` |
| `preview` | Android 设备安装与验收 | 内部分发 APK |
| `production` | 商店候选 | Android AAB；iOS 默认生成商店发行构建 |

iOS 按正式发行路线交付：使用 EAS 云端构建并签名，再上传 App Store Connect，通过 TestFlight 邀请测试者，完成审核后发布 App Store。用户无需在自己的电脑安装 Xcode；EAS 的远程构建环境负责 iOS 原生构建。TestFlight 和 App Store 分发需要 Apple Developer Program 会员以及 App Store Connect 应用记录。无签名 IPA 不能通过设备上的“信任开发者”设置直接安装；本项目不再生成 AltStore/免费个人签名侧载包。

用户电脑不需要安装 Xcode；EAS 在云端执行原生构建。TestFlight 分发依赖 Apple Developer Program 与 App Store Connect，不需要逐台登记测试设备。

提交档案目前只指定 Google Play 内部测试轨道。iOS App Store Connect 应用记录、Apple Developer Program 团队与签名凭据、Google Play 服务账号、EAS 项目 ID 均未配置；不得把当前 CI debug APK 或模拟器 App 当作商店包。正式 iOS 发行须由项目所有者先完成 Apple Developer Program 注册与协议；我们不代持或索取账号密码、验证码、私钥。

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

首次提交前须在 Play Console 确认包名 `com.yingxuapp.pocket` 已由目标发行账号持有，并确保 EAS 上传的 AAB 与商店应用记录匹配。iOS 需先由账号所有者完成 Apple Developer Program 注册、创建 App Store Connect 应用记录，并在 EAS 中配置团队签名凭据；不在仓库中保存私钥、服务账号 JSON 或令牌。完成后执行 `pnpm dlx eas-cli@latest build --profile production --platform ios`，通过 TestFlight 验收后再提交 App Review。

## 验收边界

- EAS 配置文件不等于已绑定 Expo 项目、构建成功、签名成功或商店上架。
- 正式 iOS 路线没有 7 天免费签名刷新；它依赖付费 Apple Developer Program 会员。当前账号/团队未配置，因此暂不能产出可供 TestFlight 安装的签名包。
- 本机曾用已缓存的 `pnpm dlx eas-cli@latest whoami` 做只读查询，返回 `Not logged in`。该查询不创建 EAS 项目；项目所有者登录后再执行 `project:init`。
- 生产构建前仍须完成 iPhone/Android 真机安装、局域网配对、权限、后台/切网恢复验收。
- 商店提交必须核对应用版本、隐私说明、截图、支持网址、分级与审核资料；公开发布后再从商店链接安装回读。
