# OmniMind-Plugins

为 OmniMind V2 生成公开上游插件目录。目录只保存元数据与 GitHub commit pin，安装时由 V2 从上游获取插件内容。

## 本地构建

需要 Node.js 22 或更新版本，以及已在进程环境中配置的 `GITHUB_TOKEN`。脚本通过原生 `fetch` 调用 GitHub REST / GraphQL，不需要 `gh`，不输出或持久化 token。

```sh
npm ci
npm run build
npm run validate
```

Windows PowerShell 若限制运行 `npm.ps1`，使用 `npm.cmd`。受限沙箱内可把 npm 缓存放在本仓库：

```powershell
npm.cmd ci --cache .cache/npm
npm.cmd run build
npm.cmd run validate
```

安装依赖后，一条 `npm run build` 命令生成所有产物并打印按来源统计。`node_modules/` 和 `.cache/` 不提交；`dist/` 与 `data/decay-state.json` 应提交。

## 订阅方式

桌面端与官网直接读取本仓库的合并目录：

`https://raw.githubusercontent.com/SolvingLab/OmniMind-Plugins/main/dist/plugins.json`

桌面端显示全部条目；官网生态优先展示 `featured: true` 的精选插件，用户可再自行搜索其他插件。精选名单由维护者在 `data/featured.yml` 中按 `marketplace` + manifest `name` 人工增删，初版按七类各取 3 个；优先参考 GitHub stars，官方条目没有独立 stars 时参考上游 featured 与原始排序。build 在对应来源目录标记精选，合并目录继承胜出来源的标记；未找到的名单项写入 `dist/report.json` 的 `warnings`，不阻断构建。

在 V2 Dev 的“添加插件市场”中也可填写本地 JSON 文件路径。V2 的实际安装兼容性验证属于切片 0b / 2。

| 文件 | 市场 name | 行为 |
| --- | --- | --- |
| `dist/plugins.json` | `omnimind-ext` | 单一合并目录；同名按 anthropic > openai > zcode > solvinglab > community 保留 |
| `dist/marketplaces/anthropic.json` | `omnimind-ext-anthropic` | Anthropic 来源全部通过检查的条目 |
| `dist/marketplaces/openai.json` | `omnimind-ext-openai` | OpenAI 来源全部通过检查的条目 |
| `dist/marketplaces/zcode.json` | `omnimind-ext-zcode` | ZCode 来源中具有 V2 支持 manifest 的条目 |
| `dist/marketplaces/solvinglab.json` | `omnimind-ext-solvinglab` | SolvingLab 公开仓库及子目录中发现的插件 |
| `dist/marketplaces/community.json` | `omnimind-ext-community` | topic 发现及 YAML 收录的社区插件 |

单一目录适合快速浏览，只能安装每个名字的优先来源。落选来源保存在条目的 `x-omnimind.alternates`，V2 在 `raw` 中保留它，不会自动把它变成独立可安装条目。按来源订阅适合需要选择来源的用户，例如 `github@omnimind-ext-anthropic` 与 `github@omnimind-ext-openai` 可以并存。

`dist/external.json` 是独立的外部获取链接数据，包含 `slug/name/publisher/summary/category/source/registry/homepage/action`，`registry` 在 GitHub 集合条目中为 `null`。它不是 marketplace，不能作为插件市场订阅。官网 `5798a8e34526dabc63005f83ea9e1f63ac9506ce` 的 `lib/ecosystem.ts` 实际有 **9** 条，与任务给定的 10 条不一致；本仓库保留真实的 9 条，并在报告中标记差异，待 Main 提供第 10 条的真实来源。

## 聚合规则

三个上游目录分别读取 `anthropics/claude-plugins-official/.claude-plugin/marketplace.json`、`openai/plugins/.agents/plugins/marketplace.json`、`zai-org/zcode-plugins/marketplace.json` 的当前 HEAD。相对路径与 `local` 源转换为上游仓库的 HEAD sha；GitHub `url/git-subdir` 源保留完整 sha，未提供 sha 时解析 ref 或默认分支 HEAD。所有输出 source 严格为 `{source: "github", repo, path, sha}`。

每个条目在钉死的 sha 下读取 plugin.json，按 V2 顺序识别 `.omnimind-plugin`、`.claude-plugin`、`.codex-plugin`。仅有 `.zcode-plugin` 的条目被排除。条目 name 使用 manifest 的真实 name，目录原名称不同则记录在 `nameCorrections` 与 `x-omnimind.upstreamName`，不会擅自给插件改名。同一来源内重名按 repo/path/sha 的稳定顺序保留第一条并记录拒绝原因；跨来源重名按照上述来源优先级合并。

