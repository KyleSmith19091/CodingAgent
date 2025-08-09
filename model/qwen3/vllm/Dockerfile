# # Use the official vLLM Docker image as the base
# FROM vllm/vllm-openai:v0.10.0

# WORKDIR /model

# ENV HF_HOME=./

# # Copy model
# COPY Qwen3-8B-Q4_K_M.gguf ./Qwen3-8B-Q4_K_M.gguf

# # Copy config.json  
# COPY config.json ./config.json 

# # Expose the port for vLLM server
# EXPOSE 8080

# # Command to start the vLLM server with bitsandbytes quantization and YaRN scaling
# ENTRYPOINT [ "vllm", "serve", "./Qwen3-8B-Q4_K_M.gguf", "--host", "0.0.0.0", "--port", "8080", "--max-model-len", "131072", "--rope-scaling", "{\"type\":\"yarn\",\"factor\":4.0,\"original_max_position_embeddings\":32768}", "--served-model-name", "Qwen3-8B" ]

# Use the official vLLM OpenAI-compatible base image
# FROM vllm/vllm-openai:v0.10.0

# RUN uv pip install --system git+https://github.com/huggingface/transformers.git

# # Set environment variable for your Hugging Face model name
# ENV MODEL_NAME=unsloth/Qwen3-8B-128K-GGUF
# ENV HF_HUB_ENABLE_HF_TRANSFER=1  

# # Expose the API port
# EXPOSE 8080

# # Entry point: Launch OpenAI-compatible API server
# ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
# CMD ["--model", "unsloth/Qwen3-8B-128K-GGUF", "--port", "8080"]


# FROM vllm/vllm-openai:latest

# ENV HF_HUB_ENABLE_HF_TRANSFER=1

# RUN uv pip install "huggingface_hub[cli]"
# RUN huggingface-cli download deepseek-ai/deepseek-coder-1.3b-instruct

# EXPOSE 8080

# RUN uv pip install -U vllm==0.10.1+gptoss \
#     --system \
#     --extra-index-url https://wheels.vllm.ai/gpt-oss/ \
#     --extra-index-url https://download.pytorch.org/whl/nightly/cu128 \
#     --index-strategy unsafe-best-match \
#     --prerelease=allow

# ENTRYPOINT ["uv", "run", "python3", "-m", "vllm.entrypoints.openai.api_server", \
#            "--model", "unsloth/Qwen3-8B-unsloth-bnb-4bit", \
#            "--port", "8080"]


# FROM vllm/vllm-openai:v0.10.0

# RUN apt-get update && apt-get install -y git-lfs

# WORKDIR /models

# RUN git clone https://huggingface.co/unsloth/Qwen3-8B-unsloth-bnb-4bit && \
#     cd Qwen3-8B-unsloth-bnb-4bit && \
#     git lfs pull && \
#     rm -rf .git

# ENTRYPOINT ["python", "-m", "vllm.entrypoints.openai.api_server", \
#            "--model", "unsloth/Qwen3-8B-unsloth-bnb-4bit", \
#            "--cpu-offload-gb", "8", \
#            "--enforce-eager", \
#            "--port", "8080"]

FROM vllm/vllm-openai:latest

RUN apt-get update && apt-get install -y git-lfs

WORKDIR /models

# Expose the API port
EXPOSE 8080

RUN git clone https://huggingface.co/Qwen/Qwen3-14B-AWQ && \
    cd Qwen3-14B-AWQ && \
    git lfs pull && \
    rm -rf .git

# Entry point: Launch OpenAI-compatible API server
ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
CMD ["--model", "Qwen3-14B-AWQ", "--port", "8080", "--cpu-offload-gb", "8", "--enforce-eager", "--reasoning-parser", "qwen3", "--enable-auto-tool-choice", "--tool-call-parser", "hermes"]