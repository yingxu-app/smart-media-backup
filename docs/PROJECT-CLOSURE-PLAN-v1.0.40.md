# 影序全端闭环计划 v1.0.40

核对日期：2026-10-21。下方历史记录保留当时证据；当前范围与状态以本节为准。此计划把“功能完成、平台验证、部署、公开发行”拆开记录；CI、模拟环境或候选包不能代替实机和线上验收。



## 2026-10-21 合并后权威检查点

- **主线与 PR：**PR #9、#10 均已合并。main 当前为 `8cf922635dd9b7b860e56da21982ef1909ef95a4`。本地已合并功能分支 HEAD `674cbf281c9841388da0605b4861c7e422219dd4` 与 main 文件树一致。
- **合并后 CI：**Pocket run `39495319370` 终态 success，PWA job 与 Android debug APK build 成功；Reliability run `39495319472` 六个 OS/Python 组合全成功；Windows preview `39495319292` 与 Pages deploy `39495319529` success。Dependabot dynamic run `39495338732` 因 `/mobile` 的 uuid 更新检查失败，单独跟踪，不代表产品构建或 Pocket 失败。
- **Windows x64 VM：**Windows-hosted runner 对打包 EXE 执行模拟素材卡备份，21/21 项通过，覆盖扫描、复制、SHA-256、历史/报告、重复跳过和来源保护。该证据不是实体 Windows 测试；仍需补虚拟机图形界面中的解压/启动、升级与回退流程。按用户决策不安排 Windows 实体机测试。
- **Pages：**首页、`/pocket/`、`/download/`、`/privacy.html`、`/update/` 目前全部 HTTP 200；线上更新说明已显示校验、手动安装和回退步骤。路由可访问不代表 iPhone 离线或媒体传输已验收。
- **Firebase 只读健康探测：**虚构 `example.invalid` 邮箱的 sign-in 请求返回 `INVALID_LOGIN_CREDENTIALS`，证明 Auth Web API 与邮箱/密码入口可响应；未认证的 RTDB 用户路径请求返回 HTTP 401 `Permission denied`。没有创建账号或使用真实密码，因此真实账号登录、多端同步和 UID 隔离仍待实测。
- **Draft 资产整理：**v1.0.40 仍为 Draft，target 为合并 main。macOS DMG SHA-256 `65a22d7c0671f98362e5888cf10c02f0783b2d1ced9967d4779a2dae5e79d18e`、Windows EXE SHA-256 `257b461d2aa1cb6e5b1b6eda2c9b9f0e1d54046d65eed125dbb42043e8787e1a`；移除了与候选包不匹配的旧 `SHA256SUMS.txt`，当前 Release 正文指向版本化清单 `YINGXU-v1.0.40-SHA256SUMS.txt`（SHA-256 `31882371dd6110fc4af0c97af4db090acdfa4750d94cf00e38a72443e6269637`）。公开 Latest 与下载页版本仍为 v1.0.34，未提前发布。
- **待完成门槛：**用真实账号完成注册/用户名、登录、同账号进度与云端历史、账号隔离和断网恢复；iPhone Safari PWA 选取照片/视频传至已配对桌面并核对桌面哈希与历史，验证离线缓存/联网恢复；Windows x64 VM 补图形界面运行、升级/回退。真实 iPhone/PWA 与 Firebase 证明前，v1.0.40 继续保持 Draft。
- **PWA 能力边界：**当前手机端可选择照片、RAW、视频或 Files 项目，经同 Wi‑Fi 配对上传至桌面。它不提供完整原生相册静默扫描、锁屏持续传输、离线期间桌面队列续传、任意手机目录写入或异地原始媒体云备份；这些不得写成已完成能力。iOS 原生、Android 真机、小程序、代码签名/公证均在用户排除范围之外。

## 2026-10-21 当前推进与结束门槛

- **平台范围修正：**Windows 验收使用 x64 虚拟机；GitHub `windows-latest` runner 属于虚拟机验收证据，不要求实体 Windows 电脑。iOS 仅交付 Safari PWA；Android 真机暂缓；不开发小程序、原生 iOS 或 Android 商店版。macOS/Windows 代码签名与公证按用户决定排除。
- **PR 状态基线：**PR #10 已于 2026-10-21 通过 squash 合并，main merge commit `6b042d033e3b985399574c8de77ec4073f5c4733`；其 Windows x64 runner E2E / Reliability checks 均通过。PR #9（`codex/iphone-pwa-offline-checkpoint`）仍 OPEN/DRAFT，当前产品提交 `c8d2e7f`，新 head checks 正在运行。虚拟机 E2E 是隔离目录下的打包服务/备份检查，不代表手机设备、物理读卡器或 Windows 用户桌面 GUI 安装验收。
- **本轮源码变更：**桌面局域网 `/pocket/` 新增配对后的手机媒体上传 API 和选择/扫描/传输界面：从照片或 Files 选择照片、RAW、视频；填归档名；增量 SHA‑256 扫描；对本批相同内容去重；预检查目标磁盘可用空间；512 KiB 分块上传；可以暂停/取消；桌面重验 SHA‑256、清理失败临时文件，并写入桌面历史/同步账号元数据。桌面偏好设置每 3 秒读取一次手机上传进度。
- **PWA 的设备边界：**HTTPS PWA 继续缓存页面和云端历史；明确说明在线原件传输需要打开附近电脑的局域网页面。iOS Safari 18.4+ 支持页面选择 Files 目录；早期版本可通过多文件选择器逐项授权。浏览器无法静默读取整张相册或外接盘、向任意本机目录写入，且锁屏/切换应用可能暂停。代码目前实现“选定素材→同 Wi‑Fi 传到电脑”，不是手机任意目标盘/后台无中断/电脑离线排队。
- **更新功能改动：**偏好设置现在可下载最新适用平台发行文件；桌面端先按 GitHub Release 的 SHA‑256 metadata（metadata 缺失时使用同版 SHA256SUMS）校验完整下载，校验失败不提供文件。当前仍要用户手动安装/替换并保留旧版，不能静默覆盖运行中的 App。
- **更新页线上核查：**2026-10-21 使用仓库 `.venv` 的 certifi CA bundle 复核规范 Pages 首页、`/pocket/`、`/download/`、`/privacy.html`、`/update/` 均 HTTP 200；线上 `/update/` 标题和手动安装说明可读。此前 TLS EOF 是系统 Python 证书链不全导致的检查环境差异，不能称为线上路由故障。此次代码中的新版页面尚待合并部署。
- **发布基准：**正式 GitHub Latest Release 仍为 `v1.0.34`，Windows EXE 和 SHA256SUMS 有公开 digest；v1.0.40 仍为草稿候选。新增代码没有对应候选安装包或正式发行，不得提前更新下载页版本号。
- **当前验证进度：**手机上传 API、安全配对、哈希通过/失败、历史落库和权限拒绝定向测试已新增；增量 SHA‑256 跨块/边界测试已新增。更新下载校验成功/失败测试已新增。本轮本机全量 Python 回归为 121 项、119 通过、2 项 Windows 条件跳过；手机上传/协议/更新定向组 24 项通过；Pocket 云同步与 SHA‑256 Node 测试合计 10 项通过，内嵌局域网页面脚本语法检查与 `git diff --check` 通过。新代码的 GitHub CI、Pages 部署及 iPhone 真机上传流程尚未完成。
- **真实用户门槛：**仍需在 iPhone Safari 用一张照片和一段视频走完整扫描→传输→桌面校验→历史流程，并验证暂停/恢复、断网重连及锁屏恢复；登录真实 Firebase 账号验证同步/UID 隔离的任务仍由用户在本机输入凭据后完成，不得复用聊天密码。Android 真机、Windows 实体机均不列入验收条件。
- **有限结束条件：**PR #9 checks 通过后按授权合并；Windows x64 虚拟机 E2E 在包含新代码的 main head 通过；新 Pages 首页/Pocket/下载/隐私/更新路由部署并 HTTP 200；桌面候选与 Release 资产 SHA‑256 对齐；升级和回退步骤可读。iPhone PWA 与 Firebase 真实账户项若仍只需用户在设备/应用内操作，则完成其余独立工作后输出唯一明确步骤，保持目标未完成，不以 CI 或发布状态冒充全端验收。PWA 仍不承诺锁屏持续传输或离线期间后台排队；这受浏览器权限和执行限制，需保持为明确的平台边界。

## 2026-10-20 新增 Windows runner 功能验收

