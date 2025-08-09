import shlex
import subprocess

from codingagent.packages.tools.tool import builtin_mcp

@builtin_mcp
def bash(command: str) -> str:
    """
    When to use:
        Executes a given bash command in a persistent shell session with optional timeout, ensuring proper handling and security measures.

    Parameters:
        command: command to execute (string)

    Usage:
        Before executing the command, please follow these steps:
        1. Directory verification
            - If the command will create new directories or files, first use the LS tool to verify the parent directory exists and is the correct location
            - For example, before running "mkdir foo/bar", first use ls to check that "foo" exists and is the intended parent directory
        2. Command Execution:
            - Always quote file paths that contain spaces with double quotes (e.g., cd "path with spaces/file.txt")
            - Examples of proper quoting:
                - cd "/Users/name/My Documents" (correct)
                - cd /Users/name/My Documents
                - python "/path/with spaces/script.py" (correct)
            - After ensuring proper quoting, execute the command.
            - Capture the output of the command.
        3. CRITICAL:
            - Carefully determine if commands are read-only for better user experience. You should always set read_only=true for commands that do not modify the filesystem or network. 
            - Read-Only Commands: grep, rg, find, ls, cat, head, tail, wc, stat, ps, df, du, pwd, whoami, which, date, history, man
            - Never Read-Only: Commands with > (except to /dev/null or standard output), $(), $VAR, dangerous flags (git diff --ext-diff, sort -o, npm audit --fix), git branch -D
        
        Using commands:
        Build systems like npm run build almost always need write access. Test suites also usually need write access. NEVER run build or test commands in sandbox, even if just checking types.
    """

    if not isinstance(command, str) or not command.strip():
        raise ValueError("Command must be a non-empty string.")

    # Enforce proper quoting for paths with spaces
    # (very naive: only wraps unquoted path tokens containing spaces)
    def ensure_quotes(token):
        if " " in token and not (token.startswith('"') and token.endswith('"')):
            return f'"{token}"'
        return token

    tokens = shlex.split(command)
    tokens = [ensure_quotes(t) for t in tokens]
    safe_command = " ".join(tokens)

    try:
        result = subprocess.run(
            safe_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += ("\n" + result.stderr.strip())
        return output
    except Exception as e:
        raise f"Error executing bash command: {e}"
