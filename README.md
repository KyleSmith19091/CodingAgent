<div align="center">
<h1>Coding Agent</h1>
</div>

Coding agent to assist or automate software engineering tasks.

## How to run
1. Currently only support ARM.
2. Download latest release

## How to build (google cloud run)

### Requirements
- The `uv` tool (follow instructions [here](https://docs.astral.sh/uv/getting-started/installation/))
- Access to a machine with a GPU (model packaged as Dockerfile).
- `cargo` in the future

### Steps
1. Install dependencies `uv sync`
2. Build and deploy image from dockerfile in `model` directory.
3. `gcloud run services proxy model-qwen3 --port=9090` - starts a proxy to cloud run instance hosting model.
4. Run program:
      - In current directory (when developing): `uv run src/codingagent/main.py` 
      - Build standalone binary: 
      ```bash
      uv run nuitka --onefile --standalone \
      --include-package=codingagent.packages.tools \
      --include-package=codingagent.packages.prompts \ 
      --include-package=codingagent.packages.tool_client \
      --include-package=codingagent.packages \
      --include-package=mcp \
      --include-module=mcp.server.fastmcp \
      src/codingagent/main.py
      ```