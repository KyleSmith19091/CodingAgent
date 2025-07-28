INFERENCE_API_URL = "http://localhost:9090"
MODEL_ID = "hf.co/unsloth/Qwen3-8B-GGUF:Q4_K_M"
CONTEXT_SIZE = 16000 # from https://huggingface.co/unsloth/Qwen3-14B-unsloth-bnb-4bit
TOOL_SERVERS = [
    "./packages/tools/read.py",
    "./packages/tools/ls.py",  
    "./packages/tools/glob_tool.py",  
    "./packages/tools/write.py",  
]