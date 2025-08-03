import inspect
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable

from mcp.server.fastmcp.tools.base import Tool
from mcp.types import Tool as MCPTool, CallToolResult, TextContent

@dataclass
class BuiltinTool:
    name: str
    description: str
    inputSchema: dict[str,Any]

def builtin_tool_from_function(fn: Callable[..., Any]) -> MCPTool:
    tool = Tool.from_function(
        fn,
    ) 
    return MCPTool(
        name=tool.name,
        # description=tool.description,
        inputSchema=tool.parameters,
        outputSchema=tool.output_schema,
        annotations=tool.annotations,
    )

def ollama_tool_from_mcp_tool(tool: MCPTool):
    properties = {}
    if "properties" in tool.inputSchema:
        for property_id, property in tool.inputSchema["properties"].items():
            properties[property_id] = {
                "type": "string",
            }

    # record tool in ollama function spec
    return {
        "type": "function",
        "function": {
            "name": tool.name,   
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": tool.inputSchema["required"] if "required" in tool.inputSchema else None
            },
        },
    }

def builtin_mcp(func):
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return CallToolResult(content=[TextContent(type="text", text=str(result))])
            except Exception as e:
                return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)
        return async_wrapper
    else:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return CallToolResult(content=[TextContent(type="text", text=str(result))])
            except Exception as e:
                return CallToolResult(content=[TextContent(type="text", text=str(e))], isError=True)
        return wrapper