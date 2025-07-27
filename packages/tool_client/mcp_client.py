from contextlib import AsyncExitStack
from typing import List, Optional

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        pass

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        # confirm that the server is a script that we can execute
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        # set command to use either python or node as executor
        command = "uv" if is_python else "node"
        args = [server_script_path]

        if command == "uv":
            args.insert(0, "run")

        # construct parameters so we can construct a client to interact with the 'server'
        server_params = StdioServerParameters(
            command=command,
            args=["run", server_script_path],
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


