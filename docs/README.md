# 文档地图

仓库里的文档按“读者要用它做什么”分四类，不要在一堆验收记录里找使用说明。

## 想用起来

| 想知道 | 去哪 |
| --- | --- |
| 这是个什么工具、怎么备份 | [../README.md](../README.md) |
| 手机怎么连电脑看进度 | [POCKET.md](POCKET.md) |
| AI 命名 / 废片建议怎么配 | [AI-MODEL-SETUP.md](AI-MODEL-SETUP.md)、[AI-SAFETY.md](AI-SAFETY.md) |
| 隐私与数据去了哪 | [../PRIVACY.md](../PRIVACY.md) |

## 想看懂实现

| 想知道 | 去哪 |
| --- | --- |
| 模块划分与数据流 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 手机原生备份（Android/iOS 壳） | [NATIVE-MOBILE-BACKUP.md](NATIVE-MOBILE-BACKUP.md) |
| 微信小程序局域网协议 | [MINIPROGRAM-ARCHITECTURE.md](MINIPROGRAM-ARCHITECTURE.md) |
| 官网怎么发布 | [WEBSITE-HOSTING.md](WEBSITE-HOSTING.md) |
| 上架与签名边界 | [MOBILE-STORE-RELEASE.md](MOBILE-STORE-RELEASE.md) |

## 想验收

| 想知道 | 去哪 |
| --- | --- |
| 每个版本改了什么、验收到哪一步 | [releases/](releases/) |
| 端到端回归覆盖了哪些场景 | [TEST-MATRIX.md](TEST-MATRIX.md) |
| 用户实际怎么走这条路 | [USER-JOURNEY.md](USER-JOURNEY.md) |
| 跨平台审计与全端闭环计划 | [reports/](reports/) |

## 想参赛 / 演示

| 想知道 | 去哪 |
| --- | --- |
| 比赛材料 | [product/competition-case.md](product/competition-case.md) |
| 提交清单 | [product/competition-submission-checklist.md](product/competition-submission-checklist.md) |
| 演示视频脚本 | [product/demo-video-script.md](product/demo-video-script.md) |

## 目录约定

```text
docs/
├── README.md            本文件
├── ARCHITECTURE.md      架构
├── POCKET.md            Pocket 使用说明
├── ...
├── releases/            每个版本的发布/候选验收记录（v1.0.24 → v1.0.40）
├── reports/             跨端审计、闭环计划、验收过程记录（体量大，按需读）
├── product/             比赛、演示、就绪度评估
└── archive/             历史快照的归档说明
```

写文档的约定：

- 文件名用小写短横线：`pocket-live-progress-acceptance-2026-10-18.md`。
- 发布记录一律进 `releases/`，按版本号命名。
- 一次性的调试记录、改前备份不要进仓库；需要留证据就写进 `reports/` 的一份记录里。
- 新增或移动文档后跑 `python3 scripts/check_links.py`，它会把断掉的相对链接指出来。
