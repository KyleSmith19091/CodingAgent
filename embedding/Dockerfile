FROM ghcr.io/huggingface/text-embeddings-inference:1.7.4

WORKDIR /data

ENTRYPOINT [ "text-embeddings-router", "--model-id", "Qwen/Qwen3-Embedding-0.6B", "--port", "8080", "--revision", "refs/pr/27" ]
