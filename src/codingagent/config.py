import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Callable

from rich.console import Console
from rich.pretty import Pretty

from prompt_toolkit import prompt

from codingagent.packages.tools import (
    ls,
    glob_tool,
    git,
    read,
    write,
)

@dataclass
class Config:
    inference_api_url: str
    model_id: str
    context_size: int
    user_mcp_servers: list[dict]

@dataclass
class ConfigArgs:
    config_path: str
    mcp_command: str
    inference_url: str

BUILTIN_TOOLS: list[Callable[..., Any]] = [
    ls.ls,
    glob_tool.glob_tool,
    git.git,
    read.read_file,
    write.write_tool, 
]

DEFAULT_CONFIG = Config(
    "http://localhost:9090",
    "hf.co/unsloth/Qwen3-8B-GGUF:Q4_K_M",
    128000,
    user_mcp_servers=[]
)

def load_config(config_path: str, args: ConfigArgs) -> Config:
    if config_path == "":
        raise ValueError("no config path found")    
    
    # load config from config file
    config = DEFAULT_CONFIG
    config_updated = False
    try:
        # check if config already exists
        os.stat(config_path)

        # construct config from content
        with open(config_path, "r") as f:
            body = json.loads(f.read())
            config = Config(**body)

    except FileNotFoundError:
        config_updated = True

    except Exception as e:
        print(f"could not check if config file exists: {e}") 
        exit(1)
        
    if args.mcp_command:
        while True:
            try:
                user_result = prompt("Paste configuration (alt+enter to submit): ", multiline=True, vi_mode=True)
                if len(user_result.strip()) < 1:
                    print("please provide configuration")
                    continue
                console = Console()
                result = "{" + user_result + "}"
                server_config: dict = json.loads(result)
                console.print(Pretty(server_config, expand_all=True))
                ok = prompt("Adding mcp server, continue? (y/n)", default="y") 
                if ok != "y":
                    continue
                break
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except Exception as e:
                print("invalid input: ", e)

    if args.inference_url != "":
        config.inference_api_url = args.inference_url
        config_updated = True
        print("updated inference api url")

    # write new config to file
    if config_updated:
        with open(config_path, "w") as f:
            f.write(json.dumps(asdict(config)))

    return config
