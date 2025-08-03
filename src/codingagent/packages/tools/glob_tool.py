import glob
import os
import json

from codingagent.packages.tools.tool import builtin_mcp

LIMIT = 10000

@builtin_mcp
def glob_tool(root_directory: str, pattern: str = "") -> str:
    """Fast file pattern matching tool that works with any codebase size. 
    - The root directory is the directory to start the file matching from (it is recursive)
    - Supports patterns like **/*.ts for trying to recursively find the files in subdirectories
    - Supports glob patterns like "***.ts"
    - Returns matching file paths sorted by modification time
    - Use this tool when you need to find files by name patterns
    - When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
    - You have the capability to call multiple tools in a single response. It is always better to speculatively perform multiple searches as a batch that are potentially useful.
    """

    files = glob.glob(pattern, root_dir=root_directory, recursive=True)
    files_with_mtime = []
    for f in files:
        try:
            mtime = os.path.getmtime(f)
            files_with_mtime.append((f, mtime))
        except FileNotFoundError:
            continue

    files_with_mtime.sort(key=lambda x: x[1], reverse=True)
    sorted_files = [f for f, _ in files_with_mtime]

    if len(sorted_files) > LIMIT:
        sorted_files = sorted_files[:LIMIT]

    return json.dumps(sorted_files)
        