GitHub repository 元数据使用每批 50 个仓库的 GraphQL 查询；manifest 每批 25 条查询。固定 sha 的公开文件与 tree 缓存在 `.cache/github/`；仓库状态和 HEAD 每次运行重新查询。明确的 404 会先通过 REST 确认以兼容仓库更名；403、429、网络失败与截断的 tree 会报错，不会伪装成仓库消失。

分类由 `data/categories.yml` 显式映射到办公文档、编程开发、设计创作、数据分析、科学研究、协作管理、应用增强。所有出现的上游分类都检查，未映射值导致 build 失败并列出，缺分类使用 `uncategorized -> 应用增强`。

图标优先取上游 `icon` 或 manifest `interface.logo`。相对资源解析为固定 sha 的 raw.githubusercontent.com URL；保留有效的上游 https 图片 URL。图片不可用时检查 `https://github.com/<owner>.png`，仍不可用就省略 `icon`。第三方图片检查不携带 token。

## 社区与衰减

自动发现 GitHub topic `claude-code-plugin`、`codex-plugin`、`claude-plugin`、`zcode-plugin`：stars ≥ 500、最近 180 天有 push、仓库年龄 ≥ 30 天、有 license、公开、非 archived、非 fork。awesome 列表和包含超过 20 个独立插件根目录的聚合仓库不收录。PR 使用同样的准入检查，详见 [contributing.md](contributing.md)。

所有来源都执行衰减规则，检查当前默认分支上的对应目录，而不仅检查仍然存在的旧 pin：archived、404、转为私有、manifest 消失或真实 name 改变立即移除；push 超过 180 天或 stars < 400 时立即隐藏，记录 `hiddenSince`，满 7 天标记移除。隐藏和移除条目不出现在安装目录中，状态记录保留以便复查；恢复到 push ≤ 180 天且 stars ≥ 400 时清除衰减记录。社区新增准入为 500 stars，已收录条目保留到 400 stars，避免门槛附近反复进出。

```sh
node scripts/scan-decay.mjs --dry-run
node scripts/scan-decay.mjs
node scripts/check-submission.mjs data/plugins/DietrichGebert__ponytail.yml
node scripts/validate-v2.mjs dist/plugins.json dist/marketplaces/*.json
```

`--dry-run` 不修改 `dist/` 或 `data/decay-state.json`，只更新忽略的查询缓存。正式 scan 先更新状态再重建所有目录。报告包含按来源接受/拒绝数量、全部拒绝原因、命名修正、重名胜出与 alternates、SolvingLab 递归扫描清单、社区搜索数量、图标检查、外部条目映射和衰减证据。

## Actions 与提交边界

`build.yml` 每日 `17 3 * * *`，`decay-scan.yml` 每周一 `41 4 * * 1`，cron 使用 UTC。两个任务构建和验证后把生成的 `dist/` 与衰减状态提交回默认分支，桌面端与官网读取上述 raw.githubusercontent.com 地址，不使用 CDN。精选名单的变更也触发默认分支构建。PR 任务只运行收录校验。每个 job 都限制 `github.repository == 'SolvingLab/OmniMind-Plugins'`。

本切片只准备本地文件，没有创建 GitHub 仓库、push、开 PR 或激活 Actions。Main 决定是否发布并激活定时任务；本地提交由 Main 在宿主完成。

## 本次验收记录（2026-10-10）

分支为 `feat/ext-market-0a-aggregator`，没有 commit SHA。本地实现与产物已准备好，Main 可在宿主提交 `feat: bootstrap OmniMind-Plugins aggregator`。

| 来源 | 目录条目 | 丢弃插件候选 | 排除仓库 | 主要原因 |
| --- | ---: | ---: | ---: | --- |
| anthropic | 84 | 231 | 0 | 衰减 201；缺 manifest 26；同来源重名 2；非法 manifest name 1；HEAD name 改变 1 |
| openai | 62 | 3 | 0 | 衰减 3 |
| zcode | 0 | 27 | 0 | stars < 400 隐藏 22；缺支持 manifest 5 |
| solvinglab | 0 | 0 | 11 | 11 个公开仓库的完整 tree 均无插件根目录 |
| community | 109 | 8 | 18 | 同来源重名 8；排除 >20 插件聚合仓库 3、awesome 列表 2、无 license 4、无 manifest 9 |

