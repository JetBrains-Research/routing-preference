# Execution Isolation

By default, mini-swe-agent runs commands directly on your machine. For untrusted datasets, use Docker to sandbox execution.

## Usage

```bash
# Local (default)
uv run generate --dataset data/issues/test.json --model openai/gpt-4o-mini

# Docker sandbox
uv run generate --dataset data/issues/test.json --model openai/gpt-4o-mini --sandbox docker
```

Docker mode mounts the cloned repo into a container at `/workspace`. The agent runs inside the container, but git diff runs on the host after the agent finishes.

## Custom Image

Default image is `python:3.11-slim`. To use the provided Dockerfile with git and build tools:

```bash
docker build -t routing-sandbox:latest docker/
export ROUTING_SANDBOX_IMAGE=routing-sandbox:latest
```

## Environment Variables

Docker mode forwards these to the container:
- `GITHUB_TOKEN` / `GH_TOKEN`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

## Security Notes

Docker isolates the filesystem and processes, but:
- Container escapes are possible (rare)
- Mounted paths are accessible
- No resource limits by default

For stronger isolation, add `--network=none` or resource limits to the Docker config in `src/generator.py`.
