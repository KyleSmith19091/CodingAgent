import json
import os
from typing import Callable

from openai import OpenAI
from openai.types.chat import ChatCompletion
from rich.console import Console

from codingagent.packages.prompts import system_prompt

class InferenceEngineClient:
    def __init__(self, inference_url):
        self.client = OpenAI(base_url=inference_url, api_key="") 
        models = self.client.models.list()
        self.model = models.data[0].id
        self.console = Console(stderr=True)

    def cleanup(self):
        self.client.close()

    async def chat(self, messages, tools, should_think, chunk_callback: Callable, tool_callback: Callable):
        while True:
            tool_calls = []
            thinking = False

            # send current context to model
            chat_completion: ChatCompletion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                stream=True,
                tools=tools,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": should_think},
                    "repetition_penalty": 1.05,
                },
            )

            with self.console.status("Thinking...", spinner="bouncingBall") as status:
                response = []
                for chunk in chat_completion:
                    if chunk.choices[0].delta.tool_calls:
                        tool_calls.extend(chunk.choices[0].delta.tool_calls)
                        continue
                        
                    content = chunk.choices[0].delta.content
                    if not thinking and hasattr(chunk.choices[0].delta, "reasoning_content") and chunk.choices[0].delta.reasoning_content != "":
                        status.stop()
                        thinking = True
                    elif content != None:
                        status.start()
                        thinking = False 

                    # add thinking to context
                    if content != None:
                        response.append(content)
                        
                    # set content to thinking content when the model is thinking before handing off to chunk callback
                    if thinking:
                        content = chunk.choices[0].delta.reasoning_content

                    # callback
                    if content != None:
                        chunk_callback(content, thinking)

            # add assistant content to context
            if len(response) > 0:
                assistant_content = "".join(response)
                messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                }) 

            if len(tool_calls) == 0:
                return messages

            # build tool call index - cause they decided they don't want to do this for us like ollama :(
            # TODO: Gonna do something bad here, going to assume order in the API response, so stuff might break sometimes
            tool_index = []
            for tool_call_chunk in tool_calls:
                idx = tool_call_chunk.index
                
                # this indicates the start of a new function call delta
                if tool_call_chunk.type == "function":
                    function_name = tool_call_chunk.function.name
                    function_id = tool_call_chunk.id
                    tool_index.append({
                        'name': function_name,
                        'id': function_id,
                        'args': '',
                    })
                    # for a delta tool call this all the information we can gather for a single function chunk
                    continue

                # now we are assuming (very bad) that we are getting the arguments for the tool call
                # collecting tool arguments as one big string
                try:
                    tool_index[idx]["args"] += tool_call_chunk.function.arguments
                except IndexError:
                    # this will probably happen if we get the API response got corrupted or it just broke completely
                    # so there's no real point in continuing 
                    raise ValueError("got unexpected tool call chunk for a tool call with no start")

            messages = await self.call_tools(messages, tool_index, tool_callback)

            messages.append({
                "role": "assistant",
                "content": "Interpret the result of the tool calls, IMPORTANT: I should be proactive with calling tools if I think there's still work left. If I think I should call more tools, I should call them immediately."
            })
            # enable thinking for tool call results
            should_think = True

    async def call_tools(self, messages, tool_calls: list[dict], tool_callback: Callable):
        for tool_call in tool_calls:
            try:
                messages.append(await tool_callback(tool_call))
            except Exception as e:
                self.console.print("could not perform all tool calls: ", e)
                messages.append({
                    "role": "tool",
                    "name": tool_call["name"],
                    "tool_call_id": tool_call["id"],
                    "content": f"Error: {e} try again",
                }) 
            finally:
                return messages

    