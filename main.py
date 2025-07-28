import asyncio
from contextlib import AsyncExitStack
import os
from typing import Dict

from ollama import Client
from mcp.types import TextContent
from rich.panel import Panel
from rich.prompt import Prompt
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live

from packages.config import CONTEXT_SIZE, INFERENCE_API_URL, MODEL_ID, TOOL_SERVERS
from packages.tool_client import mcp_client
from packages.prompts import system_prompt

class App:
    def __init__(self, mcp_client_index):
        self.model_client = Client(host=INFERENCE_API_URL)
        self.mcp_client_index: Dict[str, mcp_client.MCPClient] = mcp_client_index
        self.mcp_tool_client_index: Dict[str, str] = {}
        self.tools = []
        self.console = Console()
        self.error_console = Console(stderr=True)
        self.messages= [{
            "role": "system",
            "content": system_prompt.SYSTEM_PROMPT.format(directory=os.getcwd()), 
        }]

    async def init(self):
        self.console.print(Panel("[magenta bold]⛛[/magenta bold]\tHi 👋, I'm [magenta u]M3L[/magenta u]\n\n\t[#9ca0b0]Your friendly AI coding agent, ready to help all your software engineering needs[/#9ca0b0]"))
        self.console.print("")

        await self._setup_tools()

    async def _setup_tools(self):
        # connect to mcp servers
        try:
            for (tool_server_id, tool_client) in self.mcp_client_index.items():
                # append all the tools from the server
                for tool in await tool_client.available_tools():
                    # collect tool parameters
                    properties = {}
                    for property_id, property in tool.inputSchema["properties"].items():
                        properties[property_id] = {
                            "type": "string",
                        }

                    # create index to be able to map a tool to an mcp server
                    self.mcp_tool_client_index[tool.name] = tool_server_id
                        
                    # record tool in ollama function spec
                    self.tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,   
                            "description": tool.description,
                            "parameters": {
                                "type": "object",
                                "properties": properties,
                                "required": tool.inputSchema["required"]
                            },
                        },
                    }) 
        except Exception as e:
            self.notify(f"Error mounting application: {e}", severity="error")

        pass

    async def run(self):
        while True:
            # wait for the user query
            query = Prompt.ask(Text("(Enter your query here)", style="#9ca0b0 bold frame"))    

            if query == "/exit":
                break

            self.messages.append({
                "role": "user",
                "content": query,
            })

            await self.inference(query)
        pass 
    
    def render_markdown(self, content: str):
        self.console.print(Text(content), end="", style="#9ca0b0")
        
    async def inference(self, query: str):
        while True:
            try:
                # stream response
                self.console.print(Markdown("> *Assistant*: "), end="", style="bold cyan")
                with Live(self.render_markdown(""), refresh_per_second=4) as live:
                    thinking = False
                    response = []
                    tool_calls = []
                    for part in self.model_client.chat(MODEL_ID, messages=self.messages, stream=True, think=False, tools=self.tools, options={'num_ctx': CONTEXT_SIZE}):
                        if part.message.tool_calls is not None and len(part.message.tool_calls) > 0:
                            tool_calls.extend({
                                "name": call.function.name, 
                                "args": call.function.arguments
                            } for call in part.message.tool_calls)
                        else:
                            if part.message.content:
                                # check if we are thinking
                                if part.message.content == "<think>":
                                    thinking = True
                                    continue
                                elif part.message.content == "</think>":
                                    thinking = False
                                    continue

                                # display thoughts in slate
                                if thinking:
                                    # self.console.print(Text(part.message.content), end="", style="#9ca0b0")
                                    live.update(self.render_markdown(part.message.content))
                                else:
                                    # collect part of response so we can add it to context later (don't collect thinking)
                                    response.append(part.message.content)

                self.console.print(Markdown("".join(response)))
                self.console.print()

                # add assistant response to history
                assistant_content = "".join(response)
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                })

                # if no tool calls required, we're done
                if len(tool_calls) == 0:
                    return

                with self.console.status("[bold green]Caliing tools...") as status:
                    for tool_call in tool_calls:
                        self.console.log(f"calling tool {tool_call['name']} with args {tool_call['args']}")
                        try:
                            # determine server which hosts the tool
                            server = self.mcp_tool_client_index[tool_call["name"]]
                            if server == "":
                                self.notify(f"tool {tool_call['name']} not found", severity="error")
                                raise ValueError("could not find tool")

                            # determine client we can use to interact with the server
                            client = self.mcp_client_index[server]
                            if client == None:
                                self.notify(f"client not found for server {server}", severity="error")
                                raise ValueError("could not find client for server")

                            # call tool
                            tool_result_content = await client.call_tool(
                                tool_call["name"], 
                                tool_call["args"]
                            )
                            
                            # collect result content
                            tool_result = ""
                            for block in tool_result_content.content:
                                if isinstance(block, TextContent):
                                    tool_result = tool_result + block.text
                            
                            # add tool result to history
                            self.messages.append({
                                "role": "tool",
                                "content": tool_result,
                                "tool_name": tool_call["name"]
                            })

                        except Exception as e:
                            self.error_console.log(f"error during tool execution of {tool_call['name']} error: {e}", style="bold red")
                            self.messages.append({
                                "role": "tool",
                                "content": f"Error: {e}",
                                "tool_name": tool_call["name"]
                            })

            except Exception as e:
                self.error_console.log(f"inference error: {e}", style="bold red")
                raise ValueError("inference error")
        pass
        
async def main():
    mcp_client_index = {}
    try:
        async with AsyncExitStack() as stack:
            for tool_server in TOOL_SERVERS:
                client = mcp_client.MCPClient()
                
                # connect to server
                await client.connect_to_server(tool_server)

                # register client for later use
                mcp_client_index[tool_server] = client

                # ensure cleanup is correct
                stack.push_async_callback(client.__aexit__, None, None, None)

            app = App(mcp_client_index) 
            await app.init()
            await app.run()
    except (ValueError, KeyboardInterrupt, asyncio.CancelledError):
        print("Shutdown requested")
    finally:
        print("Bye!")

    pass

if __name__ == "__main__":
    asyncio.run(main())