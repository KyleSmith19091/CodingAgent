import asyncio

from ollama import Client 
from mcp.types import TextContent
from textual.app import App, ComposeResult
from textual.widgets import Markdown, Input 
from textual.scroll_view import ScrollView
from textual.containers import Vertical, Horizontal
from textual.binding import Binding

from packages.tool_client import mcp_client

INFERENCE_API_URL = "http://localhost:9090"

class ChatApp(App):
    """A Textual app for chatting with an AI assistant."""
    
    CSS = """
    #chat-container {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    #input-container {
        height: 3;
        margin: 1;
    }
    
    #user-input {
        width: 1fr;
    }
    
    .user-message {
        background: $primary 20%;
        margin: 1;
        padding: 1;
        border-left: thick $primary;
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
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+d", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__()
        self.messages = []
        self.current_assistant_content = []
        self.current_markdown = None
        self.client = None
        self.read_client = None
        self.tools = []
        
    async def on_mount(self) -> None:
        """Initialize the MCP client and tools when the app starts."""
        await self.setup_tools()
        
    async def setup_tools(self):
        """Setup MCP client and tools."""
        self.read_client = mcp_client.MCPClient()
        try:
            # connect to mcp server providing read tool
            await self.read_client.connect_to_server("./packages/tools/read.py")
            
            # append all the tools from the server
            for tool in await self.read_client.available_tools():
                # collect tool parameters
                properties = {}
                for property_id, property in tool.inputSchema["properties"].items():
                    properties[property_id] = {
                        "type": "string",
                    }
                
                # construct Ollama Tool
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
            self.notify(f"Error setting up tools: {e}", severity="error")
            
        # create ollama client
        self.client = Client(host=INFERENCE_API_URL)
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Vertical():
            with ScrollView(id="chat-container"):
                yield Markdown("# AI Chat Assistant\nWelcome! Type your message below and press Enter.", 
                             classes="assistant-message")
            with Horizontal(id="input-container"):
                yield Input(placeholder="Type your message here...", id="user-input")
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle when the user submits input."""
        if not event.value.strip():
            return
            
        user_message = event.value.strip()
        event.input.value = ""
        
        # Add user message to chat
        await self.add_user_message(user_message)
        
        # Add user message to conversation history
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Process the message
        await self.process_conversation()
    
    async def add_user_message(self, content: str):
        """Add a user message to the chat display."""
        chat_container = self.query_one("#chat-container")
        user_markdown = Markdown(f"**You:** {content}", classes="user-message")
        await chat_container.mount(user_markdown)
        # Force scroll to bottom after mounting
        self.call_after_refresh(lambda: chat_container.scroll_end(animate=True))
    
    async def add_assistant_message_start(self):
        """Start a new assistant message."""
        chat_container = self.query_one("#chat-container")
        self.current_markdown = Markdown("**Assistant:** ", classes="assistant-message")
        await chat_container.mount(self.current_markdown)
        # Force scroll to bottom after mounting
        self.call_after_refresh(lambda: chat_container.scroll_end(animate=True))
        self.current_assistant_content = []
    
    async def update_assistant_message(self, new_content: str):
        """Update the current assistant message with streaming content."""
        if self.current_markdown:
            self.current_assistant_content.append(new_content)
            full_content = "**Assistant:** " + "".join(self.current_assistant_content)
            # Update the markdown content
            await self.current_markdown.update(full_content)
            
            # Force scroll to bottom after content update
            chat_container = self.query_one("#chat-container")
            self.call_after_refresh(lambda: chat_container.scroll_end(animate=False))
    
    async def add_tool_message(self, tool_name: str, content: str):
        """Add a tool execution result to the chat."""
        chat_container = self.query_one("#chat-container")
        # Truncate long tool results for display
        display_content = content[:500] + "..." if len(content) > 500 else content
        tool_markdown = Markdown(f"**Tool ({tool_name}):** ```\n{display_content}\n```", 
                               classes="tool-message")
        await chat_container.mount(tool_markdown)
        # Force scroll to bottom after mounting
        self.call_after_refresh(lambda: chat_container.scroll_end(animate=True))
    
    async def process_conversation(self):
        """Process the conversation with the AI assistant."""
        if not self.client:
            self.notify("Client not initialized", severity="error")
            return
            
        tool_calls = []
        
        # inference loop
        while True:
            await self.add_assistant_message_start()
            
            try:
                # run inference with streaming
                for part in self.client.chat("qwen3:8b", messages=self.messages, stream=True, tools=self.tools):
                    if part.message.tool_calls is not None and len(part.message.tool_calls) > 0:
                        tool_calls.extend({
                            "name": call.function.name, 
                            "args": call.function.arguments
                        } for call in part.message.tool_calls)
                    else:
                        if part.message.content:
                            await self.update_assistant_message(part.message.content)
                
                # add assistant response to history
                assistant_content = "".join(self.current_assistant_content)
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
                        # call tool
                        tool_result_content = await self.read_client.call_tool(
                            tool_call["name"], 
                            tool_call["args"]
                        )
                        
                        # collect result content
                        tool_result = ""
                        for block in tool_result_content.content:
                            if isinstance(block, TextContent):
                                tool_result = tool_result + block.text
                        
                        # add tool result to chat display
                        await self.add_tool_message(tool_call["name"], tool_result)
                        
                        # add tool result to history
                        self.messages.append({
                            "role": "tool",
                            "content": tool_result,
                            "tool_name": tool_call["name"]
                        })
                    except Exception as e:
                        self.notify(f"Tool execution error: {e}", severity="error")
                        await self.add_tool_message(tool_call["name"], f"Error: {e}")
                
                tool_calls = []
                
            except Exception as e:
                self.notify(f"Inference error: {e}", severity="error")
                break
    
    async def on_unmount(self) -> None:
        """Cleanup when the app is closing."""
        if self.read_client:
            await self.read_client.cleanup()

async def main():
    """Run the chat application."""
    app = ChatApp()
    await app.run_async()

if __name__ == "__main__":
    asyncio.run(main())