# 影序 Pocket · Android 预览包

这是由 `android-release.yml`（Expo `assembleRelease`）构建的 Android 预览 APK，内嵌 JS bundle，安装后无需 Metro 开发服务器即可运行。

- 版本：1.0.0（versionCode 1）
- 包名：`com.yingxuapp.pocket`
- ABI：arm64-v8a / armeabi-v7a / x86 / x86_64
- 签名：debug 签名（非商店包，非生产签名）
- 状态：**未做真机验收**，仅本机（vivo V2405A / Android 16）冷启动验证通过
- 校验：见同目录 `.sha256` 文件

## 安装

```
adb install -r yingxu-pocket-android-preview-1.0.0.apk
```

或在手机浏览器打开本文件原始链接直接下载安装（需允许安装未知来源应用）。

## 注意

- 这是预览包，不是 Google Play 商店包，也没有生产签名。
- 未经项目所有者批准，不应作为正式发行版本分发。
