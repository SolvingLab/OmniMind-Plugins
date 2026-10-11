# 社区收录规则

提交 `data/plugins/<owner>__<repo>.yml`，每个公开 GitHub 仓库一个文件。name 从插件 manifest 读取，不能在 YAML 中重命名。单个仓库可通过 `path` 指定一个插件根目录，其余合法目录仍可能由 topic 自动发现。

## 准入要求

- GitHub topic 至少包含 `claude-code-plugin`、`codex-plugin`、`claude-plugin`、`zcode-plugin` 之一。
- stars ≥ 500，最近 180 天有 push，创建至少 30 天。
- 公开、有 GitHub 能识别的 license、非 archived、非 fork。
- 不是 awesome 列表，独立插件根目录数量不超过 20。
- 指定目录在钉死版本上有有效 `.omnimind-plugin/plugin.json`、`.claude-plugin/plugin.json` 或 `.codex-plugin/plugin.json`，当前 HEAD 上也没有消失。
- manifest name 符合 `/^[a-z0-9][a-z0-9._-]{0,127}$/`。
- category 必须是办公文档、编程开发、设计创作、数据分析、科学研究、协作管理、应用增强之一；summary 用中文准确描述功能，不宣称尚未验收的安装兼容性。

只有 `.zcode-plugin` 的包暂不能进入 V2 安装目录。npm、PyPI 包、MCP server、普通 skills 目录与 GitHub 链接集合也不能冒充插件包；官网外部获取条目放在 `data/external.yml`。

## YAML 模板

例如 `data/plugins/DietrichGebert__ponytail.yml`：

```yaml
repo: DietrichGebert/ponytail
path: "" # 仓库根；子目录例如 plugins/my-plugin，不允许 .. 或绝对路径
category: 编程开发
summary: 优先选择简单方案的编码工作流，提供 Claude Code 与 Codex hooks。
homepage: https://github.com/DietrichGebert/ponytail
# displayName: Ponytail # 可选展示名，不影响 plugin name
# ref: main # 可选；构建时解析为完整 sha
# sha: 9b58c1ffb790c075ca32e70a89cf1d80588f4abf # 可选完整 commit pin
```

允许字段仅为 `repo/path/ref/sha/category/summary/displayName/homepage`。省略 `ref/sha` 时每次构建固定当前默认分支 HEAD；同时提供时 sha 优先。文件名大小写应与上游一致，检查接受 GitHub 的大小写兼容。文件中的路径相对于仓库根，图标相对于插件根目录或 manifest 所在目录解析。

## 本地检查

先安装依赖，把 `GITHUB_TOKEN` 放入进程环境，然后运行：

```sh
npm ci
node scripts/check-submission.mjs data/plugins/DietrichGebert__ponytail.yml
npm run build
npm run validate
```

不传文件参数的 `npm run check` 会检查全部 YAML。未知 YAML 字段、非法路径、准入失败、未核实的网络错误都以非零退出码结束。无效条目的具体原因会打印；token 不输出、不保存。

## 后续维护

精选由维护者在 `data/featured.yml` 中按 `marketplace` + `name` 决定，社区收录不会自动成为精选。

仓库 archived、404、转私有或 manifest 消失时立即退出目录。push 超过 180 天或 stars < 400 时隐藏，保留 7 天的起始时间后标记移除；恢复达标会清除记录。修改分类映射必须覆盖全部真实上游值，不能把未知分类静默归入兜底类。

目录聚合通过不代表插件已完成 OmniMind 安装或运行验收；安装验证在 V2 切片执行。不要在本仓库提交 token、插件源码副本、`node_modules/` 或 `.cache/`。
