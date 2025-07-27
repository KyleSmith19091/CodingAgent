import fnmatch
import logging
import os
from pathlib import Path
import subprocess
import json
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

# initialise FastMCP server
mcp = FastMCP("edit", log_level="CRITICAL")

LIMIT = 25000

@mcp.tool()
def edit_tool(path: str, ignore: Optional[List[str]] = None) -> str:
    """Performs exact string replacements in files. 
    Usage:
    - You must use your read_file tool at least once in the conversation before editing. This tool will error if you attempt
      an edit without reading the file.
    - When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
    - ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
    - Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
    """

    p = Path(path)
    if not p.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    # Run `ls -A` (includes hidden files, excludes . and ..)
    result = subprocess.run(
        ["ls", "-A", str(p)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )

    files = result.stdout.strip().split("\n") if result.stdout else []
    ignore = ignore or []

    filtered = []
    for f in files:
        full_path = str(p / f)
        if any(fnmatch(full_path, pattern) for pattern in ignore):
            continue
        filtered.append(full_path)

    return json.dumps(filtered)

if __name__ == "__main__":
    mcp.run()