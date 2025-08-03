from contextlib import AsyncExitStack

from fastmcp import Client

from codingagent.packages.tools.tool import ollama_tool_from_mcp_tool

class MCPClient:
    def __init__(self):
        self.client = None 
        self.exit_stack = AsyncExitStack()
        self._connected = False

    async def connect_to_server(self, server_command: str) -> list:
        """Connect to an MCP server

        Args:
            server_command: py file to 
        """

        self.client = await self.exit_stack.enter_async_context(
            Client(server_command)
        )
        await self.client.ping() 
        self._connected = True
        tools = await self.client.list_tools() 

        return [ollama_tool_from_mcp_tool(tool) for tool in tools]
            
    async def call_tool(self, tool_name, tool_args):
        return await self.client.call_tool(tool_name, tool_args)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._connected:
            await self.client.close()
            await self.exit_stack.aclose()


