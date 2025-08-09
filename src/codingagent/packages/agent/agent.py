import json
import os
from typing import Dict

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from rich.tree import Tree
from rich.syntax import Syntax
from prompt_toolkit import PromptSession
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.patch_stdout import patch_stdout
from fastmcp.exceptions import ToolError
from mcp.types import TextContent

from codingagent.packages.prompts import system_prompt
from codingagent.packages.tool_client import mcp_client
from codingagent.packages.agent.inference_engine_client import InferenceEngineClient
from codingagent.packages.tools import (
    bash,
    edit,
    read,
    write
) 

completer = NestedCompleter.from_nested_dict({
    "/exit": None,
})

class Agent:
    def __init__(self, engine: InferenceEngineClient, mcp_client_index: Dict[str, mcp_client.MCPClient], tools: list):
        self.engine = engine
        self.tools = tools
        self.mcp_client_index = mcp_client_index
        self.console = Console()
        self.error_console = Console(stderr=True)
        self.session = PromptSession()
        self.current_output = []
        self.messages= [{
            "role": "system",
            "content": system_prompt.SYSTEM_PROMPT.format(directory=os.getcwd()), 
        }]
        pass

    async def init(self):
        self.console.print(Panel(f"[magenta bold]⛛[/magenta bold]   Hi 👋, I'm [magenta u]M3L[/magenta u]\n\n[#9ca0b0]Your friendly AI coding agent, ready to help all your software engineering needs\n\ncwd: {os.getcwd()}[/#9ca0b0]", border_style="bold magenta", width=60))
        self.console.print("")
        self.console.print("[bold red u]Ensure gcloud proxy is running[/bold red u]")
        self.console.print("")
        self.console.print(Markdown("--- Tips ---"))
        self.console.print("[#303446]1.[/#303446] [#9ca0b0]Add \\think to your prompt to enable extended thinking (great for complex tasks!)[/#9ca0b0]")
        self.console.print("[#303446]2.[/#303446] [#9ca0b0]Type /exit to end session[/#9ca0b0]")
        self.console.print("")        

    async def run(self):
        while True:
            # wait for the user query
            with patch_stdout():
                query = await self.session.prompt_async("(⌥ + ↵ to submit) > ", completer=completer, multiline=True, cursor=CursorShape.BLINKING_BEAM) 

            # parse query
            if query == "/exit":
                break

            # add nothink by default 
            should_think = False
            if "\\think" in query:
                should_think = True

            # append user message
            self.messages.append({
                "role": "user",
                "content": query,
            })

            # clear output
            self.current_output = []
            
            # call engine
            try:
                self.messages = await self.engine.chat(self.messages, self.tools, should_think, self.handle_content, self.handle_tool)
            except Exception as e:
                self.error_console.print(f"error during chat: {e}")
                raise e

            # print markdown content if found
            if len(self.current_output) != 0:
                self.console.print(
                    Panel(Markdown("".join(self.current_output)), title="Assistant", padding=1)
                )

        pass 

    def handle_content(self, content: str, thinking: bool):
        if thinking:
            self.console.print(Text(content, style="#9ca0b0", end=""), end="")
        else:
            self.current_output.append(content)

    async def handle_tool(self, tool_call: dict):
        try:
            args = json.loads(tool_call["args"])
        except Exception as e:
            self.console.print(Text(f"tool arguments malformed ({tool_call["args"]}): {e}", justify="center", style="bold #e78284"))
            raise ValueError(f"argument are expected to be valid json({tool_call["args"]}): {e}") 
    
        content = Panel(Markdown(f"- Calling tool `{tool_call['name']}` with args `{tool_call['args']}`"), title="Tool Call")
        if tool_call["name"] == read.read_file.__name__:
            tree = Tree(label=Markdown("**📁 Read**", style="#ef9f76"))
            tree.add(Text(f'{args["file_path"]}', style="underline"))
            content = Panel(tree, title="Read", style="#85c1dc")
        elif tool_call["name"] == edit.edit_tool.__name__:
            tree = Tree(label=Markdown("**📁 Edit**", style="#81c8be"))
            tree.add(Text(f'{args["path"]}', style="underline"))
            tree.add(Text(f'{args["old_string"]}', style="#e78284"))
            tree.add(Text(f'{args["new_string"]}', style="#a6d189"))
            content = Panel(tree, title="Edit", style="#85c1dc")
        elif tool_call["name"] == write.write_tool.__name__:
            tree = Tree(label=Markdown("**📁 Write**", style="#f4b8e4"))
            tree.add(Text(f'{args["file_path"]}', style="underline"))
            tree.add(Syntax(f'{args["content"]}', lexer="text", line_numbers=True))
            content = Panel(tree, title="Read", style="#85c1dc")
        elif tool_call["name"] == bash.bash.__name__:
            tree = Tree(label=Markdown("**Bash**", style="#8caaee"))
            tree.add(Syntax(f'{args["command"]}', lexer="bash"))
            content = Panel(tree, title="Bash", style="#85c1dc")
                
        self.console.print(content)

        try:
            client = self.mcp_client_index[tool_call["name"]]
        except KeyError:
            raise ValueError(f"can not find client for tool {tool_call["name"]}")

        try:
            # call tool
            tool_result_content = await client.call_tool(
                tool_call["name"], 
                args,
            )

            # collect result content
            tool_result = ""
            for block in tool_result_content.content:
                if isinstance(block, TextContent):
                    tool_result = tool_result + block.text

            # add tool result to history
            return {
                "role": "tool",
                "name": tool_call["name"],
                "tool_call_id": tool_call["id"],
                "content": tool_result,
            }
        except ToolError as t:
            self.error_console.print(Markdown(f"- error during tool execution of {tool_call['name']} error: {t}", style="bold red"))
            return {
                "role": "tool",
                "name": tool_call["name"],
                "tool_call_id": tool_call["id"],
                "content": f"Error: {e}",
            } 
        except Exception as e:
            self.error_console.print(Markdown(f"- unknown error during tool execution of {tool_call['name']} error: {e} with type {type(e)}", style="bold red"))
            return {
                "role": "tool",
                "name": tool_call["name"],
                "tool_call_id": tool_call["id"],
                "content": f"Error: {e}",
            }