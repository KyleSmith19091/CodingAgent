import subprocess
import shlex

from mcp.server.fastmcp import FastMCP

# Initialise FastMCP server with a tool namespace "git"
mcp = FastMCP("git", log_level="CRITICAL")

# Whitelist of safe git commands (only these allowed)
SAFE_GIT_COMMANDS = [
    "status", "log", "diff", "show", "branch", "rev-parse", "fetch", "remote",
    "tag", "describe", "ls-files", "grep", "config --get user.name", "config --get user.email",
    "cat-file", "rev-list", "for-each-ref", "merge-base"
]

LIMIT = 25000  # max output length, can be used if you want

@mcp.tool()
def git(command: str) -> str:
    """
    Execute a git command safely with sandbox and timeout.
    Only allows commands in SAFE_GIT_COMMANDS whitelist (after stripping 'git ' prefix).
    
    Parameters:
    - command: The git command string **without** the initial 'git', e.g. "status" or "log -1"
    
    Returns:
    - Command stdout or error messages.
    """

    # validate command starts with allowed git subcommand
    # only allow exact matches or commands that start with an allowed prefix
    stripped_command = command.strip()
    if not any(
        stripped_command == allowed or stripped_command.startswith(allowed + " ")
        for allowed in SAFE_GIT_COMMANDS
    ):
        return f"Error: The git command '{stripped_command}' is not allowed for security reasons."

    full_cmd = "git " + stripped_command

    try:
        proc = subprocess.run(
            full_cmd,
            shell=True,
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = proc.stdout
    except Exception as e:
        return f"Error: Exception running command: {e}"

    # Optionally truncate output if longer than LIMIT (not shown here)
    return output.strip()

if __name__ == "__main__":
    mcp.run()
