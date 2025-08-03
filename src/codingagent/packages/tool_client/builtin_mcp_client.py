from typing import Any, Callable, List
import inspect
from mcp import Tool

from codingagent.packages.tools.tool import builtin_tool_from_function, ollama_tool_from_mcp_tool

class BuiltinMCPClient:
    def __init__(self, builtin_tool_commands: list[Callable[..., Any]]):
        self.tool_schema_list = [builtin_tool_from_function(fn) for fn in builtin_tool_commands]
        self.command_index = {command.__name__: command for command in builtin_tool_commands}
    
    async def connect_to_server(self, _: str = "") -> list:
        return [ollama_tool_from_mcp_tool(tool) for tool in self.tool_schema_list]

    async def call_tool(self, tool_name, tool_args):
        # confirm tool is a builtin tool
        if tool_name not in self.command_index:
            raise ValueError(f"{tool_name} not a builtin tool")

        # get a handle to the tool
        command = self.command_index[tool_name]

        # check if we need to await the execution of the command
        if inspect.iscoroutinefunction(command):
            return await command(**tool_args)
        else:
            return command(**tool_args)
