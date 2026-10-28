# 固定工具

名字摘自该 commit 的 `fusion_bridge/tool_surface.py`。不要发明别的工具名。这不是 CrowdStrike Falcon Fusion，也不是 Oracle Fusion ERP。

| 工具 | 本客户端默认 |
| --- | --- |
| `get_viewport` | 读相机，可调用 |
| `fetch_api_documentation` | 读 Fusion 进程内的 API 元数据，可调用 |
| `fetch_online_documentation` | 由 Fusion 进程去取 Autodesk cloudhelp，可调用；本客户端自己不访问该网站 |
| `fetch_design_guide` | 读插件内设计指南，可调用 |
| `list_scripts` | 列已保存脚本，可调用 |
| `load_script` | 读一个已保存脚本，可调用 |
| `get_active_selection` | 读当前选择，可调用 |
| `manage_annotations` | 只有 `action=list` 默认可调用。`claim`、`complete`、`release` 会锁注释并可能写属性标记，需要 `--allow-cad-write` |
| `call_autodesk_api` | 可改设计，需要 `--allow-cad-write` |
| `execute_python` | 在 Fusion 里执行 Python，需要 `--allow-cad-write` |
| `capture_viewport` | 会临时改视口，需要 `--allow-cad-write` |
| `set_viewport` | 改共享视口，需要 `--allow-cad-write` |
| `save_script` | 写脚本文件，需要 `--allow-cad-write` |
| `delete_script` | 删脚本文件，需要 `--allow-cad-write` |

宿主通过 `mcpServers` 直连时，工具列表由正在运行的插件返回，本包不过滤。脚本入口 `scripts/launch.py` 才执行上表的写保护。安装本包不会调用这些工具。