- PR #10 head `eb079c9353312f27fc22c91f16e11be95d59f42d` 的 Windows preview run `39445925130` 与 Reliability run `39445924653` 均 success。
- Windows runner 在临时目录中用合成来源卡完成 20 项检查：扫描、无效来源拒绝、复制、SHA-256、照片/视频分类、缩略图树、增量跳过、历史/报告导出及来源不变；Windows reliability suite 通过。x64 PE、未签名状态、SHA-256 清单读回与构建 artifact 上传也通过。
- Windows EXE artifact `12276881124` metadata digest `sha256:60626be7ff1202bd7d779516ecb7382ebdc6f032f5bba0a84910eff0089cb9da`；E2E JSON 报告 artifact `12275642204` metadata digest `sha256:43767f6cee57f34c02dc2840760a18fccd5849e3dfa5450f001d40e017131ced`。此处是 GitHub-hosted Windows runner 的合成文件系统功能检查，不是用户 Windows PC、真实读卡器或打包 GUI 安装验收；Windows 实机门槛仍开放。
- E2E 脚本修正为从自身文件位置定位仓库，并将用户配置、模拟来源、备份目标与报告全部放入临时目录；改前快照保存在 `docs/snapshots/2026-10-20-windows-e2e-ci/`。

## 2026-10-20 当前目标范围与权威状态

- **范围决定：**iPhone 交付为 Safari PWA；不开发原生 iOS。Android 真机验收暂缓（用户没有 Android 设备），Android CI/debug artifact 仍保留为构建证据。停止小程序开发，不纳入活跃发布门禁。异地原始媒体上传/下载和浏览器在线备份不在本阶段。
- **发行决定：**用户明确不做 macOS/Windows 身份代码签名与公证。未签名发行候选可继续准备；必须在官网和安装说明中如实提示系统安全警告。不得把签名/公证列为本阶段完成门槛。
- **仓库与合并：**当前主线已包含 PR #4（merge `40cb4dfe82e6917fe0d404b5d5a9eb8be8a7f005`）及 PR #7（merge `9281242accbb6e66db51fa36ff96594109d93f1d`）。PR #4 的更新检查 TLS CA bundle 修复和 PWA/Firebase 实现已进入 main；PR #7 将首页状态改为 HTTPS PWA 已上线。工作分支 `codex/pwa-live-status` 的文档提交 `6eccc2f` 已合入 PR #7。
- **线上站点：**2026-10-20 本机 `curl` 检查规范 Pages `/pocket/` 与 `/download/` 均返回 HTTP 200；Pages 部署 run `39307408371` success。PWA 线上可访问，不等于 Firebase 真实登录、iPhone 主屏幕安装或离线恢复已验收。
- **浏览器回读：**Codex 浏览器实际打开线上 `/pocket/`，页面标题为“影序 Pocket — 手机协作台”，出现登录/注册、用户名、附近电脑入口和“离线页面缓存已启用”说明；该提示不等于断网启动实测。线上 `/update/` 实际渲染了检查更新、SHA-256 校验、安装和旧版本/数据回退步骤；未执行真实版本升级或回退。
- **公开版本：**GitHub Latest Release 当前实查仍为 `v1.0.34`，仅有 Windows EXE 和 `SHA256SUMS.txt`；下载页也仍展示 Windows v1.0.34。v1.0.40 仍是候选，不能描述为已公开发行。
- **v1.0.40 候选重核：**macOS artifact `12212088920`（metadata 21,081,542 bytes，SHA-256 `c6927a1b5b4755fbba5a62e88b8ffcda0291401a7117dea44e0914315d40ccff`）；内含 DMG SHA-256 `01249b61e141e142b3c4c4be5b9befea84b831c34bab1ea605a007b5c67e34a7`，清单匹配、`hdiutil verify` 为 VALID，arm64 app `codesign --verify --deep --strict` 通过且签名为 ad-hoc、无 Team ID。Windows artifact `12211509463`（metadata 27,876,758 bytes，SHA-256 `adcfb123859b7e5049ae9d241dd72b54de8be5538ac3ae06741930e7d47e29d9`）；EXE SHA-256 `40dfe06ec15f7e635d633bd3bceee79b912c7b14c4c7fb66a15e928fe1e77a72` 与随包清单匹配，文件为 PE32+ x86-64。两者来自产品代码提交 `f60055b` 的候选构建，未做 Windows 真机验收，也不是公开 Release。
- **当前 CI：**主线合并后的 Reliability run `39307408377` success。Pocket run `39306460382` 后续终态为 success（`updated_at=2026-10-19T19:18:16Z`）；Pocket JS/CNG job 与 Android debug job 均 success。Android artifact `12214489435` metadata 为 94,609,048 bytes、SHA-256 `bb967626196499f628714b5bd03eafa3d17020ef04dd03954cc5182902680958`；本机下载 ZIP 摘要相符。内含 APK 269,595,675 bytes，SHA-256 `93619fd0db5fe982997adc714dce5dcff4a80abef53353736c1f9314e9b44221`，ZIP 完整，包含 arm64-v8a、armeabi-v7a、x86、x86_64。它是 debug APK，不是 Android 真机验收或公开安装包。run 只观察至终态，未重启。
- **Firebase 安全诊断：**当前桌面 `/api/firebase/settings` 返回 `configured=true`、`signed_in=false`。使用仓库公开 Web 配置发起的无副作用 Auth 登录探针：格式无效邮箱返回 `HTTP 400 INVALID_EMAIL`；格式有效的虚构邮箱返回 `HTTP 400 INVALID_LOGIN_CREDENTIALS`。RTDB 匿名根读取返回 `HTTP 401`。这证明 Auth endpoint/API key 可响应、匿名数据库访问被拒绝；不证明用户账号密码、注册、云同步或 Safari 的真实登录成功。
- **本轮代码进展：**桌面 Firebase 登录此前对未分类的本机异常返回通用提示；现在响应中只显示安全的异常类型，不返回底层异常详情、密码或请求 URL。Firebase server 定向测试 8/8 通过，`git diff --check` 通过；当前改动尚未提交、尚未进入 CI 或公开应用包。
- **仍待证实：**由用户在本机输入凭据后验证 Firebase 注册/登录、用户名、桌面与 PWA 实时进度及云历史、UID 隔离、断网恢复；iPhone Safari 主屏幕安装、PWA 离线缓存/恢复和网络重连；Windows 真机安装及核心备份、失败恢复、升级回退；之后更新正式 Release、下载页与回滚说明并从公开链接回读验证。
- **有限结束条件：**范围内每项交付都要有源码/CI/线上或设备证据；正式 Release 与下载说明一致，安装包及校验文件可回读，升级/回退路径有证据。若只剩用户凭据输入或设备操作，完成可独立工作后提供一条明确步骤并保持目标未完成。明确排除的签名/公证、原生 iOS、Android 真机、小程序、异地原片传输不作为阻塞项。

## 2026-10-20 PR #8 终态与未完成验收

- 当前 PR #8 head `4478ff024fe37565c1c5adb8882da566068c8c56` 的 Reliability push/PR、macOS、Windows 和 Pocket workflows 均 success；Pocket Android debug artifact `12219107452` 已下载并核对 metadata、ZIP 与 APK SHA-256、ZIP 完整性和四种 ABI。此证据只到构建包，不代表 Android 实机验收。
- 规范 GitHub Pages 首页、下载、隐私、PWA 与更新说明路由当前均 HTTP 200。PWA 离线 shell 与 standalone manifest 在线可读；iPhone 主屏幕安装、离线启动和恢复仍需真机验证。
- Codex in-app browser 的 Firebase 登录请求只得到浏览器 `TypeError`/网络错误，没有 Auth 错误码；无凭据 CORS preflight 从主机端返回 200。真实登录、用户名、多端历史/进度、UID 隔离及离线恢复仍未验证。
- 本机旧桌面服务的 `/api/updates/latest` 仍返回 502；PR #8 更新诊断代码的定向测试通过，但新包尚未替换运行实例。GitHub Latest Release 与下载页仍为 Windows v1.0.34；新正式版、公开下载、升级和回退仍未完成。
- 下一步先继续完成候选/PR 收尾和更新包验证，再在用户设备上完成 Firebase 登录与 iPhone PWA、Windows 真机流程。遇到需要 iPhone/Safari 或 Windows 设备的门槛时，先完成其他独立工作，再给用户单一步骤。签名/公证不属于结束条件。

以下内容是 2026-10-19 及更早的历史证据快照；其中未完成事项和平台范围可能已被本节后续决定取代。

## 2026-10-19 当前 head 候选交付

