# Coding Agent

```text
                           ___           ___           ___ 
                          /\__\         /\  \         /\__\
                         /::|  |       /::\  \       /:/  /
                        /:|:|  |      /:/\:\  \     /:/  / 
                       /:/|:|__|__   /::\~\:\  \   /:/  /  
                      /:/ |::::\__\ /:/\:\ \:\__\ /:/__/   
                      \/__/~~/:/  / \:\~\:\ \/__/ \:\  \   
                            /:/  /   \:\ \:\__\    \:\  \  
                           /:/  /     \:\ \/__/     \:\  \ 
                          /:/  /       \:\__\        \:\__\
                          \/__/         \/__/         \/__/
```

Coding agent to assist or automate coding tasks.

## How to run

### Requirements

- The `uv` tool (follow instructions [here](https://docs.astral.sh/uv/getting-started/installation/))

- Access to a machine with a GPU (model packaged as Dockerfile).

- `cargo` in the future

### Steps
1. Install dependencies `uv sync`
2. Build and deploy image from dockerfile in `model` directory.
3. Run with `uv run main.py`