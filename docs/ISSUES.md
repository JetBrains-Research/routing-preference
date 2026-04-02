# Issue Collection

We need ~500 GitHub issues to generate solutions for. About 100 of these will end up in the final user survey.

## What we're looking for

Python issues only, from the last 2 years. Mix of JetBrains repos (like `teamcity-messages`) and popular open-source projects (flask, pytest, rich, fastapi, etc.). We want both bugs and feature requests.

Repos should be reasonably active (commits in last 3 months, responsive maintainers) and have enough open issues to pick from.

## How collection works

Run the collector:
```bash
uv run collect-issues collect --repos pallets/flask pytest-dev/pytest
```

This pulls issues from GitHub, then filters out the junk:
- Bot-created issues (dependabot, renovate)
- Issues with empty or tiny descriptions
- Vague titles like just "Bug" or "Help"
- Duplicates
- Non-English issues
- Stuff that looks AI-generated

Each issue gets classified as bug/feature and simple/medium/complex based on labels and some heuristics.

## Reviewers

Every issue needs someone to review the AI-generated solutions. We try to assign repo maintainers first, but fall back to the issue author if needed. The `reviewer_type` field tracks which one we used.

```bash
uv run collect-issues reviewers import --repos pallets/flask
uv run collect-issues assign
```

## Output format

Issues are stored as JSON in `data/issues/`. Each one has the usual GitHub fields (title, body, labels, author) plus our additions (issue_type, complexity, base_commit, assigned_reviewer, reviewer_type).

The `base_commit` is the repo state when the issue was created - needed so mini-swe-agent works on the right version of the code.

## Decisions

- **Python only** - more benchmarks exist, tooling is easier
- **Last 2 years** - avoids stale issues, maintainers still around
- **Maintainers as reviewers** - they know the codebase; author is fallback

## References

Our approach draws from existing benchmarks:

**Main ones:**
- [SWE-bench](https://arxiv.org/abs/2310.06770) (ICLR 2024) - 2,294 issues from 12 Python repos
- [BugsInPy](https://dl.acm.org/doi/abs/10.1145/3368089.3417943) (FSE 2020) - 493 bugs from 17 Python projects
- [Defects4J](https://program-repair.org/benchmarks.html) (2014) - the original Java bug benchmark

**Recent work:**
- [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) - 500 human-validated issues
- [SWE-bench+](https://arxiv.org/abs/2410.06992) - fixes data quality issues
- [SWE-MERA](https://aclanthology.org/2025.emnlp-demos.30.pdf) (EMNLP 2025) - dynamic benchmark to avoid data leakage

One thing recent papers flag: LLMs might memorize older benchmarks like Defects4J ([paper](https://arxiv.org/abs/2411.13323)). Using fresh issues from the last 2 years helps with this.
