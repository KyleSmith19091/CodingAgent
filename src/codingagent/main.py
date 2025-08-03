import asyncio
import os
import argparse
import json
from contextlib import AsyncExitStack
from typing import Dict 
from pathlib import Path

from ollama import Client
from mcp.types import TextContent
from fastmcp.exceptions import ToolError
from rich.panel import Panel
from rich.prompt import Prompt
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from rich.progress import Progress
from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.patch_stdout import patch_stdout

from codingagent.config import (
    BUILTIN_TOOLS, 
    Config, 
    ConfigArgs, 
    load_config,
)
from codingagent.packages.prompts import system_prompt
from codingagent.packages.tool_client import (
    mcp_client,
    builtin_mcp_client,
)

completer = NestedCompleter.from_nested_dict({
    "/exit": None,
    "/plan": None,
})

class App:
    def __init__(self, mcp_client_index: Dict[str, mcp_client.MCPClient], tools: list, config: Config):
        self.is_sub_agent = False
        self.model_client = Client(host=config.inference_api_url)
        self.mcp_client_index: Dict[str, mcp_client.MCPClient] = mcp_client_index
        self.mcp_tool_client_index: Dict[str, str] = {}
        self.tools = tools
        self.console = Console()
        self.session = PromptSession()
        self.error_console = Console(stderr=True)
        self.config = config
        self.messages= [{
            "role": "system",
            "content": system_prompt.SYSTEM_PROMPT.format(directory=os.getcwd()), 
        }]

    async def init(self):
        if not self.is_sub_agent:
            self.console.print(Panel(f"[magenta bold]⛛[/magenta bold]   Hi 👋, I'm [magenta u]M3L[/magenta u]\n\n[#9ca0b0]Your friendly AI coding agent, ready to help all your software engineering needs\n\ncwd: {os.getcwd()}[/#9ca0b0]", border_style="bold magenta", width=60))
            self.console.print("")
            self.console.print("[bold red u]Ensure gcloud proxy is running[/bold red u]")
            self.console.print("")
            self.console.print(Markdown("--- Tips ---"))
            self.console.print("[#303446]1.[/#303446] [#9ca0b0]Add \\think to your prompt to enable extended thinking (great for complex tasks!)[/#9ca0b0]")
            self.console.print("[#303446]2.[/#303446] [#9ca0b0]Type /exit to end session[/#9ca0b0]")
            self.console.print("")

    async def run(self, query: str = ""):
        while True:
            # wait for the user query
            if not self.is_sub_agent:
                with patch_stdout():
                    query = await self.session.prompt_async("> ", completer=completer, vi_mode=True) 

            # parse query
            if query == "/exit":
                break

            if query == "/plan":
                break

            # add nothink by default 
            should_think = True
            if "\\think" not in query:
               should_think = False
               query += " \\nothink" 

            # append user message
            self.messages.append({
                "role": "user",
                "content": query,
            })

            # run inference on history
            await self.inference(should_think)
        pass 
    
    def stream_response(self):
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

        return response, tool_calls
    
    async def call_tools(self, tools):
        with self.console.status("[bold green]Calling tools...") as status:
            for tool_call in tools:
                self.console.print(Markdown(f"- Calling tool `{tool_call['name']}` with args `{tool_call['args']}`"))
                # determine client we can use to interact with the server
                try:
                    client = self.mcp_client_index[tool_call["name"]]
                except KeyError:
                    raise ValueError(f"can not find client for tool {tool_call["name"]}")

                # call tool and collect result
                try:

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

                except ToolError as t:
                    self.error_console.print(Markdown(f"- error during tool execution of {tool_call['name']} error: {t}", style="bold red"))
                    self.messages.append({
                        "role": "tool",
                        "content": f"Error: {e}",
                        "tool_name": tool_call["name"]
                    }) 
                except Exception as e:
                    self.error_console.print(Markdown(f"- error during tool execution of {tool_call['name']} error: {e} with type {type(e)}", style="bold red"))
                    self.messages.append({
                        "role": "tool",
                        "content": f"Error: {e}",
                        "tool_name": tool_call["name"]
                    })
        pass
    
    async def inference(self, should_think: bool):
        while True:
            try:
                # stream response
                if should_think:
                    response, tool_calls = self.stream_response() 
                else:
                    counter = 0
                    with self.console.status(f"Thinking...{counter}"):
                        response, tool_calls = self.stream_response() 
                    
                if len(response) != 0:
                    self.console.print(Markdown("".join(response)))

                # add assistant response to history
                assistant_content = "".join(response)
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                })

                # if no tool calls required, we're done
                if len(tool_calls) == 0:
                    return

                await self.call_tools(tool_calls)                

            except Exception as e:
                self.error_console.log(f"inference error: {e}", style="bold red")
                raise ValueError("inference error")
        pass
        
async def main(config: Config):
    mcp_client_index = {}
    mcp_client_builtin = builtin_mcp_client.BuiltinMCPClient(BUILTIN_TOOLS)
    try:
        # add builtin tools to index
        tools = await mcp_client_builtin.connect_to_server()
        for tool in tools:
            mcp_client_index[tool["function"]["name"]] = mcp_client_builtin

        # add async context for user defined tools
            async with AsyncExitStack() as stack:
                if len(config.user_mcp_servers) > 0:
                    for server_config in config.user_mcp_servers:
                        # construct client
                        client = mcp_client.MCPClient()

                        # setup
                        server_tools = await client.connect_to_server(server_config)

                        # map each tool to its respective client
                        for tool in server_tools:
                            mcp_client_index[tool["function"]["name"]] = client

                        # add tools to available tools list
                        tools.extend(server_tools)

                        # push exit call to stack so we can cleanup later
                        stack.push_async_callback(client.__aexit__, None, None, None)

                # construct app
                app = App(mcp_client_index, tools, config) 

                # initialise app
                await app.init()

                # run it
                await app.run()

                # for client in mcp_client_index.values():
                #     await client.cleanup()

                raise KeyboardInterrupt
    except ValueError as e:
        print("Something went wrong: ", e)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Shutdown requested")
    finally:
        # explicitly cancel all tasks
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        print("Bye!")
    pass

if __name__ == "__main__":
    try:
        homePath = Path.home()    

        parser = argparse.ArgumentParser()    
        parser.add_argument("-c", "--config", help="Absolute path to config file", default=f"{homePath}/.codingagent_config")
        parser.add_argument("-add", "--add-mcp", help="Add mcp command", default=False, action="store_true")
        parser.add_argument("-inf-url", "--inference-url", help="API URL where model is hosted", default="")
        args = parser.parse_args()

        # load config
        config = load_config(config_path=args.config, args=ConfigArgs(
            config_path=args.config,
            mcp_command=args.add_mcp,
            inference_url=args.inference_url,
        ))

        asyncio.run(main(config))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("something went wrong: ", e)
        pass