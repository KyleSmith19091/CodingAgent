import json
from pathlib import Path
from typing import List, Tuple, Union

from codingagent.packages.tools.tool import builtin_mcp

LIMIT = 25000

@builtin_mcp
def edit_tool(path: str, file_content: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """
    When to use:
        - When you need to perform exact string replacements in files. 
        - When you need to update part of the content of a file.
        - When need to append to an existing file.

    Parameters:
        path: Path to the file to edit.
        file_content: Current file content (from read_file output).
        old_string: String to replace (must exclude line number prefixes).
        new_string: Replacement string (must preserve indentation after prefix).
        replace_all: If True, replace every occurrence of old_string.

    Usage:
        - IMPORTANT when editing text from read_file output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string. 
        - ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
        - The edit will FAIL if old_string is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use replace_all to change every instance of old_string. 
        - Use replace_all for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance.
    """

    p = Path(path)
    if not p.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    count = file_content.count(old_string)

    if replace_all:
        if count == 0:
            raise ValueError(f"String '{old_string}' not found in provided file content.")
        updated_content = file_content.replace(old_string, new_string)
    else:
        if count == 0:
            raise ValueError(f"String '{old_string}' not found in provided file content.")
        if count > 1:
            raise ValueError(
                f"String '{old_string}' found {count} times, must be unique or set replace_all=True."
            )
        updated_content = file_content.replace(old_string, new_string, 1)

    with open(p, "w", encoding="utf-8") as f:
        f.write(updated_content)

    return json.dumps({"output": "done"})