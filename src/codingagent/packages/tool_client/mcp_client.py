from contextlib import AsyncExitStack
from typing import List, Optional

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        pass

    async def connect_to_server(self, server_command: list[str]):
        """Connect to an MCP server

        Args:
            server_command: full command to run mcp server
        """

        # validate command (not sure if more need to be checked)
        if server_command[0] not in ["uv", "python", "python3", "npx"]:
            raise ValueError(f"command {server_command[0]} not supported")

        # construct parameters so we can construct a client to interact with the 'server'
        server_params = StdioServerParameters(
            command=server_command[0],
            args=server_command[1:],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        
        # set session
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        # initialise session
        await self.session.initialize()

    async def available_tools(self) -> List[Tool]:
        response = await self.session.list_tools()
        return response.tools
    
    async def call_tool(self, tool_name, tool_args):
        return await self.session.call_tool(tool_name, tool_args)

    async def cleanup(self):
        await self.exit_stack.aclose()
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.exit_stack.aclose()


