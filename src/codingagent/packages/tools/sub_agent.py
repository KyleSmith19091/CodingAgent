import pkgutil

from codingagent.packages import tools
from codingagent.packages.tools.tool import builtin_mcp

# collect supported tools
_tools = []
for module_info in pkgutil.iter_modules(tools.__path__):
    module_name = module_info.name
    _tools.append(f"{tools.__name__}.{module_name}")

@builtin_mcp
def sub_agent_launch(query: str) -> str:
    f"""Launch a new agent that has access to the following tools: {" ".join(_tools)}.
    - When you are searching for a keyword or file and are not confident that you will find the right match in the first few tries, use the Agent tool to perform the search for you.
    When to use the Agent tool:
    - If you are searching for a keyword like "config" or "logger", or for questions like "which file does X?", the Agent tool is strongly recommended.
    When NOT to use the Agent tool:
    - If you want to read a specific file path, use the read_file tool instead of the Agent tool is strongly recommended. 
    - If you are searching for a specific class definition "class Foo" use the grep tool instead to find the match quickly.
    - If you are searching for code within a specific file or set of 2-3 files, use the read_file tool instead of the Agent tool, to find the match more quickly.
    - Writing code and running bash commands (use other tools for that).
    - Other tasks that are not related to searching for a keyword or file.

    Usage notes:
    1. Launch multiple agents concurrently whenever possible, to maximize performance; to do that, use a single message with multiple tool uses
    2. When the agent is done, it will return a single message back to you. The result returned by the agent is not visible to the user. To show the user the result, you should send a text message back to the user with a concise summary of the result.
    3. Each agent invocation is stateless. You will not be able to send additional messages to the agent, nor will the agent be able to communicate with you outside of its final report. Therefore, your prompt should contain a highly detailed task description for the agent to perform autonomously and you should specify exactly what information the agent should return back to you in its final and only message to you.
    4. The agent's outputs should generally be trusted
    5. Clearly tell the agent whether you expect it to write code or just to do research (search, file reads, web fetches, etc.), since it is not aware of the user's intent
    """
    return ""


