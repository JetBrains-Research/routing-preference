# Task Types

The pipeline solves two kinds of tasks. Both flow through the same commands,
storage layout, judging, and selection; they differ only in how the workspace
is prepared and which agent prompt template is used.

| Task type | Input | Workspace | Solution diff |
|-----------|-------|-----------|---------------|
| `github_issue` | GitHub issue with `repo` and `base_commit` | Repo cloned and checked out at `base_commit` | Changes to existing code |
| `zero_shot` | Natural-language prompt, no code input | Empty directory with a fresh git repo | Newly created project files |

The task type is stored on each task and derived automatically: rows with a
`repo` are GitHub issues, rows without one are zero-shot prompts. It can also
be set explicitly with a `task_type` field.

## Zero-Shot Prompts

Zero-shot prompts are requests to start a project or build a minimal tool from
scratch (e.g., a CLI utility, an API script, a data-processing script). The
prompt text can be informal or structured; the pipeline treats both as plain
text.

Prompts are stored as JSON files under `data/prompts/`:

```json
[
  {
    "id": "prompt__unit-converter-001",
    "title": "Unit Converter CLI",
    "body": "Build a command-line tool that converts between units..."
  }
]
```

Only `id`, `title`, and `body` are required. `title` is a short task name;
`body` holds the full prompt text.

Tasks whose prompt references provided data files declare an `assets_dir`,
resolved relative to the dataset file. The directory is copied into the
workspace and committed before the agent starts, so the agent can read the
files but they never appear in the solution diff:

```json
{
  "id": "prompt__book-journey-002",
  "title": "Book Journey",
  "body": "... Books are loaded from assets/books.json ...",
  "assets_dir": "prompts_vibench/002-book-journey/assets"
}
```

## Usage

Generation, judging, and selection use the same commands as issue tasks:

```bash
uv run routing generate --dataset data/prompts/zero_shot_20.json --model <provider/model>
uv run routing judge --exposure V1
uv run routing select
```

## Behavior Differences

- **Generation**: instead of cloning a repository, the generator creates an
  empty directory with an initialized git repo. The agent prompt uses the
  `zero_shot` template registered in `docs/agent/prompts.json`, which tells
  the model it is starting from an empty project.
- **Solution capture**: `patch.diff` includes newly created files (captured
  via git intent-to-add before diffing).
- **Judging**: V1 (issue + diff) works unchanged. V2 exposures provide no
  source files, because zero-shot tasks have no pre-existing code; V1 is the
  natural exposure for them.
- **Objective metrics, storage, selection**: identical to issue tasks.