- 产品代码候选 head 是 `9d04a5e2354988ded5dab3ce1aa69c9d3dcd2851`。只更新证据与快照的后继 head `a86b28afe50fb26f86fa6f1e7e612d4d0550c44d` 当前位于 PR #4；PR OPEN/DRAFT、mergeable，工作树 clean，后继提交未改产品源码。
- Reliability PR `39188941105`、push `39188938449`、macOS `39188941117`、Windows `39188941135`、Pocket `39188941122` 均 success；Pocket JS/CNG、Android debug、iOS Simulator 全通过。iOS Simulator job 不产出 IPA。
- 文档后继 head `a86b28a` 的 PR Reliability `39197816737`、push Reliability `39197812330`、macOS `39197816836`、Windows `39197816796`、Pocket `39197816810` 均 success。下面的本机包体逐项校验仍指向产品代码候选 `9d04a5e` 的下载 artifact，不等同于核验 `a86b28a` 新生成的包体。
- macOS artifact `12159535671`（21,078,353 bytes；metadata SHA-256 `17f5e0804e2a34135e20085325ed8db24fa9f5f4745ba3ae7c61ec831dd1f221`）。内含 DMG SHA-256 `89eef56bebafa483d65c5a4e54c7d93ed1e6a04337798e9273c0a57f45f1caf7`，清单一致、hdiutil VALID；arm64 app deep/strict code verification 通过，但 ad-hoc、无 Team ID、未公证。
- Windows artifact `12159231755`（27,874,165 bytes；metadata SHA-256 `b12d22207311defe362acbf917bba43005a0f36ec793516994a5cc0a3dc590e6`）。内含 x86-64 PE EXE SHA-256 `79bce8d91a9a06c8d04dc763f58cda592dabaac9d30b5a736dabd83ea5e5a061`，与清单一致；未做 Windows 实机运行验收。
- Android artifact `12159314027`（94,608,820 bytes；ZIP SHA-256 `0ebeca6aef5b874e4e34e748018b12a1447eab17e6c52f6a85b8e84271c94fdd` 与 metadata 一致）。APK SHA-256 `a6aaa85668cd927b069b7e340083b7cd58167f94ec3746705a35077168609518`，269,595,547 bytes、四 ABI；属于 debug 包，未在实体手机安装。
- 最新公开 Release 仍为 `v1.0.34`，只有 Windows EXE 与校验文件。当前 CI 无小程序门禁。

## 阶段停止条件与外部交接

代码候选阶段以最新 PR checks 成功、候选证据和外部验收清单记录完毕、PR #4 保持 OPEN/DRAFT 为结束点；不把这一结束点称为产品发布或真机闭环。后续需要 owner/设备：iPhone、Android、Windows 实机验收；Firebase 同账号多端进度与历史、不同 UID 隔离和断网恢复；EAS 项目关联；各平台签名、公证/商店；正式 Release 下载、升级与回滚。

## 当前交付面与权威证据

| 交付面 | 当前实现 / 已有证据 | 当前状态 | 闭环门槛 |
| --- | --- | --- | --- |
| macOS 桌面 | PR head `4463789` candidate run `39039775174` success。artifact `12103985107` ZIP 20,953,575 bytes，SHA-256 `16b1a1deb3ab39d2933be1a6f6eb1b58a570e8bacb27d3108cecb76056176402` 与 GitHub metadata 一致；v1.0.40 DMG SHA-256 `3c7ecc95f05fbe00074802db6241f6d40c43fdcafcc300fe36d11d280f8cc24a` 与清单匹配且 `hdiutil verify` VALID。arm64 app deep/strict codesign 通过，但 ad-hoc、无 Team ID、未公证。同机隔离运行 health/database 正常、静态路由 HTTP 200。 | 当前 head 候选包和同机运行已核验；尚非 Developer ID 签名、公证、另一台 Mac 安装或公开发行。 | Developer ID 签名与公证；正式 Release、下载页及另一台 Mac 安装回读。 |
| Windows 桌面 | PR head `4463789` preview run `39039775172` success。artifact `12103003464` ZIP 27,494,145 bytes，SHA-256 `7ffa948bc366151d2238ec3991fe01044106b6c600048acd402c4038a19453d5` 与 metadata 一致；内含 x86-64 PE EXE SHA-256 `7836f032358e86e469e6086340dfff22420ff96bb3f150bf4feb9935591d49c7`，与包内清单一致。 | CI preview 与包体校验通过；仍无 Windows 真机安装、运行、Defender、读卡器或断盘恢复证据。 | 在真实 Windows PC 安装并逐项操作；测试 SD 卡、目标盘、恢复与升级；签名后发布正式安装包并从公开链接回读。 |
| 手机 PWA | 用户提供的 iPhone Safari 实机截图显示 Pocket 页面已加载，桌面显示已连接且安全配对，历史记录列表可见；同一时段 Mac `/api/pocket/status` 返回 `paired:true`、`idle`。 | iPhone 到桌面端的 LAN 页面与配对基础链路已验收。 | 验收实时状态刷新、拍摄信息/备注读写、主屏幕入口、后台/锁屏恢复、离线/切网/重连和撤销；HTTP LAN 下 Service Worker 离线能力仍不可用；Android 真机另行验收。 |
| 原生 iOS / Android | PR head `4463789` Pocket run `39039775166` 的 JS/CNG/check、Android debug 和 iOS Simulator 三 job 均 success。Android artifact `12103619468` ZIP 94,576,841 bytes，SHA-256 `70f4ac2efc655bc333dadcd979f58ab60f0b4333bca20c895fa70ad74d980f8d` 与 GitHub metadata 一致；内含 269,562,399-byte debug APK，SHA-256 `64d9481c6baa0c67d3e5e681cfd0f5a33dcd8e946c7137c3ec676b20f77fb1bf`，包含四种 ABI。未上传 iOS Simulator app/IPA。 | 当前 head 原生编译通过、Android debug APK 包体已核验；仍未签名、未在实体 iPhone/Android 安装，也无 LAN 授权或桌面 TCP 真机配对证据。 | 在真机完成安装、授权、配对、切网和重连；配置正式签名构建与商店资料，产出并检查签名 IPA/AAB、提审及上架。Expo SDK 58 默认 targetSdk 36；未来升到 targetSdk 37 时须处理 Android 17 的 `ACCESS_LOCAL_NETWORK` 运行时权限。 |
| 微信小程序 | `miniprogram/` 页面和 TCP 客户端已存在；桌面 TCP bridge 默认关闭，启用后监听 `18080`。本地 Node 测试现为 7 项通过，包含非法响应帧拒绝和切后台清理；脚本语法与配置 JSON 解析通过。 | 微信开发者工具 CLI 实际打开项目时因占位 AppID `touristappid` 返回 code 10“不存在此 AppID”，尚未进入编译；没有真实 AppID、真机或审核证据。当前源码路线为同一局域网直连，正式数据路径仍待确认。 | 配置真实 AppID 后完成开发者工具编译预览；确认正式连接架构；iPhone/Android 微信真机验收配对、前后台、切网、过期/撤销；补隐私指引并提交审核，核对线上版本。 |
| 官网与浏览器产品 | 主仓库 `site/` 规范 Pages URL `https://yingxu-app.github.io/smart-media-backup/`、`/download/`、`/privacy.html` 已用 Codex 浏览器实际打开并渲染；下载页仍显示正式 Windows v1.0.34。 | 规范站点路由可访问；浏览器在线备份范围未定义。 | 确认网页是否还需浏览器内导入/备份；若纳入在线备份，还需账户/数据/存储/隐私架构。 |
| 正式发布与售后回滚 | GitHub Latest Release 仍是 `v1.0.34`，资产只有 Windows EXE 与 `SHA256SUMS.txt`。PR #4 head `4463789` 的 Reliability PR `39039775211`、push `39039770286`、macOS `39039775174`、Windows `39039775172`、Pocket `39039775166` 均 success。 | v1.0.40 候选包和 debug/simulator build 不是多平台正式发行。 | 完成 Windows/mobile 真机验收和签名；准备隐私及商店资料；发布正式 Release、更新下载页，验证新用户下载、安装、升级与回滚。 |

## 共同完成门槛

1. **功能**：从“复制新内容”和“转移老内容”两条主流程逐项验收；转移包含废片、重复、分类命名、暂停/取消、校验失败保护与可恢复结果。
2. **数据安全**：原素材读写边界、重名不覆盖、哈希校验、拔盘/进程中断恢复、隐私最少化；任何删除来源动作都需在实际设备上验证。
3. **平台矩阵**：Windows、macOS、iPhone、Android、微信开发者工具和真机分别给出证据；平台间共享源码或 CI 绿灯不替代终端体验验证。
4. **部署/发行**：候选构建、签名包、商店审核、线上公开下载/安装、版本读回分别记录；一端上线不代表其他端完成。
5. **回滚**：每次正式替换保留旧安装包/版本和恢复说明；数据库升级需证明旧历史可读。

## 待用户一次性决定的范围

1. 手机端：是否同时交付 PWA 与原生 iOS/Android，还是 PWA 即为移动正式交付；若需原生上架，确认可接受的开发者账号/签名和商店资料准备。
2. 微信小程序：同一局域网 TCP（无云数据路径、仅本地网络）或微信云托管中继（可远程、需配置云环境）；也可分阶段支持两种路线。
3. 网页：只维护产品官网/下载站，还是增加浏览器在线备份产品；后者需重新定义文件访问、安全与浏览器兼容范围。

