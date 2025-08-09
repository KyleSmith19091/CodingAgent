import asyncio
import argparse
from contextlib import AsyncExitStack
from pathlib import Path

from codingagent.config import (
    BUILTIN_TOOLS, 
    Config, 
    ConfigArgs, 
    load_config,
)
from codingagent.packages.agent.agent import Agent
from codingagent.packages.tool_client import (
    mcp_client,
    builtin_mcp_client,
)
from codingagent.packages.agent.inference_engine_client import InferenceEngineClient

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

            # construct inference engine
            engine = InferenceEngineClient(config.inference_api_url)

            # construct agent
            agent = Agent(engine, mcp_client_index, tools)

            # initialise agent
            await agent.init()

            # run it
            await agent.run()

            engine.cleanup()
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