五个来源目录共有 255 条，合并目录 245 条。三个上游声明名称有 25 个跨源重名；筛选后的目录有 10 个跨源重名，10 条落选来源保存为 alternates。9 个名字由 anthropic 胜出：`cloudflare/expo/figma/github/hyperframes/linear/mcp-apps/stripe/superpowers`；`data-analytics` 由 openai 胜出。20 处上游目录名称按 manifest 的真实 name 修正。没有非 GitHub 源进入目录，本轮非 GitHub 丢弃数为 0。

衰减统计使用去重后的来源/仓库/路径/pin/name，因此隐藏的候选行数与隐藏的独立记录数不同。build 检查 492 个独立 subject，263 个健康、223 个隐藏、6 个立即移除；健康条目同来源去重后保留 255 条。dry-run 复查实际发布目录与状态中的 484 个 subject，255 个健康、223 个隐藏、6 个移除，9 个受检的 `dist/` 和 state 文件 SHA-256 均未改变。

| 验收命令 / 操作 | 真实结果 |
| --- | --- |
| `npm.cmd ci --cache .cache/npm` | exit 0；安装 2 个包，audit 0 vulnerabilities |
| `node scripts/build.mjs` | exit 0；255 个来源条目、245 个合并条目、9 个 external 条目 |
| `node scripts/validate-v2.mjs dist/plugins.json dist/marketplaces/*.json` / `npm.cmd run validate` | exit 0；六个目录均通过规则检查 |
| 仓库外 stdin 临时脚本，`node --import ../base/node_modules/tsx/dist/loader.mjs --input-type=module` | exit 0；只读调用 V2 `parseMarketplaceManifest`，六个目录计数及 listing/raw 保留检查通过 |
| 新鲜 GitHub Contents API 抽查 | exit 0；anthropic `agent-sdk-dev`、openai `adobe`、community `agentrq` 的 manifest name 与条目完全一致；额外核对隐藏的 zcode `accounting-and-reporting` |
| `node scripts/scan-decay.mjs --dry-run` | exit 0；上述 484 个 subject 复查，产物与 state 不变 |
| `node scripts/check-submission.mjs data/plugins/DietrichGebert__ponytail.yml` / `npm.cmd run check` | exit 0；1/1 收录 YAML 通过 |
| stdin 断言脚本 | exit 0；覆盖 source 归一化、路径拒绝、7 天临界值、恢复、立即移除、400/500 门槛、旧 name 隔离、重名优先级、未知分类失败、GraphQL 失败、tree 截断/404、仓库更名与私有 manifest 不缓存 |
| workflow / 依赖 / token 静态检查 | exit 0；所有 job 有仓库限制，唯一直接依赖版本正确，交付文件未包含进程 token |

早期环境失败已解决：PowerShell 禁止 `npm.ps1`（改用 `npm.cmd`）；默认 npm cache 无写权限（改用仓库 `.cache/npm`）；`js-yaml` 5 ESM 不提供默认导出（改用命名空间导入）。一次 stdin 中文测试常量被 PowerShell 管道编码替换，改为从分类模块取真实字符串后断言通过。没有把失败的尝试计为通过。

external 的真实映射：Context7、Playwright MCP、LangGraph → 编程开发；MarkItDown、Filesystem MCP → 办公文档；LlamaIndex → 数据分析；Firecrawl MCP → 科学研究；Browser Use、Model Integration Catalog → 应用增强。第 10 条缺少真实源信息，是唯一未完成的数据项；不会杜撰条目。实际插件安装验收按任务范围由 0b / 切片 2 完成。

### 应提交文件（33 个）

```text
.gitignore
LICENSE
README.md
contributing.md
package.json
package-lock.json
scripts/build.mjs
scripts/scan-decay.mjs
scripts/check-submission.mjs
scripts/validate-v2.mjs
scripts/lib/github.mjs
scripts/lib/categories.mjs
scripts/lib/logo.mjs
scripts/readers/anthropic.mjs
scripts/readers/openai.mjs
scripts/readers/zcode.mjs
scripts/readers/solvinglab.mjs
scripts/readers/community.mjs
data/categories.yml
data/decay-state.json
data/external.yml
data/plugins/DietrichGebert__ponytail.yml
.github/workflows/build.yml
.github/workflows/decay-scan.yml
.github/workflows/pr-check.yml
dist/plugins.json
dist/marketplaces/anthropic.json
dist/marketplaces/openai.json
dist/marketplaces/zcode.json
dist/marketplaces/solvinglab.json
dist/marketplaces/community.json
dist/external.json
dist/report.json
```

## 许可证与范围

聚合脚本使用 MIT License。插件内容始终受各自上游许可证约束。这里不镜像插件内容、不收录私有仓库、不修改 V2、OmniMind-Web 或 Euler。
