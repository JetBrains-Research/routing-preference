# Implementation Plan

## Current State

The solution generation pipeline is implemented.

## Phase 0: Pipeline Validation

Test the end-to-end flow with minimal data before scaling up.

- [ ] Generate solutions with 2-3 models
- [ ] Implement basic LLM as a Judge (single characteristic)
- [ ] Verify the flow works: issue → solution → score

## Phase 1: Issue Dataset Creation

Create or source a HuggingFace dataset of GitHub issues.

- [ ] Define issue schema (repo, number, title, body, labels, metadata)
- [ ] Collect issues from JetBrains repositories (or other target repos)
- [ ] Apply filtering criteria (see [ISSUES.md](ISSUES.md))
- [ ] Upload dataset to HuggingFace

## Phase 2: Solution Generation

Generate solutions for all issues using all 7 models.

- [ ] Configure model access (LiteLLM / direct APIs)
- [ ] Run pipeline for each model tier
- [ ] Store solutions with full trajectories
- [ ] Track costs and timing per solution

## Phase 3: LLM as a Judge

Implement characteristic scoring for solutions.

- [ ] Define the 7 characteristics to measure
- [ ] Create judge prompts (one per characteristic)
- [ ] Implement scoring pipeline
- [ ] Validate: Manual review of sub-sample to gauge alignment
- [ ] Score all solutions

## Phase 4: Pair Selection

Select solution pairs for user comparison.

- [ ] Calculate average scores per solution
- [ ] Implement pair selection algorithm:
  - Similar overall average
  - Different characteristic distributions (e.g., {2,7,5} vs {7,2,5})
- [ ] Generate comparison set

## Phase 5: User Survey

Build comparison interface.

- [ ] Design survey flow:
  1. Present two solutions (code diffs)
  2. User rates characteristics of both
  3. User selects preferred solution
  4. User indicates willingness-to-pay
- [ ] Implement survey interface
- [ ] Determine cost scale presentation (per-task vs monthly/yearly)
- [ ] Deploy and collect responses

## Phase 6: Analysis

Analyze results to determine characteristic priorities.

- [ ] Correlate user preferences with characteristic scores
- [ ] Determine which characteristics drive preference
- [ ] Analyze willingness-to-pay by characteristic
- [ ] Derive routing recommendations
