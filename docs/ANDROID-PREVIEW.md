# 影序 Pocket · Android 预览包

Android 预览 APK 由 [`.github/workflows/android-release.yml`](../.github/workflows/android-release.yml) 用 Expo `assembleRelease` 构建，内嵌 JS bundle，安装后不需要 Metro 开发服务器。

- 版本：1.0.0（versionCode 1）
- 包名：`com.yingxuapp.pocket`
- ABI：arm64-v8a / armeabi-v7a / x86 / x86_64
- 签名：debug 签名（不是商店包，没有生产签名）
- 状态：**未做真机验收**，仅本机（vivo V2405A / Android 16）冷启动验证通过

## 现在去哪拿 APK

预览包**不再提交到仓库**。92 MB 的二进制放在 git 里，会让每次 clone 都变大，而且 `dist/` 本来就是 CI 的输出目录（已在 `.gitignore` 里）。

两种拿法：

1. 在 Actions 里跑 `Android preview release` 工作流，下载名为 `android-preview-release` 的 artifact。
2. 需要长期分发时，把它作为 **pre-release** 的附件上传，而不是塞回仓库：

```bash
gh release create android-preview-1.0.0 \
  --prerelease \
  --title "Android 预览包 1.0.0（未验收）" \
  --notes "内部预览，debug 签名，未做真机验收，不作正式分发。" \
  ./yingxu-pocket-android-preview-1.0.0.apk
```

## 安装

```bash
adb install -r yingxu-pocket-android-preview-1.0.0.apk
```

或在手机浏览器打开 Release 附件链接直接下载（需允许安装未知来源应用）。

## 注意

- 这是预览包，不是 Google Play 包，也没有生产签名。
- 未经项目所有者批准，不应作为正式发行版本分发。
- 没有 Android 测试机，真机安装验收一直处于“暂缓”状态，别在官网写成可用。
