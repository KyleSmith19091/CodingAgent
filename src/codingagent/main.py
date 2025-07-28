import asyncio
from contextlib import AsyncExitStack
import os
from typing import Dict
import argparse
from pathlib import Path
import json
from dataclasses import asdict

from ollama import Client
from mcp.types import TextContent
from rich.panel import Panel
from rich.prompt import Prompt
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live

from codingagent.packages.config import DEFAULT_CONFIG, Config
from codingagent.packages.tool_client import mcp_client
from codingagent.packages.prompts import system_prompt

class App:
    def __init__(self, mcp_client_index, config: Config):
        self.is_sub_agent = False
        self.model_client = Client(host=config.inference_api_url)
        self.mcp_client_index: Dict[str, mcp_client.MCPClient] = mcp_client_index
        self.mcp_tool_client_index: Dict[str, str] = {}
        self.tools = []
        self.console = Console()
        self.error_console = Console(stderr=True)
        self.config = config
        self.messages= [{
            "role": "system",
            "content": system_prompt.SYSTEM_PROMPT.format(directory=os.getcwd()), 
        }]

    async def init(self):
        if not self.is_sub_agent:
            self.console.print(Panel("[magenta bold]⛛[/magenta bold]\tHi 👋, I'm [magenta u]M3L[/magenta u]\n\n\t[#9ca0b0]Your friendly AI coding agent, ready to help all your software engineering needs[/#9ca0b0]", border_style="bold magenta"))
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

    async def run(self, query: str = ""):
        while True:
            # wait for the user query
            if not self.is_sub_agent:
                query = Prompt.ask(Text("✿ (Query)", style="#8839ef bold"))    

            # parse query
            if query == "/exit":
                break

            # add nothink by default 
            if "\\think" not in query:
               query += " \\nothink" 

            # append user message
            self.messages.append({
                "role": "user",
                "content": query,
            })

            # run inference on history
            await self.inference()
        pass 
    
    def render_markdown(self, content: str):
        self.console.print(Text(content), end="", style="#9ca0b0")
        
    async def inference(self):
        while True:
            try:
                # stream response
                self.console.print(Markdown("> *Assistant*: "), end="", style="bold cyan")
                thinking = False
                response = []
                thoughts = []
                tool_calls = []
                for part in self.model_client.chat(self.config.model_id, messages=self.messages, stream=True, think=False, tools=self.tools, options={'num_ctx': self.config.context_size}):
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
                                thoughts.append(part.message.content)
                                self.console.print(Text("".join(part.message.content), style="#9ca0b0"), end="")
                            else:
                                # collect part of response so we can add it to context later (don't collect thinking)
                                response.append(part.message.content)

                self.console.print()
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
    homePath = Path.home()    

    parser = argparse.ArgumentParser()    
    parser.add_argument("-c", "--config", help="Absolute path to config file", default=f"{homePath}/.codingagent_config")
    parser.add_argument("-add", "--add-mcp", help="Add mcp command")
    parser.add_argument("-inf-url", "--inference-url", help="API URL where model is hosted")

    args = parser.parse_args()

    config_path = args.config
    config = DEFAULT_CONFIG 

    # read config
    try:
        # check if config already exists
        os.stat(config_path)

        # construct config from content
        with open(config_path, "r") as f:
            body = json.loads(f.read())
            config = Config(**body)
    except FileNotFoundError:
        # create config file
        with open(config_path, "w") as f:
            f.write(json.dumps(asdict(config)))
    except Exception as e:
        print(f"could not check if config file exists: {e}") 
        exit(1)

    # add mcp server
    if args.add_mcp != None:
        config.tool_server.append(args.add_mcp)
        with open(config_path, "w") as f:
            f.write(json.dumps(config))
        print(f"Added mcp: {args.add_mcp}")
        exit(0)

    # update inference url        
    if args.inference_url != None:
        config.inference_api_url = args.inference_url
        with open(config_path, "w") as f:
            f.write(json.dumps(config))
        print(f"Updated inference url: {args.inference_url}")
        exit(0)

    mcp_client_index = {}
    try:
        async with AsyncExitStack() as stack:
            for tool_server in config.tool_server:
                client = mcp_client.MCPClient()
                
                # connect to server
                await client.connect_to_server(tool_server.split(" "))

                # register client for later use
                mcp_client_index[tool_server] = client

                # ensure cleanup is correct
                stack.push_async_callback(client.__aexit__, None, None, None)

            app = App(mcp_client_index, config) 
            await app.init()
            await app.run()
    except ValueError as e:
        print("Something went wrong: ", e)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Shutdown requested")
        # Explicitly cancel all tasks
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        print("Bye!")
    pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Done {e}")