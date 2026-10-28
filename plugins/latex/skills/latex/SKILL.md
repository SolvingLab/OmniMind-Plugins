---
name: latex
description: 在已固定的 web-latex-mcp@0.9.0 上读取、修改并编译用户工作区里的 LaTeX。未配置工作区时保持 setup_required。
---

# LaTeX

- npm：web-latex-mcp@0.9.0
- integrity：sha512-FlBOY1s9mzQAiYLJzAWQnM0XplvPETQcJZgYLLVu3F61RxPUZlp5dKi95iXc95mxRVflmJEXc6roa4jM2bFnXg==
- gitHead：2997a607bbc8d45ad0b75393eea857e52f84db99
- 入口：web-latex-mcp -> dist/index.js
- argv：npx --yes web-latex-mcp@0.9.0
- 禁止：@latest

user_config.workspace 必填，无默认值，只展开到 WEB_LATEX_MCP_WORKSPACE。不要使用主目录或上游的 ${HOME}/latex-workspace。

上游点名的编译器是 latexmk 和 tectonic。本卡没有运行 TeX，也没有配置 Overleaf 或 GitHub token。
