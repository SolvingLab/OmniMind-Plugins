# roblox-studio

读取已打开的 Roblox Studio 场景和脚本，修改脚本、插入资源，并控制试玩。

这是 Roblox 官方文档描述的 Studio 内置服务器，不是社区包，也不是 `Roblox/studio-rust-mcp-server`。文档固定在 `Roblox/creator-docs` commit `031b2f91d3d47274c255f3ed5691c29f792c181d` 的 `content/en-us/studio/mcp.md`。页面要求最新 Studio，但没有给出可核对的版本号。本卡没有读取本机 Studio 版本或设置。

Windows 文档命令是 `cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat`。本包不展开 `%LOCALAPPDATA%`，也不读取那个目录。启动器路径必须由 `user_config.studio_mcp_launcher` 提供，没有默认值。未设置时服务器不注册。

文档许可证是 CC-BY-4.0。Studio 程序本身的最终用户许可不在这份文档许可证里。

图标是 Simple Icons icons/robloxstudio.svg，commit ed9a5192b24ad2f169bf1009931da0df27d5a49a。图标许可证是单独的 CC0-1.0，正文在 assets/icon-LICENSE.md，复用 K7 已保存的同一份。文档许可证仍是 CC-BY-4.0，两份许可证不合并。