## 可并行推进

- 持续维护桌面主功能、测试与 Windows/macOS 候选证据；优先补 Windows 真机与现有 Pocket 真机网络验收。
- 复核正式网站与下载页，不把候选直接部署为正式下载。
- 不公开发布、不启用云付费服务、不索要任何账号密码或验证码；等架构决定后再开发依赖该决定的端侧集成。

## 2026-10-17 current verification checkpoint — PR head `9bbae70`

- Refreshed repository state: branch `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `9bbae707f51575a862693de4349b33de4135843d`, worktree clean. PR #4 is OPEN/DRAFT and mergeable.
- On this head, Reliability PR run `39015108813`, Reliability push run `39015105206`, macOS candidate `39015108870`, Windows preview `39015108802`, and Pocket run `39015108799` all completed successfully.
- macOS artifact `12094134210` ZIP SHA-256 `86473cfafdf3b7b347aa992d52da89f47cc78f8654546c4d945c6b9d95f8a846` matches GitHub metadata. Its v1.0.40 DMG SHA-256 `a88570c2c321948df22f73bac3830f26048dedab4a1c98a0e129f4402da7ff19` matches its manifest; `hdiutil verify` returned VALID. The app is arm64 and passes deep/strict codesign verification, but its ad-hoc signature has no Team ID and it is not notarized.
- Windows artifact `12093584501` ZIP SHA-256 `b5aeb2413f3524391c29a282c7687a85eec6c276549bce2d9e037b19cdd8a51a` matches GitHub metadata. The bundled x86-64 EXE SHA-256 `e90892aebfa686e1531ae1fadf77dab189c1a4710f89a61f19d30c640c609132` matches its manifest. The preview has not been installed on a Windows PC.
- Pocket run `39015108799` passed JS/CNG/check, Android debug and iOS Simulator builds. Artifact `12094239285` is an Android debug APK only; local SHA-256 `b9017bc68e8145e52855e03504c9fab4df9d0cdae2d8456d3cd7ec2256edd640`, ABIs arm64-v8a, armeabi-v7a, x86 and x86_64. No iOS Simulator app or IPA artifact was uploaded.
- Canonical Pages home, `/download/` and `/privacy.html` returned HTTP 200. One curl TLS error on privacy was followed by Python urllib HTTP 200. Latest Release remains `v1.0.34`, with only Windows EXE and `SHA256SUMS.txt`; the download page displays v1.0.34.
- **Historical open gates as of this checkpoint:** Windows/iPhone/Android real-device acceptance; Mini Program AppID/DevTools/preview/device review/submission; EAS owner login and project; formal platform signing, Apple notarization, store submission, public release and upgrade/rollback; user decision on browser online-backup scope. The scope was subsequently revised in the 2026-10-19 decision below: iOS native and Mini Program are out of scope, and Android device acceptance is deferred.

## Follow-up verification — docs head `7039ca8`, product source `9bbae70`

- Re-read the current checkout: branch `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `7039ca8f0b8c9ada22c0064db3353cce1d0f9f9c`. The delta from product-source head `9bbae70` is audit/closure documentation plus pre-edit snapshots only.
- Local regression on this checkout: Python unittest ran 82 cases, 80 passed and 2 Windows-only cases skipped; Mini Program Node tests passed 7/7; Pocket mobile Node tests passed 5/5; Expo lint and TypeScript no-emit typecheck both exited successfully. The desktop suite logged an expected offline Ollama connection-refused diagnostic while returning exit code 0.
- The macOS v1.0.40 CI candidate from artifact `12094134210` was launched from its read-only DMG with an isolated config and port 18184. Health/database were OK, version 1.0.40 and idle; loopback desktop/Pocket routes returned 200. LAN `/api/status` returned 403 and unpaired LAN `/api/pocket/status` returned 401. TCP bridge was disabled and port 18080 had no listener. No media was copied or deleted; the process was stopped, port 18184 was released, and the DMG was detached. This is same-Mac runtime evidence only.
- Live GitHub check found a new Pocket run `39033010125` for docs head `7039ca8`: Pocket JS/CNG/check job passed, while Android debug APK and iOS Simulator build jobs remained in progress at the last poll. Do not rerun it; record terminal results only after polling this same run.
- Public status recheck: canonical Pages home and `/download/` returned HTTP 200. `curl` failed TLS on `/privacy.html`; system `/usr/bin/python3` urllib then returned HTTP 200. GitHub Latest Release API reports `v1.0.34`, published 2026-09-12, with only `YINGXU-Windows-v1.0.34.exe` and `SHA256SUMS.txt`.
- Product source remains unchanged. Real-device, WeChat AppID/DevTools/review, EAS owner project/login, signed/notarized packages, store submission, public release/upgrade/rollback, and the browser online-backup scope are still open.

## Correction: Pocket run `39033010125` terminal result

- Re-polled the same run; it completed successfully. Pocket JS/CNG/check job `117397111823`, iOS Simulator build job `117397111736`, and Android debug build job `117397111886` all concluded success.
- The run uploaded Android artifact `12101672408` only (94,576,872-byte ZIP, SHA-256 `0f7ed3e140bc921d6e31bb73d5895ede95692d0e27c399f6e89c63cce220e3a8`). The locally downloaded ZIP hash matches the GitHub artifact metadata.
- ZIP contains `app-debug.apk` (269,562,399 bytes; SHA-256 `15074a39103722de72c66e7102df01bb4ab65023f9946032ce7c66024379d703`) with `arm64-v8a`, `armeabi-v7a`, `x86`, and `x86_64` native libraries. This remains an unsigned debug APK, not device or store acceptance.
- No iOS Simulator app or IPA artifact was uploaded. Simulator build success does not prove iPhone installation or App Store signing.

## PWA 安全上下文依据

- [MDN Secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts) 说明普通安全上下文需 HTTPS；`localhost`/loopback 是开发例外，局域网 IP 不因此自动获得例外。
- [MDN Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) 说明 Service Worker 仅在 secure context 可用。当前 Pocket 通过 `http://<桌面局域网 IP>:8080/pocket/` 配对；在未完成真实 iPhone/Android 验证前，离线缓存和主屏幕体验均保持未验收。

## 2026-10-17 配对地址修复后的当前进度

Pocket 配对地址误选 VPN 已在 PR #4 head `d223dfe` 修正：本机 `_local_ip()` 返回活动 Wi-Fi 地址 `192.168.31.172`，接口级、配对 API、桌面全套、移动端和小程序自动检查通过。新 head 的 Pocket、macOS candidate 与 Windows preview 仍待 CI 终态；因此尚不能安装新候选做真实 iPhone/Android 局域网配对。旧 head `5d17e14` 的 iOS Simulator 与 Android debug 构建仍在运行，完成后可作为该旧 head 的构建证据，不能替代新 head 检查。

下一步按顺序：读取新 head 三条 CI 终态；检查新 macOS/Windows 候选并保留可回滚安装版本；在同 Wi-Fi 手机验证 Pocket 页面、配对、状态/历史/备注、锁屏/切网恢复；对原生客户端复核 iOS 权限和 Android TCP 后台行为。Windows 实机、真实微信 AppID/开发者工具/审核、移动商店签名/账号、在线网页产品范围仍分别缺证据或配置。

## 2026-10-17 Candidate package runtime check

The macOS artifact from run `39009788643` was checksum-verified, passed `hdiutil verify` and deep/strict ad-hoc codesign checks, then ran from its read-only DMG under isolated config/port. Health/database were OK; pairing advertised the Wi-Fi IP; the Pocket page returned HTTP 200 through that address; an unpaired status API request returned 403. The candidate was stopped and unmounted; the installed v1.0.40 app stayed healthy. This verifies packaged runtime behavior on the same Mac, not a phone over Wi-Fi.

The Windows unsigned preview from run `39009837297` built successfully; its artifact ZIP and EXE manifest hashes match, and the EXE is PE32+ x86-64. Latest head `f7e5c8a` still has Reliability macOS matrix, Pocket Android/iOS native builds and macOS candidate workflow pending. Windows real-device install, phone pairing, WeChat DevTools/real AppID, formal signing and public release remain open.

## 2026-10-17 EAS store-build preparation (head `de6f82a`)

- Added `mobile/eas.json` with development-client, Android preview APK, Android production AAB, production iOS build defaults, and Android Play internal-track submit settings. Expo app version source is local; no remote version counter is initialized.
- Added `docs/MOBILE-STORE-RELEASE.md` with owner-side EAS linking/build/submit steps and explicit credential boundaries. Existing app config resolves successfully as slug `yingxu-pocket`, version `1.0.0`, and matching iOS/Android identifier `com.yingxuapp.pocket`.
- Preserved pre-change `mobile/app.json` and `mobile/package.json` in `docs/snapshots/2026-10-17-pre-eas-release-config/`.
- This configuration is not an EAS project link, signed build, store submission, or release. EAS project ID, Apple team/App Store Connect app, Apple signing credentials, and Google Play service account still need owner setup. Do not add secrets to the repository.
- `pnpm dlx eas-cli@latest whoami` ran from the local package cache and returned `Not logged in`; this confirms no usable Expo account session. The setup guide now uses `pnpm dlx` and starts with account login and project initialization. Android/iOS local device tools remain absent on this Mac.

