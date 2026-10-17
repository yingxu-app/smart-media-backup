# 影序 Pocket 移动端构建与商店交付

`mobile/eas.json` 保存 Expo Application Services（EAS）的可复用构建档案：

| 档案 | 用途 | 输出 |
| --- | --- | --- |
| `development` | 原生开发客户端 | 内部分发；依赖 `expo-dev-client` |
| `preview` | Android 设备安装与验收 | 内部分发 APK |
| `production` | 商店候选 | Android AAB；iOS 默认生成商店发行构建 |

提交档案目前只指定 Google Play 内部测试轨道。iOS App Store Connect App ID、开发者团队、Apple 签名、Google Play 服务账号、EAS 项目 ID 均未配置；不得把当前 CI debug APK 或模拟器 App 当作商店包。

## 账号绑定后执行

在项目所有者控制的终端登录 Expo 并绑定 EAS 项目，使用官方 CLI 将项目 ID 写入 `mobile/app.json` 的 `expo.extra.eas.projectId`。然后按需执行：

```sh
cd mobile
npx eas-cli build --profile development --platform all
npx eas-cli build --profile preview --platform android
npx eas-cli build --profile production --platform all
```

完成 Apple / Google 商店凭据与应用记录设置后，才可提交商店审核。Android 内测提交可使用：

```sh
npx eas-cli submit --profile production --platform android
```

首次提交前须在 Play Console 确认包名 `com.yingxuapp.pocket` 已由目标发行账号持有，并确保 EAS 上传的 AAB 与商店应用记录匹配。iOS 需先取得实际 App Store Connect App ID 和团队配置；不在仓库中保存私钥、服务账号 JSON 或令牌。

## 验收边界

- EAS 配置文件不等于已绑定 Expo 项目、构建成功、签名成功或商店上架。
- 生产构建前仍须完成 iPhone/Android 真机安装、局域网配对、权限、后台/切网恢复验收。
- 商店提交必须核对应用版本、隐私说明、截图、支持网址、分级与审核资料；公开发布后再从商店链接安装回读。
