# FreeCAD addon component

From `addon/FreeCADMCP/package.xml` at commit `78bf0230a03324b56c9a0b7f55150fb5be2a0d42`.

- name: FreeCAD MCP
- version: 0.1.27
- date: 2026-10-13
- license declared in package.xml: MIT
- workbench classname: FreeCADMCPAddonWorkbench
- workbench name: MCP Addon
- subdirectory: `./` so `InitGui.py` stays at the addon package root

The addon directory also contains `Init.py`, `InitGui.py`, and `rpc_server/`. Those files were listed, not vendored into this wrapper and not installed into FreeCAD.

Windows paths from `docs/installation.md`, recorded only:

- FreeCAD 1.1: `%APPDATA%\FreeCAD\v1-1\Mod\`
- older unversioned: `%APPDATA%\FreeCAD\Mod\`

The resulting folder must contain `FreeCADMCP\InitGui.py` directly.
