uv run nuitka --onefile --standalone \                       
--include-package=codingagent.packages.tools \
--include-package=codingagent.packages.prompts \
--include-package=codingagent.packages.tool_client \
--include-package=codingagent.packages \
--include-package=mcp \
--include-module=mcp.server.fastmcp \
src/codingagent/main.py