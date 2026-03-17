# GitHub Issue Collection

## Overview

Issues are collected from GitHub repositories and categorized to ensure consistent, fair evaluation across models.

## Categorization Criteria

### Repository Size

- Target: **Medium-sized repositories**
- Rationale: Large repos are harder to generate well-contextualized solutions for
- Definition of "medium" to be specified

### Programming Language

- Target: **Single language** (Python or Java - TBD)
- Rationale: Consistency across comparisons

### Issue Source

- **Human-reported** vs **AI-reported** issues
- Expectation: AI-reported issues may be less complex and easier to solve
- Should be tracked as a potential confounding variable

### Repository Age

- Older repositories tend to be more complex
- May affect difficulty of feature additions

### Issue Type

- **Bug fixes** vs **Feature additions**
- Critical distinction - affects solution complexity and evaluation
- Labels from maintainers are useful but not universally reliable

## Filtering Approach

- Cannot rely solely on issue labels (inconsistent naming conventions, missing labels)
- Need **deterministic filtering** mechanism
- Scan for "no AI contributions" policy to save time

## Collection Pipeline

1. **Collection**: Gather issues from GitHub
2. **Filtering**: Apply categorization criteria
3. **Assignment**: Each issue should have an assigned reviewer who receives the two PRs for decision

## Open Decisions

1. **Language choice**: Python vs Java
2. **Size thresholds**: What defines "medium" repository
3. **Filtering implementation**: How to deterministically categorize beyond labels
