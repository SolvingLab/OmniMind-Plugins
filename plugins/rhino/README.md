# rhino

Functional mapping of prototype Rhino. Not an official McNeel plugin and not a Kimi package.

Pinned source: `EaseHee/rhino-mcp` tag `v0.6.0` commit `3e10efb9963be36ee1209f8f9ebd2cc6efcfcc46`.

`pyproject.toml` name is `rhino3dm-mcp` 0.6.0. Console scripts `rhino-mcp` and `rhino3dm-mcp` both call `rhino_mcp.server:main`. This package launches `rhino3dm-mcp`.

There is no verified PyPI artifact equal to this commit. Do not use bare `uvx rhino3dm-mcp`.

stdio command, not executed here:

```text
uvx --python 3.11 --from git+https://github.com/EaseHee/rhino-mcp.git@3e10efb9963be36ee1209f8f9ebd2cc6efcfcc46 rhino3dm-mcp
```

`--python 3.11` is uv's option. The project requires Python `>=3.11` and also classifies 3.12 and 3.13. This wrapper requests 3.11.

`user_config.force_mode` has no default. Unset disables the server (`setup_required`). `standalone` is headless `.3dm` via `rhino3dm` and does not connect to Rhino. `bridge` still requires a local Rhino 8 session and the C# plugin; this package does not install or start either.

Icon is the pinned repo file `assets/rhino-mcp.png`, a rhino-head mark, not an author avatar and not a claim of an official McNeel plugin.
