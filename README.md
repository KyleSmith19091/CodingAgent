<div align="center">
<h1>Coding Agent</h1>
</div>

Coding agent to assist or automate software engineering tasks.

## How to run (running on google cloud run)
1. Build/Download the main.bin binary.
2. `gcloud config set project <project-id>`
3. `gcloud run services proxy <cloud-run-instance> --port=9090` 
4. Run binary.
