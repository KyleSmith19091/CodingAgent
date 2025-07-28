from dataclasses import dataclass

@dataclass
class Config:
    inference_api_url: str
    model_id: str
    context_size: int
    tool_server: list[str]

DEFAULT_CONFIG = Config(
    "http://localhost:9090",
    "hf.co/unsloth/Qwen3-8B-GGUF:Q4_K_M",
    32000,
    [
        "uv run --with mcp /Users/kylesmith/Development/codingagent/src/codingagent/packages/tools/ls.py",    
        "uv run --with mcp /Users/kylesmith/Development/codingagent/src/codingagent/packages/tools/glob_tool.py",    
        "uv run --with mcp /Users/kylesmith/Development/codingagent/src/codingagent/packages/tools/read.py",    
        "uv run --with mcp /Users/kylesmith/Development/codingagent/src/codingagent/packages/tools/write.py",    
        "uv run --with mcp /Users/kylesmith/Development/codingagent/src/codingagent/packages/tools/git.py",    
    ],
)

