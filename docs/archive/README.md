# 历史快照去哪了

整理仓库时，从当前版本移出了两类过程文件：

| 移出的目录 | 内容 | 数量 |
| --- | --- | --- |
| `docs/snapshots/` | 每次 AI 工作会话改动前的文件副本（`*.before-*`、整份旧文档、旧 workflow） | 67 个目录 / 226 个文件 |
| `docs/site-history/` | 官网改版前的 HTML 副本 | 5 个目录 / 15 个文件 |

一共移除 241 个文件、约 5.5 MB，其中 170 个是 `*.before*` 备份残留。

## 为什么移出

这些文件是“改之前先存一份”的保险，不是给读者看的产品文档。留在 `docs/` 里的结果是：仓库首页面点进 docs 看到 67 个 `2026-10-xx-xxx` 目录，真正要读的架构说明被淹没；搜索也会被一堆同名旧版本干扰。

移出不等于销毁：**它们仍然完整保存在 git 历史里**，`git checkout` 一条命令就能拿回来。

## 怎么找回来

```bash
# 看这些目录最后的提交
git log --oneline -- docs/snapshots | head

# 找删除这次整理的提交，把它之前的状态恢复出来
git log --diff-filter=D --oneline -- docs/snapshots | head -1
git restore --source=<那个提交>^ -- docs/snapshots

# 或者只看某一个快照里的某一个文件
git show <提交>:docs/snapshots/2026-10-20-windows-e2e-ci/build-windows.yml.before
```

恢复之后如果不打算提交，记得别 `git add` 它们。

## 以后怎么留证据

需要保留“改前状态”时，改为在 `docs/reports/` 写一份记录，正文里写清楚：

- 改了什么（文件 + 关键 diff 摘要）；
- 改前是什么行为、改后是什么行为；
- 怎么验证的（命令、run id、产物哈希）。

旧文件的完整内容交给 git 历史，不要往仓库里复制第三份。

> 注意：`docs/reports/cross-platform-audit-*.md`、`docs/reports/closure-plan-*.md` 等历史记录里仍然写着 `docs/snapshots/...` 这类路径，那是当时的真实路径，按上面的方法可以找回，别再据它找当前文件。
