# freecad

在 FreeCAD 里新建和查看 CAD 文档、创建和修改零件与模型，并在已启动的插件上运行建模脚本。

固定源是 `neka-nat/freecad-mcp` tag `v0.1.27` commit `78bf0230a03324b56c9a0b7f55150fb5be2a0d42`。它有两个组件：FreeCAD 里的 addon `addon/FreeCADMCP`，以及客户端启动的 stdio 服务器 `freecad-mcp = freecad_mcp.server:main`。本包不把 addon 装进 FreeCAD，也不启动 FreeCAD。

stdio 命令没有执行：

```text
uvx --python 3.12 --from git+https://github.com/neka-nat/freecad-mcp.git@78bf0230a03324b56c9a0b7f55150fb5be2a0d42 freecad-mcp --host <你设置的主机>
```

`user_config.rpc_host` 没有默认值。未设置时宿主不注册服务器。不要填 `localhost` 当本包默认，也不要填盘符根。上游代码把 RPC 端口写死为 `9875`，本包没有另开一个端口配置。

README 里的安装步骤是上游说明，本卡没有执行。

图标是 FreeCAD 官方应用独立图标 src/Gui/Icons/freecad.svg，tag weekly-2026.10.14，commit 50daee777321b5085accd1f57b57f1a7c1781cae。原文件 width 48、height 48、viewBox 0 0 48 48，title 为 FreeCAD。文件里没有 copyright 行，也没有许可证句子，不能把服务器的 MIT 说成这张 SVG 的许可证。供私人 DEV 身份展示。