## 2026-10-17 PR #4 candidate validation at head df24115

The following checks refer to the exact current PR head `df2411578a0598d8c82415eef41235860261a01f` (branch `codex/v1.0.39-miniprogram-lan-tcp`, PR #4 OPEN/DRAFT, mergeable). They supersede older CI snapshots above where a newer run exists.

- **macOS candidate:** run `39011334553` completed successfully; artifact `12093236578`, 20,950,217 bytes, GitHub digest `sha256:54ed88b29dda95b2b8198d4178508ca9e0fc3dc70cb4ffe864b266eff15fa757`. Local ZIP SHA-256 matched. Its DMG SHA-256 is `1da55c2eeae9adf4a3ee029bbb30e647f1d525fc93038bc985d2446fc45b8d64`, matching the embedded `SHA256SUMS.txt`; `hdiutil verify` returned VALID. Read-only mounted app reports v1.0.40, Mach-O arm64, and passes `codesign --verify --deep --strict`; signature is ad-hoc with no Team ID. This is a verified candidate, not a notarized or public release.
- **Windows preview:** run `39011334570` completed successfully; artifact `12093300236`, 27,493,031 bytes, GitHub digest `sha256:213ff3361d7f59008684d31ce1b4a0648969ecc2189fca5ab85f4a13cf23a332`. Local ZIP SHA-256 matched. Embedded EXE SHA-256 `f182f3bf0ab4b822bacb0a60a9788ff0f72596911143e81382ac79e485812131` matches the package manifest; PE machine is x86-64. It remains an unsigned preview and has not been installed on a Windows PC.
- **Reliability:** run `39011334711` completed successfully across all six OS/Python matrix jobs.
- **Transfer-old-content regression check:** confirmed `smb/transfer.py`, `smb/templates/transfer.html`, and `tests/test_transfer_safety.py` are tracked in the canonical checkout (feature commit `2941a30`); the focused current-worktree suite ran 10 tests and all passed. This confirms the old-session feature exists in the current repository, while physical Windows/removable-drive recovery remains untested.
- **Pocket:** run `39011334571` Pocket JS/CNG/lint/typecheck/protocol tests and iOS/Android bundle exports completed successfully. At the last live poll, Android debug job `117334323780` was still building the APK and iOS Simulator job `117334323944` was still compiling the app. Do not count either native job as complete until a later terminal poll.
- **Remaining gates:** Windows and phone real-device use, Mini Program real AppID/DevTools/real-device review, Expo owner login and EAS project setup, Apple/Google signing and store submission, and formal public release remain unverified or unconfigured. Latest Release remains v1.0.34 at the last verified checkpoint.

### Same-host runtime check of the df24115 macOS candidate

- Launched the v1.0.40 app from the read-only artifact DMG through LaunchServices with isolated `SMB_CONFIG_DIR` and port 18083; the installed `/Applications/影序 YINGXU.app` was left untouched. `/api/health` returned `status=ok`, `database=ok`, version `1.0.40`.
- Pairing advertised Wi-Fi address `192.168.31.172` and `http://192.168.31.172:18083/pocket/`. Through that LAN address, `/pocket/` returned HTTP 200, unauthenticated `/api/status` returned 403, and `/api/pocket/status` returned 401. A loopback `/api/status` request returned 200 by design because the desktop UI is trusted on loopback; the LAN-path checks are the relevant Pocket exposure check.
- The candidate process was stopped and its DMG detached. This is same-host routing evidence, not a phone-on-Wi-Fi pairing test.

### Current public-site check caveat

- GitHub Latest Release still identifies `v1.0.34`, with assets `YINGXU-Windows-v1.0.34.exe` and `SHA256SUMS.txt`.
- Homepage and privacy page returned HTTP 200 on this check. The download route request ended in TLS/connection EOF from the audit host, so its current response is inconclusive; this transport result does not prove that the deployed route is down or healthy.

## Current verification checkpoint — PR head ae44735

- PR #4 head is `ae4473533f9b87081d57afe81a74d0d2379af2d7`, OPEN/DRAFT and mergeable. This commit contains only the candidate evidence audit and pre-edit snapshots; product code is unchanged from `df24115`.
- macOS run `39012271620` and Windows run `39012271576` completed successfully. Their artifact ZIP hashes matched GitHub metadata; package-internal DMG/EXE hashes matched their manifests. The macOS DMG passed `hdiutil verify`; its v1.0.40 arm64 app passed deep/strict codesign checks. Windows preview is unsigned x86-64. Same-source macOS candidate runtime evidence is recorded above.
- Reliability PR run `39012271555` and push run `39012268735` both completed successfully across all six OS/Python jobs.
- Local current-checkout verification: `.venv` unittest ran 82 tests (80 passed, 2 Windows-conditional skips); Mini Program Node tests passed 7/7; the focused transfer safety tests passed 10/10; `git diff --check` passed. The suite printed an optional local Ollama connection-refused message, but exited 0.
- Current Pocket run `39012271597` completed successfully: JS/CNG/lint/typecheck/protocol, Android debug job `117337141000`, and iOS Simulator job `117337140938` all passed. The artifact list contains only the Android debug artifact; no iOS simulator app or signed IPA artifact was uploaded. Android artifact `12093254859` ZIP (94,576,845 bytes) SHA-256 `36b13b0b8fe6fbdc65985e224715d7d998cc684a62696ac69084c1bf215cc543` matches GitHub metadata. The ZIP contains only `app-debug.apk` (269,562,399 bytes), no SHA256SUMS file; local APK SHA-256 `ed4f2ac38957c6ff5dd17e337fd7639f68a90383afa32bb9cacfc1e0224e471c`, ABI directories `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64`. This is an unsigned debug APK, not a store package or device install.
- Latest Release remains `v1.0.34`. Current home/privacy checks returned HTTP 200, while the download-route request failed at the audit host with TLS/connection EOF and remains inconclusive. Do not treat that transport result as a server outage or a success.

## 2026-10-17 current live recheck — PR head `3c68fe4`

- Worktree is clean on `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `3c68fe4583eed8916f7dfe28ce1feafbb2142485`; PR #4 is OPEN/DRAFT and mergeable.
- Current-head PR Reliability `39013794116`, push Reliability `39013788234`, macOS candidate `39013794195`, and Windows preview `39013794501` completed successfully.
- Pocket run `39013794196` has completed the Pocket JS/CNG/check job and Android debug job `117341606796` successfully. Artifact `12093724774` downloaded; GitHub metadata: 94,576,846 bytes, digest `sha256:8f4d6aaad3d965a5a5b84bc90ae95a1a93c8a7ceb03633650b00ba4b5680eeac`. Its `app-debug.apk` is 269,562,399 bytes; local SHA-256 `5f83d2e3b3a1177a087eee0e22aa4122397beea2ae9aa66fff2d517f30969758`; ABIs: arm64-v8a, armeabi-v7a, x86, x86_64. This is a debug artifact, not a store package or device acceptance.
- Pocket run `39013794196` completed successfully. iOS Simulator job `117341606981` completed successfully; the run's artifact list contains only the Android debug APK, no iOS Simulator app or IPA.
- The canonical Pages home, `/download/`, and `/privacy.html` under `https://yingxu-app.github.io/smart-media-backup/` all returned HTTP 200. The legacy org root URL returns a GitHub Pages “Site not found” 404, and API lookup for the old standalone `yingxu-app/yingxu-app.github.io` repo returns 404. Do not publish the stale local clone, which advertises macOS v1.0.31 and Windows v1.0.33.
- GitHub Release API lists the expected Windows v1.0.34 EXE and checksum file, but direct asset downloads from the audit host failed during TLS handshake with EOF; end-to-end public download remains unverified from this host.
- `https://smart-media-backup.vercel.app/` root returns HTTP 200 with older marketing content; `/download/` and `/privacy.html` return 404. It is not a complete current mirror. Pages uses the main repository's workflow; deployment run `38924919861` succeeded.
- Still open: Windows and mobile real-device use, real WeChat AppID/DevTools/review, EAS account/project setup, formal Apple/Google signing, notarization and store release, and the scope of browser-based backup.

## Follow-up verification — docs head `7283164`, product source `9bbae70`

- PR #4 is OPEN/DRAFT and mergeable at `72831641945f44c0786c8c5a405614dc9b74e8f8`; branch `codex/v1.0.39-miniprogram-lan-tcp`. The product source remains `9bbae707f51575a862693de4349b33de4135843d`.
- Reliability PR `39034625439`, Reliability push `39034622595`, macOS candidate `39034625447`, and Windows preview `39034625416` completed successfully. Exact-head desktop candidate packages were locally verified as recorded above.
- Pocket run `39034625528` completed successfully: JS/CNG/check `117401857804`, Android debug `117401857937`, and iOS Simulator `117401858066` all succeeded.
- Android artifact `12101758334` (94,576,845-byte ZIP) was downloaded; local SHA-256 `99007e5f87030719f683f5c3cbaaa434c72a2cf0e331577f4892d919581a2eb7` matches GitHub metadata, and ZIP integrity check passed. It contains `app-debug.apk` (269,562,399 bytes; SHA-256 `a903ea33e7ea8657443eca249fbda9ef89ac9568cc109c4100b84ae462e39be3`) with ABI directories `arm64-v8a`, `armeabi-v7a`, `x86`, and `x86_64`. No iOS Simulator app or IPA was uploaded.
- Exact-head native CI and Android debug artifact checks are closed. Android/iPhone physical installation, LAN pairing and reconnection, production signing, and store distribution remain open. Formal Release remains `v1.0.34`; website online-backup scope remains undefined.

## Follow-up verification — PR head `0f9be54`, product source `9bbae70`

- PR #4 is OPEN/DRAFT and mergeable at `0f9be54100e64f354f773de0561fd7e1779edb6f`; branch `codex/v1.0.39-miniprogram-lan-tcp`. This head contains documentation/snapshots only; product source remains `9bbae707f51575a862693de4349b33de4135843d`.
- Reliability PR `39036413957`, Reliability push `39036411847`, macOS candidate `39036414038`, Windows preview `39036414152`, and Pocket `39036413945` completed successfully.
- macOS artifact `12102705941` ZIP SHA-256 `8866893b4a0546e971c60271386c4c443f3720fd2c9e8cacce01b800905f1c83` matches metadata; v1.0.40 DMG SHA-256 `c46c91d85e448ad7718cb179781c0875e829eb97b12a5c92024ad1bc08abf0d3` matches its manifest and `hdiutil verify` is VALID. Its arm64 app passes deep/strict codesign but is ad-hoc, has no Team ID, and is not notarized.
- Windows artifact `12102725972` ZIP SHA-256 `132d0e01cbf74bcc823a1c8007f95b6af527af4c1fe07916b55816abf5fcb347` matches metadata; EXE SHA-256 `46f42a74076c5216e414040940d15e924766bc5435c0fb1845d496159717de91` matches its manifest. It is an unsigned x86-64 preview with no Windows-device acceptance.
- Pocket run `39036413945`: JS/CNG/check `117407077378`, Android debug `117407077639`, and iOS Simulator `117407077493` all succeeded. Android artifact `12103170937` ZIP (94,576,872 bytes) SHA-256 `43b652eff216cfaa619b6057c6cbfb47a02e20054741b734da0659d476f873f8` matches metadata and ZIP integrity passed. Its APK is 269,562,399 bytes, SHA-256 `2563c77002e95640abfe71cf5c739c2f9baaffeea19579e295e70a25edf2bf44`, with four ABI directories. No iOS app or IPA was uploaded.
- Canonical Pages home, `/download/`, and `/privacy.html` returned HTTP 200. Latest Release remains `v1.0.34` with Windows EXE and checksum only.
- Current-head CI/artifact verification is complete; physical Windows/iPhone/Android installation and LAN pairing, production signing, notarization, store distribution, Mini Program AppID/DevTools/review, EAS owner/project, and the browser online-backup scope remain open. This host lacks `adb`, full Xcode `devicectl`, and `xctrace` for physical-device acceptance.

## 2026-10-17 follow-up checkpoint — PR head `2ef63c6`

当前 head 所有 workflow 已终态成功：Reliability PR `39037887466`、Reliability push `39037883156`、macOS candidate `39037887277`、Windows preview `39037887272`、Pocket `39037887268`。当前 head 的 macOS 与 Windows artifact 均已下载并在本机核对 ZIP digest、内层清单及文件类型；macOS v1.0.40 DMG 在隔离配置下同机启动，health/database 正常，首页及 Pocket 静态资源返回 HTTP 200。Android debug APK `12103368321` 已下载并验证包体，APK SHA-256 `52a6df6ad9fa4fe6e7d7f88f90b809a2801d52fb5412c1941d736a30e4ea3560`，支持四个 ABI。Pocket iOS Simulator build 成功但没有上传 app 或 IPA。网站首页 HTTP 200；download/privacy 探测因 TLS EOF 无结论。正式 Release 仍为 v1.0.34。

此 checkpoint 不改变全端验收范围：Windows 和 iPhone/Android 实机、真实微信 AppID/审核、EAS owner 项目、正式签名/公证/商店发行、公开下载与回滚、Browser online backup 范围仍未闭环。上方平台表是较早证据快照，以上本 head checkpoint 为最新 CI 与候选产物状态；设备/账号与发行门槛仍需逐项实证。


## 2026-10-17 current verification checkpoint — PR head `4463789`

- Pocket run `39039775166` 三 job 全部 success。Android debug artifact `12103619468` 的 ZIP SHA-256 `70f4ac2efc655bc333dadcd979f58ab60f0b4333bca20c895fa70ad74d980f8d` 与 GitHub metadata 一致；APK SHA-256 `64d9481c6baa0c67d3e5e681cfd0f5a33dcd8e946c7137c3ec676b20f77fb1bf`，四 ABI。它是 debug 包且未真机安装；本 run 无 iOS artifact/IPA。
- 本 head macOS / Windows candidates、Pocket CI、Reliability PR/push 均通过；规范 Pages 首页、下载页、隐私页已在 Codex 浏览器实开，下载页正式版本仍为 v1.0.34。
- 仍需真实 Windows/iPhone/Android 验收，微信真实 AppID/DevTools/审核，EAS owner/project，签名、公证、商店发行与升级回滚，以及确认是否建设浏览器在线备份。

## 2026-10-17 current verification checkpoint — PR head `a271c92` and iPhone Pocket LAN

- PR #4 is OPEN/DRAFT and mergeable at `a271c92edfa800d2f5230bfd915ccf72eb97659a`; the worktree was clean before this documentation update. Product source remains `9bbae707f51575a862693de4349b33de4135843d`.
- Pocket run `39041500623` completed successfully: JS/CNG/check, Android debug and iOS Simulator jobs all succeeded. Android artifact `12104977106` is 94,576,842 bytes with metadata SHA-256 `b79d524bd6819f8ac60e12aa9865be7d176ebecd75d6f328666bf6a1d4300009`; local download matched and passed ZIP integrity. The APK is 269,562,399 bytes, SHA-256 `e7eb5b3dbc998c79646c0dc8fdb00c8ac93f64ce69bed5a4c35c79f85760f1ad`, with four ABIs. It is debug-only; the run uploaded no iOS app or IPA.
- Local regression on this checkout: desktop unittest 82 passed / 2 Windows-only skipped; Mini Program 7/7; Pocket protocol 5/5; mobile lint and TypeScript checks passed. The canonical Pages home, `/download/`, and `/privacy.html` returned HTTP 200; Latest Release remains `v1.0.34`.
- **iPhone PWA LAN acceptance:** a user-provided iPhone Safari screenshot shows the Pocket page with “桌面端已连接” and “已安全配对”, and historical records visible. At the same time, the installed Mac returned HTTP 200 with `paired:true`, `status:idle` from `/api/pocket/status`; `/api/status` reports v1.0.40/idle. This confirms actual iPhone Safari LAN page loading and secure pairing.
- **Still open:** refresh/status behavior, capture information/note read-write, home-screen installation, background/lock recovery, offline and network-switch/reconnect behavior, permission revocation; LAN HTTP does not support Service Worker offline cache. Android real-device acceptance remains open. Native iOS/Android store packages, Windows real-device acceptance, Mini Program real AppID/DevTools/review, EAS owner/project, production signing/notarization/store submission, formal release and browser online-backup scope remain open.

## 2026-10-19 native-app development checkpoint — PR head `52ee1cd`

- Current checkout: branch `codex/v1.0.39-miniprogram-lan-tcp`, HEAD `52ee1cd50e7f5c631d16a89ec31985b6cd496922`; PR #4 remains OPEN/DRAFT and mergeable. Worktree was clean before this checkpoint edit.
- Current-head checks: Reliability PR `39185713579`, Reliability push `39185709858`, macOS candidate `39185713548`, Windows preview `39185713515`, and Pocket `39185713562` all succeeded. Pocket JS/CNG/check, Android debug APK build, and iOS Simulator build all succeeded. This is CI evidence only.
- Android artifact `12158133353` is listed by GitHub with metadata size 94,608,827 bytes. Attempts to retrieve the archive from the Actions API returned EOF; its contents and local SHA-256 were not verified in this checkpoint. It is a debug build, not a signed release. The iOS job produced a Simulator build but no distributable IPA.
- Commit `52ee1cd` adds desktop and Pocket account profile initials, account registration name support, a cloud-history view under Archive Records, and version-check controls in Preferences. Version checks guide users to manually download/install; they do not silently update the app. Current public Release remains `v1.0.34`, with Windows EXE and checksum only, so there is no published mobile update package to install.
- The native-mobile implementation document records local-first phone backup, platform folder grants, copy/hash verification, interruption recovery, two-way LAN transfer, Firebase metadata sync/outbox, and local history. The remaining acceptance list below distinguishes these implemented paths from real-device and owner-account evidence.

### Scope decision and remaining work

- **Active product:** desktop app, iPhone Safari PWA, Android CI/debug candidate, LAN collaboration and Firebase account-scoped metadata sync. Native iOS is out of scope; Android device acceptance is deferred because no Android phone is available.
- **Web:** maintain the static product/download/privacy site only. Browser online backup and remote original-file transfer are out of this phase.
- **Needs device or account owner:** verify the iOS Safari PWA on the user's iPhone (home-screen launch, page refresh, LAN disconnect/reconnect, background/lock recovery); verify live Firebase sign-in and account-scoped sync on the already configured owner account; exercise Windows desktop on a physical PC. Android device acceptance is explicitly deferred; no Android phone is available.
- **Needs distribution setup:** publish a formal desktop release, update the download page, and verify install/update/rollback. The user has explicitly excluded Windows/macOS signing and notarization. Do not publish the internal Android preview APK as a release. iOS uses the PWA route, not the native store route.
- **Code-side finish line for this phase:** source gaps identified in the audit are implemented, targeted automated checks and current-head candidate builds pass, active CI remains free of Mini Program gates, and this document matches current evidence. Stop and hand over the exact device/account/release actions when no independent code work remains; do not claim full product closure.

### Source follow-up: preserve local backup progress when the desktop is offline

- The mobile copy engine previously stopped the entire multi-target task at the first offline desktop destination. It now marks that destination queued, continues copying to the phone/attached destinations and remaining files, then retries missing destinations after reconnection; already-copied local files are hash-deduplicated.
- Targeted mobile Node tests now pass 26/26; Expo lint and TypeScript no-emit checks pass. Physical media, app-background, and LAN reconnect behavior remain device acceptance items.

### Source follow-up: make Firebase authentication errors actionable

- Desktop and Pocket authentication now parse the Firebase error-code prefix even when Firebase appends policy details. They distinguish weak passwords, disabled email/password sign-in, invalid Web API keys, and incomplete Authentication setup.
- Local simulated-response checks pass: Pocket 27/27, desktop Firebase sync 7/7, Firebase server routes 6/6; Expo lint and TypeScript no-emit pass. This does not prove a live account can sign in or sync across devices.

## 2026-10-19 EAS Android preview build checkpoint

- EAS project `@nanyu-lu/yingxu-pocket` (ID `e83a97a0-f588-4068-a66d-f3e38782bcc1`) is linked in `mobile/app.json`. Android preview build `2926409f-7f75-454f-91a8-37ebf4dc2a66` reached `FINISHED`; build details are available at Expo's project build page. It used profile `preview`, app version `1.0.0` / build `1`, package `com.yingxuapp.pocket`, and source commit `2b1c89b`.
- The downloaded APK at `/Users/nanyu/Downloads/影序Pocket-Android-preview-1.0.0-build1.apk` is 92,264,537 bytes. Local SHA-256 is `9783f71f24c0105d8d22457e8f7715fbe2d61d6599d63ba578730f3e7b1cba64`; ZIP integrity passed. Package name was found in the binary Android manifest, and the APK contains `arm64-v8a`, `armeabi-v7a`, `x86`, and `x86_64`. This SHA is locally calculated; no independent Expo checksum was available. The preview has not been installed on a physical Android device.
- GitHub Actions for source commit `2b1c89b`: Reliability `39205982870`, macOS candidate `39205982844`, Windows preview `39205982843`, and Pocket `39205982845` all succeeded. Pocket JS/CNG/check, Android debug, and iOS Simulator jobs passed. The workflow uploaded only an Android debug artifact; it produced no iOS Simulator app artifact or IPA.
- Per the updated scope, iOS native distribution is excluded; the EAS iOS Simulator job is CI evidence only. Android device installation remains deferred, and this EAS checkpoint does not close physical-device acceptance or the broader product goal.
- Pre-edit document snapshots are preserved under `docs/snapshots/2026-10-19-eas-preview-build/`.

## 2026-10-19 scope update — iOS PWA and Android device deferral

- User decision: iOS delivery is Safari PWA only; remove Apple Developer membership, iOS native IPA, TestFlight, and App Store as active requirements. Android native-device acceptance is postponed because no Android handset is available; keep the existing Android preview as an internal artifact only.
- The PWA is currently served by the desktop app over LAN HTTP. The iPhone has previously loaded it and paired securely, but offline app-shell startup is not yet proven because the local HTTP origin does not support Service Worker offline caching. The PWA still needs Safari home-screen, lock/background, refresh, and reconnect checks.
- Firebase project is configured and its RTDB rules deny unauthenticated access and scope each user to `/users/{uid}`. Live owner-account login and cross-device data sync remain unverified. The desktop Settings UI previously cleared the password on all failures; this checkpoint changes it to clear only after successful login, so users can retry after an error.
- Current release remains v1.0.34; PR #4 is OPEN/DRAFT. macOS and Windows release candidates lack production signing (macOS is ad-hoc and not notarized; Windows preview is unsigned). Do not label them a public formal release until release assets and rollback path are verified.
- The last pre-scope Pocket run `39208969155` on `cba6674` reached success for JS/CNG/check, Android debug, and iOS Simulator. Future mobile CI no longer generates iOS native projects or runs an iOS Simulator build; iPhone delivery is the Safari PWA.
- Local checks for this update: desktop suite 107 passed with 2 Windows-only skips; targeted Firebase Python suite 14 passed; Pocket Node 27/27; mobile lint and typecheck passed; site home/download/privacy HTML parsed; workflow YAML parsed with Android-only jobs; `git diff --check` passed. A password-field mock confirmed failed login retains the field and successful login clears it.
- Firebase live probe: unauthenticated RTDB root read returned HTTP 401 `Permission denied`; Auth endpoint returned the expected HTTP 400 `INVALID_EMAIL` for a deliberately malformed test email, with no account created. The real account password must be typed locally before authentication and multi-device sync can be verified.

### Firebase account-verification checkpoint

- The configured Realtime Database is reachable; an unauthenticated root read returned HTTP 401 `Permission denied`, consistent with the deployed owner-scoped rules.
- A safe Firebase Authentication reachability probe using a deliberately malformed test email returned HTTP 400 `INVALID_EMAIL` from `identitytoolkit.googleapis.com`. No account was created. This confirms the endpoint responded to the probe but does not establish whether the user's login credentials work.
- Desktop Settings now keeps the password input after an unsuccessful login/registration request and clears it only after a successful response. A mocked UI check confirmed both branches; 14 targeted Firebase Python tests passed with the project virtualenv. Real account login and cross-device sync still require a user-entered password in the local app; credentials from chat will not be used.

### HTTPS iPhone PWA and Firebase username checkpoint (2026-10-19)

- Added an independent static PWA candidate under `site/pocket/`: account login/registration, initials avatar, UID-scoped Firebase history/live views, IndexedDB cache, offline app-shell service worker, install manifest and iPhone-sized PNG icon. This source candidate has not yet been deployed to GitHub Pages.
- Added PWA cloud client tests for password non-persistence, username profile update, UID-scoped history, offline restore, storage failure messaging and logout cache cleanup. PWA unit tests pass 7/7; the native Firebase client tests pass 5/5; targeted desktop Firebase tests pass 14/14; Expo lint/typecheck and mobile tests pass 28/28.
- Firebase email/password sign-up's REST request does not document `displayName` as an accepted request field. Desktop, native mobile and PWA now use `accounts:update` with the returned ID token to persist the username; an existing account can submit the optional username field on sign-in to update its profile. A failed profile update returns a retry instruction instead of claiming the name was saved.
- The desktop app at port 8080 was reachable during this checkpoint but reports `configured=true`, `signed_in=false`; the source server on port 18187 was not running. No password was entered and no real account login or cloud history sync was verified.
- PWA CI checks now run when `site/pocket/**` changes. Local JS syntax, manifest JSON, seven PWA tests, mobile lint/typecheck and 28 mobile tests pass. A targeted Python run initially exposed a stale mock assertion for the optional `display_name` argument; after updating the assertion, 14 targeted desktop Firebase tests pass.
- A localhost browser preview rendered the PWA, loaded its app-shell resources and reached Service Worker readiness. After stopping the static server, reloading the same localhost page still rendered from the cached shell. This proves the browser shell fallback in the local preview; it does not prove iPhone Safari installation, offline history for a real account, or public HTTPS deployment.
- Remaining: review and deploy the PWA candidate, verify public HTTPS routes, then have the user enter the Firebase password locally and validate real account sign-in, owner-scoped cloud reads, cached history and live progress in Safari. The PWA displays metadata and does not provide native iPhone media scanning or background copying. Android real-device testing remains deferred.

#### Local regression refresh before PR update (2026-10-19)

- Re-ran the complete desktop suite on the current local candidate: 108 tests passed, with 2 Windows-only tests skipped on macOS. The simulated Ollama connection-refused line is expected test output; the suite exit code was 0.
- Re-ran mobile lint, TypeScript no-emit, and Node tests: all succeeded, 28/28 tests passed. The separate HTTPS PWA cloud-client suite passed 7/7; JavaScript syntax checks and `git diff --check` passed.
- These results cover local code only. Current candidate changes remain uncommitted on branch `codex/v1.0.39-miniprogram-lan-tcp`; PR CI, Pages deployment, public HTTPS routes, real Firebase account login, and iPhone Safari install/offline behavior are not yet verified for this candidate.

#### PR candidate CI checkpoint (`5c95001`)

- Committed and pushed the HTTPS PWA/Firebase candidate as `5c95001c3a83bf90975226a3ce7039500a87c92e` to PR #4. The PWA job's JavaScript checks, manifest parse and 7 unit tests passed in GitHub Actions. Reliability matrix and macOS/Windows candidate builds succeeded; the Android debug build remains an internal CI artifact and is not device acceptance.
- The Pocket job initially stopped at `expo install --check`: the online Expo version service recommended `expo@58.0.16`, `expo-modules-core@58.0.23`, and `expo-router@58.0.24`. Offline package metadata reported no matching `expo-modules-core@58.0.23`, and this Mac could not reach npm (`ECONNREFUSED`), so I could not verify that the other recommended versions were published or installable. The pinned installed SDK's bundled module map accepts the current package versions under `EXPO_OFFLINE=1`; the workflow now uses that SDK-local compatibility check. The remaining lint/typecheck/test/prebuild/export checks must pass on the next exact PR head before accepting the CI checkpoint.
- macOS artifact `12196956679` metadata: 21,098,798 bytes, SHA-256 `aba82f823633e03e8d487874b05196a7b2185060ba3c8312a267c5b5a8f9b796`. GitHub's artifact download tool returned a reusable ZIP file reference, while local `gh` download failed with TLS EOF; therefore the package bytes have not been locally hashed or inspected. The current macOS build is ad-hoc/unnotarized by the existing workflow design.
- Current work is reviewable in PR #4 but not merged. Pages has not been deployed, Latest Release remains v1.0.34, and no live Firebase account password was entered. Real login/sync, public PWA routing, iPhone Safari installation/offline restore, Windows current-candidate device acceptance, signing/notarization, and release download/upgrade/rollback remain open.

## 2026-10-20 iPhone HTTPS PWA offline launch checkpoint

- **Verified on device:** On the current public `yingxu-app.github.io` Pocket page, Safari's Add to Home Screen flow was completed with “Open as Web App” enabled. The iPhone home screen then showed two entries named “影序 Pocket”; one was launched successfully. The app rendered its YINGXU POCKET account-login page without Safari address or navigation bars.
- **Offline evidence:** The iPhone status bar showed Airplane Mode during launch. The standalone PWA displayed its login form while offline, confirming the cached page shell can start from the home screen. This does not verify authenticated history cache, Firebase login, queued sync, or online recovery.
- **Network recovery:** Airplane Mode remained enabled. Control Center could not be reached through the current mirror gesture, and the mirrored app reported user control during one attempt. No account data or credentials were entered. Continue after network access is restored, then have the user enter credentials on-device for Firebase sync verification.
- **Current release evidence:** Local `origin/main` is `1dcd5284b2dfde9a2fa9425bd1fc8761e147ad6e`; latest main Reliability (`39326896855`), Pocket (`39326896840`) and Windows (`39326896672`) runs are successful. GitHub Release `v1.0.40` remains Draft with macOS DMG, Windows EXE and SHA256SUMS; latest public Release is `v1.0.34` with Windows EXE and checksum. No publication was performed.
- **Site recheck:** canonical `/`, `/pocket/`, `/download/`, and `/privacy.html` returned HTTP 200 using the system Python TLS store. `/update/` returned a TLS EOF in this check, so its current response is inconclusive. The update/install/rollback route and public release promotion remain open gates.
- **Home screen note:** there are two same-named Pocket icons. Neither was removed because their origin could not be distinguished safely.

## 2026-10-20 Windows 打包程序运行验收补充

- 现有 Windows runner 流程已对隔离的合成来源卡做 20 项备份接口检查，但旧流程在 Python 进程内启动 Flask，不能证明 PyInstaller 产物能启动。
- PR #10 新增构建后运行阶段：用临时配置启动本次生成的 unsigned x64 EXE，轮询 `/api/health` 并核对版本，再将同一套扫描、复制、SHA-256、重复跳过、历史和报告断言指向 EXE 自己的服务；完成后终止测试进程。
- 该 Windows-hosted runner 结果可以证明候选 EXE 在 CI 虚拟机中启动并执行合成备份流程，不代替用户 Windows PC、真实 SD 卡读卡器、交互式桌面窗口或不同机器上的安装升级验收。
- 本次修改前快照：`docs/snapshots/2026-10-20-windows-packaged-runtime/`。

### 首轮 Windows GUI runner 探测结果与调整

- PR #10 exact head `7089fc6fa2087829ff73319d331d217057df0ff5` 的 Windows preview run `39449881232` 通过 reliability 与 Python 进程内模拟备份，但“启动打包 EXE 并执行备份”步骤失败；PyInstaller 构建成功。runner 上 GUI EXE 进程保持存活，但 `/api/health` 在等待期间未响应，步骤日志不能进一步区分 WebView 会话与后台服务线程问题。
- 为避免把缺失的 GUI 运行时误报为产品功能失败或通过，本分支改用显式的 `YINGXU_E2E_HEADLESS=1` 诊断模式：相同打包 EXE 直接运行内置服务，随后对其服务执行健康版本核对和完整合成备份断言。标准用户启动仍保留 pywebview 桌面窗口流程。
- 下一次成功结果只可证明 Windows runner 上打包 EXE 的服务端资源和核心备份流程可运行；仍不覆盖 GUI 窗口交互、用户 Windows 安装/升级或真实读卡器。
- 调整前快照：`docs/snapshots/2026-10-20-windows-packaged-runtime-adjustment/`。
- PR #10 exact head `6deddba` 对应 run `39450869691` 的 PyInstaller build 与打包服务健康检查通过；验证脚本随后在打印中文标题时因 runner `cp1252` stdout 编码失败，尚未执行打包服务备份断言。workflow 子进程现显式使用 UTF-8；修复前快照在 `docs/snapshots/2026-10-20-windows-packaged-utf8-fix/`，修复效果待新 run 验证。

#### Packaged Windows service E2E terminal evidence (`bbfb942`)

- PR #10 head `bbfb942a83fe2c4d9412c4f6c3c0ac788cbbc560`: Windows preview run `39451574588` success; Reliability push `39451563134` and Reliability PR `39451574482` success across Windows/macOS/Ubuntu × Python 3.11/3.12; macOS candidate run `39451574496` success.
- Windows preview runner built the unsigned v1.0.40 EXE, launched that exact packaged executable in explicit isolated service mode, confirmed `/api/health` HTTP 200 and version 1.0.40, then passed 21 packaged-service E2E assertions including scan, invalid source rejection, copy, SHA-256, duplicates, history/report and unchanged source. PE x64, unsigned status, checksum manifest and artifact upload passed.
- Windows EXE artifact `12278397307`: 27,876,356 bytes, Actions metadata digest `sha256:be9a656d6e1cc8f1108f1b1745a5a91d0ea6ea6442df0e1ea3eb5edf831ac18a`. E2E report artifact `12279032308`: 1,971 bytes, metadata digest `sha256:1c2bb3347743966d26412bc56245f4324ee5d4d33855fd382df77264d65e7087`.
- This establishes packaged backend/service behavior on a Windows-hosted runner. It does not establish pywebview GUI interaction, a user-PC install/upgrade, or a physical card reader. PR #10 remains OPEN/DRAFT; the user's Windows device gate remains open. Snapshot: `docs/snapshots/2026-10-20-windows-packaged-e2e-terminal/`.
