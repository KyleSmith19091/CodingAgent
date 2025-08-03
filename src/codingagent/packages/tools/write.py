from codingagent.packages.tools.tool import builtin_mcp


@builtin_mcp
def write_tool(file_path: str, content: str = "") -> str:
    """Writes a file to the local filesystem. 
    Usage:
    - This tool will overwrite the existing file if there is one at the provided path.
    - If this is an existing file, you MUST use the 'read' tool first to read the file's contents. This tool will fail if you did not read the file first.
    - ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
    - NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
    - Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked.
    """

    with open(file_path, "w") as f:
        f.write(content)

    return f"File {file_path} has been created."


        