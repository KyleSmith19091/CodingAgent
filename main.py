import asyncio
from contextlib import AsyncExitStack
import json
import logging
import os
from typing import Callable, Dict

from ollama import Client, Tool
from mcp.types import TextContent
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.scroll_view import ScrollView
from textual.widgets import Markdown, Input, Collapsible, Label
from textual.binding import Binding
from textual.widgets import RichLog
from textual.reactive import reactive
from textual import render

from packages.tool_client import mcp_client
from packages.prompts import system_prompt

logging.getLogger("fastmcp").setLevel(logging.CRITICAL)

INFERENCE_API_URL = "http://localhost:9090"
MODEL_ID = "qwen3:8b"

HEADER = """
## M3L

> I'm a friendly coding agent, ready to help you with your software engineering tasks.
"""

tool_servers = [
    "./packages/tools/read.py",
    "./packages/tools/ls.py",  
    "./packages/tools/glob_tool.py",  
    "./packages/tools/write.py",  
]

class AssistantMarkdown(Markdown):
    
    content = reactive("content", layout=True)

    def render(self):
        return Markdown(self.content).render() 

class AgentApp(App):
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+d", "quit", "Quit", priority=True),
    ]

    CSS = """
    #chat-container {
       height: 1fr;
    }

    #input-container {
        align-vertical: bottom; 
        height: 3;
        margin: 1;
    }

    .assistant-message {
        background: $secondary 20%;
        margin: 1;
        padding: 1;
        border-left: thick $secondary;
    }

    .tool-message {
        background: $warning 20%;
        margin: 1;
        padding: 1;
        border-left: thick $warning;
    }

    .error-message {
        background: $error 20%;
        margin: 1;
        padding: 1;
        border-left: thick $error;
    }

    .toggle {
        border-top: $secondary 20%;
        background: $secondary 20%;
        width: 100%;
    }

    .user-message {
       margin: 1;
       padding: 1; 
    }
    """

    def __init__(self, mcp_client_index: Dict[str, mcp_client.MCPClient]):
        super().__init__()
        self.theme = "tokyo-night"
        self.messages = [{
            "role": "system",
            "content": system_prompt.SYSTEM_PROMPT.format(directory=os.getcwd()), 
        }]
        self.current_assistant_content = []
        self.current_markdown = None
        self.current_thinking_content = []
        self.current_thinking_markdown = None
        self.client = None
        self.mcp_client_index: Dict[str, mcp_client.MCPClient] = mcp_client_index
        self.mcp_tool_client_index: Dict[str, str] = {}
        self.tools = []
        self.processing = False
        self.thinking = False 

    async def on_mount(self) -> None:
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
        
        # construct client
        self.client = Client(host=INFERENCE_API_URL)

    def compose(self) -> ComposeResult:
        """create widgets for the app"""
        with Vertical():
            yield Markdown(f"# M3L\nWelcome! What can I help with?")
            yield VerticalScroll(id="chat-container", classes="assistant-message")
            with Horizontal(id="input-container"):
                yield Input(placeholder="Type your message here..." if not self.processing else "thinking...", id="user-input", disabled=self.processing)
    
    async def add_user_message(self, content: str):
        """Add a user message to the chat display."""
        chat_container = self.query_one("#chat-container")
        user_markdown = Markdown(f"**You:** {content}", classes="user-message")
        await chat_container.mount(user_markdown)
        chat_container.scroll_end(animate=False)
        
    async def add_assistant_message_start(self):
        """Start a new assistant message."""
        chat_container = self.query_one("#chat-container")
        self.current_markdown = Markdown("**Assistant**: Working on it...")
        await chat_container.mount(self.current_markdown)
        self.current_assistant_content = []
        # chat_container.scroll_end(animate=False)
        chat_container.anchor(True)

    @work()
    async def update_assistant_message(self, new_content: str):
        """Update the current assistant message with streaming content."""
        if self.current_markdown:
            if new_content == "<think>":
                self.thinking = True
            elif new_content == "</think>":
                self.thinking = False
                self.current_thinking_content = []
                self.current_thinking_markdown = None

            if self.thinking and new_content == "<think>":
                self.current_thinking_markdown = Label("".join(self.current_thinking_content), shrink=True, disabled=True)
                self.current_markdown.mount(
                    Collapsible(self.current_thinking_markdown, classes="toggle", title="Thoughts")
                )
            elif self.thinking:
                self.current_thinking_content.append(new_content)
                self.current_thinking_markdown.update("".join(self.current_thinking_content))
                self.current_markdown.update(
                    Collapsible(self.current_thinking_markdown, classes="toggle", title="Thoughts")
                )
                full_content = "**Assistant:** Thinking..."
                await self.current_markdown.update(full_content)
            else:
                self.current_assistant_content.append(new_content)
                content = self.current_assistant_content
                if len(content) == 0:
                    content = ["Working on it..."]
                full_content = "**Assistant:** " + "".join(content)
                # Update the markdown content
                await self.current_markdown.update(full_content)

            # Force scroll to bottom after content update
            chat_container = self.query_one("#chat-container")
            chat_container.scroll_end(animate=False)

    async def add_tool_message(self, tool_name: str, args, is_error: bool):
        """Add a tool execution result to the chat."""
        chat_container = self.query_one("#chat-container")
        if not is_error:
            tool_markdown = Markdown(f"**Tool**: Executed tool {tool_name} with args {args}", classes="tool-message")
        else:
            tool_markdown = Markdown(f"**Tool**: Error during tool execution for {tool_name}: {args}", classes="error-message")
    
        await chat_container.mount(tool_markdown)
        chat_container.scroll_end(animate=False)
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle when the user submits input."""
        if not event.value.strip():
            return
            
        user_message = event.value.strip()
        event.input.value = ""

        user_input = self.query_one("#user-input")
        user_input.disabled = True
        user_input.placeholder = "thinking..."
        
        # Add user message to chat
        await self.add_user_message(user_message)
        
        # Add user message to conversation history
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Process the message
        await self.process_conversation()

    async def process_conversation(self):
        """Process the conversation with the AI assistant."""
        if not self.client:
            self.notify("Client not initialized", severity="error")
            return
        
        self.processing = True
            
        tool_calls = []
        # inference loop
        while True:
            # add initial assistant message
            await self.add_assistant_message_start()
            
            try:
                # run inference with streaming
                response = []
                for part in self.client.chat(MODEL_ID, messages=self.messages, stream=True, think=True, tools=self.tools, options={'num_ctx': 32000}):
                    if part.message.tool_calls is not None and len(part.message.tool_calls) > 0:
                        tool_calls.extend({
                            "name": call.function.name, 
                            "args": call.function.arguments
                        } for call in part.message.tool_calls)
                    else:
                        if part.message.content:
                            response.append(part.message.content)
                            self.update_assistant_message(part.message.content)
                
                # add assistant response to history
                assistant_content = "".join(response)
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                })
                
                # if no tool calls required, we're done
                if len(tool_calls) == 0:
                    break
                
                # execute tool calls
                for tool_call in tool_calls:
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
                        
                        # add tool result to chat display
                        await self.add_tool_message(tool_call["name"], tool_call["args"], is_error=False)
                        
                        # add tool result to history
                        self.messages.append({
                            "role": "tool",
                            "content": tool_result,
                            "tool_name": tool_call["name"]
                        })
                    except Exception as e:
                        self.notify(f"Tool execution error: {e}", severity="error")
                        await self.add_tool_message(tool_call["name"], f"Error: {e}", is_error=True)
                
                tool_calls = []
                
            except Exception as e:
                self.notify(f"Inference error: {e}", severity="error")
                break
            finally:
                self.processing = False
                user_input = self.query_one("#user-input")
                user_input.disabled = False
                user_input.placeholder = "Type your message here..."

    async def on_unmount(self) -> None:
        logging.info("unmounting application")

    pass

async def main():
    mcp_client_index = {}
    try:
        async with AsyncExitStack() as stack:
            for tool_server in tool_servers:
                client = mcp_client.MCPClient()
                
                # connect to server
                await client.connect_to_server(tool_server)

                # register client for later use
                mcp_client_index[tool_server] = client

                # ensure cleanup is correct
                stack.push_async_callback(client.__aexit__, None, None, None)

            app = AgentApp(mcp_client_index) 
            await app.run_async()
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Shutdown requested")

if __name__ == "__main__":
    asyncio.run(main())
