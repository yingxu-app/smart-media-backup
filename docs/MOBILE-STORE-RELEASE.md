# 影序 Pocket 移动端构建与商店交付

`mobile/eas.json` 保存 Expo Application Services（EAS）的可复用构建档案：

| 档案 | 用途 | 输出 |
| --- | --- | --- |
| `development` | 原生开发客户端 | 内部分发；依赖 `expo-dev-client` |
| `preview` | Android 内部预览 | 内部分发 APK |
| `production` | Android 商店候选 | Android AAB |

iOS 按用户最新决定仅维护 Safari PWA，不开发 iOS 原生 App，也不做 TestFlight/App Store 发行。当前 PWA 通过桌面端局域网服务连接；若桌面服务关闭，联网功能不可用。局域网 HTTP 下离线 Service Worker 缓存不可用，离线 app shell 尚未验收。

EAS 项目已绑定到 Expo 账号 `nanyu-lu`；Android preview APK 已构建并校验，但用户暂时没有 Android 测试设备，因此不做真机验收。Google Play 服务账号和生产发行配置仍未配置。不得把当前 CI debug APK 或 EAS preview APK 当作商店包。

## EAS 项目已绑定；后续构建与发行

EAS 项目为 [`@nanyu-lu/yingxu-pocket`](https://expo.dev/accounts/nanyu-lu/projects/yingxu-pocket)，ID `e83a97a0-f588-4068-a66d-f3e38782bcc1`，已写入 `mobile/app.json`。本仓库使用 pnpm；构建命令统一使用 `pnpm dlx`：

```sh
cd mobile
pnpm dlx eas-cli@latest account:login
pnpm dlx eas-cli@latest account:view
pnpm dlx eas-cli@latest build --profile development --platform android
pnpm dlx eas-cli@latest build --profile preview --platform android
pnpm dlx eas-cli@latest build --profile production --platform android
```

完成 Google Play 凭据与应用记录设置并具备设备验收条件后，才可提交商店审核。Android 内测提交可使用：

```sh
pnpm dlx eas-cli@latest submit --profile production --platform android
```

首次提交前须在 Play Console 确认包名 `com.yingxuapp.pocket` 已由目标发行账号持有，并确保 EAS 上传的 AAB 与商店应用记录匹配；不在仓库中保存服务账号 JSON 或令牌。

## 验收边界

- EAS 配置文件不等于已绑定 Expo 项目、构建成功、签名成功或商店上架。
- iOS 原生构建与 Apple 签名已按用户决定移出当前范围，采用 Safari PWA。
- 历史上曾有一次 Expo CLI `whoami` 返回 `Not logged in`；该状态已由后续项目所有者 OAuth 登录解决。EAS 项目和构建已实证成功，见下方记录。
- iPhone 侧仅验收 Safari PWA：主屏幕启动、刷新、桌面 LAN 服务重连和后台恢复。Android 真机验收暂缓，待有设备后再安排。
- 商店提交必须核对应用版本、隐私说明、截图、支持网址、分级与审核资料；公开发布后再从商店链接安装回读。

## 2026-10-19 EAS Android preview 构建记录

- EAS Android preview build `2926409f-7f75-454f-91a8-37ebf4dc2a66` 已完成（`FINISHED`）；构建详情：[Expo build](https://expo.dev/accounts/nanyu-lu/projects/yingxu-pocket/builds/2926409f-7f75-454f-91a8-37ebf4dc2a66)。profile `preview`，app version `1.0.0` / build `1`，包名 `com.yingxuapp.pocket`，来源提交 `2b1c89b`。
- APK 已下载到本机并完成 SHA-256 与 ZIP 完整性核验：`/Users/nanyu/Downloads/影序Pocket-Android-preview-1.0.0-build1.apk`，92,264,537 bytes，SHA-256 `9783f71f24c0105d8d22457e8f7715fbe2d61d6599d63ba578730f3e7b1cba64`；APK ZIP 测试通过，包含 `arm64-v8a`、`armeabi-v7a`、`x86`、`x86_64`，二进制 Manifest 中可见包名。此为内部 preview 构建，尚无 Android 真机安装验收；本地计算的 SHA-256 不是 Expo 发布的独立校验和。
- 同提交 GitHub Actions Pocket run `39205982845` 成功，JS/CNG/check、Android debug 和 iOS Simulator jobs 均成功；Actions 仅提供 Android debug artifact，没有 iOS Simulator app artifact 或 IPA。
- iOS Simulator job 仅是历史 CI 产物验证，与当前 PWA 交付选择无关；Android preview APK 尚未真机安装。
