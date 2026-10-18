# 回到 iOS 正式发行路线：变更前快照

- 基线提交：`988741226dd0fe51940d46d9ae1ebfacba3c4be5`
- 目的：保留撤销临时 unsigned IPA / AltStore 侧载候选前的源文件，以便审阅或回滚。
- `mobile.yml.before`：包含 `ios-device-unsigned` 候选 job。
- `MOBILE-STORE-RELEASE.md.before`：包含该候选 job 和 AltStore 侧载说明。
- 本快照不是当前发行配置；正式发行继续使用 EAS `production` profile。
