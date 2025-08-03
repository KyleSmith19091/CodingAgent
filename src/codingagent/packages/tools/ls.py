import fnmatch
from pathlib import Path
import subprocess
import json
from typing import List, Optional

from codingagent.packages.tools.tool import builtin_mcp

@builtin_mcp
def ls(path: str, ignore: Optional[List[str]] = None) -> str:
    """Lists files and directories in a given path. 
    - The path parameter must be an absolute path, not a relative path. 
    - You can optionally provide an array of glob patterns to ignore with the ignore parameter. 
    - You should generally prefer the Glob and Grep tools, if you know which directories to search.
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
