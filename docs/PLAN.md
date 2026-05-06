# Implementation Plan

## Current State

The solution generation pipeline and LLM as a Judge system are implemented.

## Phase 0: Pipeline Validation

Test the end-to-end flow with minimal data before scaling up.

- [x] Generate solutions with 2-3 models
- [x] Implement LLM as a Judge (4 subjective characteristics)
- [x] Verify the flow works: issue → solution → score
- [x] Add comparative ranking mode for multi-solution comparison

## Phase 1: Issue Dataset Creation

Create or source a HuggingFace dataset of GitHub issues.

- [ ] Define issue schema (repo, number, title, body, labels, metadata)
- [ ] Collect issues from JetBrains repositories (or other target repos)
- [ ] Apply filtering criteria (see [ISSUES.md](ISSUES.md))
- [ ] Upload dataset to HuggingFace

Currently using test issues from SWE-bench (sympy, requests) for validation.

## Phase 2: Solution Generation

Generate solutions for all issues using all 7 models.

- [x] Configure model access (LiteLLM / direct APIs)
- [ ] Run pipeline for each model tier
- [ ] Store solutions with full trajectories
- [ ] Track costs and timing per solution

Initial solutions generated with gpt-4o-mini and gpt-4o for testing.

## Phase 3: Characteristics

Implement subjective judging and objective metric extraction for solutions.

- [x] Define the 4 subjective and 2 objective characteristics to measure
- [x] Create judge prompts for subjective characteristics
- [x] Implement scoring pipeline
- [x] Implement comparative ranking pipeline
- [x] Implement objective metric extraction
- [ ] Validate: Manual review of sub-sample to gauge alignment
- [ ] Score all solutions

See [JUDGE.md](JUDGE.md) for architecture details.

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
