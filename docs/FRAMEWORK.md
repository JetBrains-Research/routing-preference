# Framework Choice: mini-swe-agent

## Summary

We chose **mini-swe-agent** for solution generation due to its minimal tooling (bash only), which ensures fair comparison across models of varying capabilities.

## Background

The execution flow is:
```
issue → agent → environment → agent → ... → environment → agent → solution
```

- **User perspective**: issue → agent → solution (single interaction)
- **Agent perspective**: Multi-round communication with the environment (exploring files, running tests, etc.)

This approach:
- Focuses on characteristics of the **first generation** (no user feedback loops)
- Still allows agents to explore codebases and use available tools
- Differs from simply feeding code to an LLM (which has context window limitations)

**Why not OpenCode?** While OpenCode has more capabilities (LSP, MCP, web tools), it's designed for interactive user-agent development. mini-swe-agent is more typical for benchmarks without user interaction and ensures smaller models can participate.

## Tool Comparison

### mini-swe-agent (bash only)

| Tool | Description |
|------|-------------|
| `bash` | Only provides bash. Each command runs independently in a separate terminal. |

### SWE-Agent (bash + file navigation + editing + search)

| Tool | Description |
|------|-------------|
| `bash` | Run shell commands |
| `open` | Opens a file in windowed viewer (~100 lines at a time) |
| `scroll_up/down` | Moves view window up/down 100 lines |
| `goto` | Jumps to a specific line |
| `search_file` | Searches for term within currently open file |
| `search_dir` | Searches for term across all files in a directory |
| `find_file` | Finds files by name |
| `edit` | Custom editor command for multi-line edits |

### Cline (bash + file ops + web + MCP + dialogue)

| Tool | Description |
|------|-------------|
| `execute_command` | Run CLI commands with optional user approval |
| `write_to_file` | Create or overwrite files entirely |
| `read_file` | Read file contents |
| `replace_in_file` | Targeted edits to specific parts of a file |
| `search_files` | Regex search across files |
| `list_files` | List directory contents |
| `list_code_definition_names` | List code definitions (functions, classes) |
| `browser_action` | Interact with websites via Puppeteer |
| `use_mcp_tool` | Call tools from connected MCP servers |
| `access_mcp_resource` | Read resources from MCP servers |
| `ask_followup_question` | Ask user for clarification mid-task |
| `attempt_completion` | Signal task completion |
| `new_task` | Spin up fresh task with clean context |

### OpenCode (bash + file ops + web + MCP + LSP + task tracking)

| Tool | Description |
|------|-------------|
| `bash` | Run terminal commands |
| `edit` | Precise edits by replacing exact text matches |
| `write` | Create new files (overwrites existing) |
| `read` | Read files, supports line ranges |
| `grep` | Fast content search across codebase |
| `glob` | Search files using glob patterns |
| `list` | List directory contents |
| `lsp` | Code intelligence via LSP servers |
| `patch` | Apply patch/diff files |
| `skill` | Load SKILL.md into conversation |
| `todowrite/read` | Track progress across multi-step tasks |
| `webfetch` | Fetch and read URL content |
| `websearch` | Search web using Exa AI |
| `question` | Pause and ask user questions |

## Analysis

**Common Ground**: All frameworks provide bash - it's essential for development and appears heavily in coding training data.

**Divergence**: Beyond bash, frameworks differ significantly:
- SWE-Agent adds file navigation tools (all have bash equivalents like `cat`, `find`)
- Cline/OpenCode add MCP, web browsing, and sophisticated dialogue control

## Why mini-swe-agent?

Our research requires models that can be hosted locally or on rented servers with near-zero inference cost. These smaller models face challenges with sophisticated tooling:

1. **Syntax failures**: May attempt to use complex tools but fail on correct syntax
2. **Context overflow**: MCP or web search outputs could fill their context window
3. **Tool avoidance**: Smaller models may avoid complex tools entirely, while expensive models leverage them - biasing results toward our framework choice

## Trade-offs

**Pros**:
- Any model can participate regardless of tool-use capability
- Fair comparison across model tiers
- Simple, predictable behavior

**Cons**:
- Pure bash may prove too limiting for certain tasks
- May not reflect real-world agentic coding workflows
- Results should be interpreted with this constraint in mind
