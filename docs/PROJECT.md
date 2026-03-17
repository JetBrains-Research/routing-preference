# Project Overview

## Research Goal

Determine user priorities for AI-generated code solution characteristics and their price sensitivity. The core question: **What characteristics do users value most in AI code solutions, and how much more are they willing to pay for them?**

### Model Routing Context

The broader goal is **Model Routing** - not shifting all usage to cheaper models, but intelligently routing easier tasks to smaller/cheaper models while keeping complex tasks on expensive models. This reduces overall costs without forcing users to always use one tier.

## Methodology

### Solution Generation

- Use **mini-swe-agent** to generate solutions for GitHub issues (see [FRAMEWORK.md](FRAMEWORK.md) for detailed comparison)
- Generate solutions using **7 different models** per issue (3 tiers)
- Each model produces a solution with naturally varying characteristics

**Model Tiers**:
| Tier | Description | Models |
|------|-------------|--------|
| 1 | Small, self-hosted | Qwen-8b |
| 2 | Medium, cloud-hosted (low cost) | Qwen-32b, Qwen-235b, GLM-4.7 |
| 3 | Large SOTA | GPT-5.2, Claude 4.6 Opus*, Kimi-k2 |

### Provider Considerations

- Goal: Use same provider across all models to avoid cost/speed variance
- Challenge: No single provider has all SOTA models
- **OpenRouter caution**: Suspiciously cheaper costs - may use quantization affecting accuracy

### LLM as a Judge

Score each solution on **7 characteristics** using dedicated judges (one judge per characteristic).

Purpose:
- Ensure fair comparisons by selecting solution pairs with **similar overall quality but different characteristic sub-scores**
- The measured scores are **not shown to users** - users must reason and rate characteristics themselves

**Validation**: Sub-sample of LLM judgments manually reviewed by humans to gauge alignment before full automation.

### User Comparison

1. Present user with **two solutions** (similar overall quality, different characteristic profiles)
2. User **rates the characteristics** of both solutions
3. User **chooses their preferred solution**
4. User indicates **willingness to pay more** for their choice ($5, $10, etc.)

### Cost Handling

- Real solution costs are **hidden** during comparison to avoid bias
- Price sensitivity is measured through willingness-to-pay after choice is made
- If chosen solution is actually cheaper, it doesn't matter - focus is on characteristic priority

**Willingness-to-Pay Approach**: Present discrete price options ($5, $10, $15...) for users to indicate how much more they'd pay for their preferred solution. This produces more normalized, unbiased results than open-ended pricing.

**Scale Consideration**: Raw per-task costs (e.g., $1 vs $5) may not feel significant to users. Presenting monthly/yearly projected costs may better convey the price difference impact.

## Why Multiple Models?

Using different models creates natural variation in characteristics without needing to prove we can "corrupt" a model. If models prove too similar, the approach may shift to intentional model corruption.

## Design Decisions

**Framework Choice (mini-swe-agent)**: Chosen for its minimal tooling (bash only), which ensures smaller/cheaper models can participate without failing on sophisticated tools. Richer frameworks (Cline, OpenCode) would bias results toward expensive models that can handle complex tool syntax.

**Overall Score Calculation**: Simple averaging of characteristic scores is acceptable for pair selection. Rationale: By comparing solutions with similar averages but different characteristic distributions (e.g., {2,7,5} vs {7,2,5}), the user study will naturally reveal which characteristics matter more - solutions with higher scores in important characteristics will be consistently preferred, revealing true priorities without pre-assumed weights.

## Open Questions

1. **Judging approach**: Judge all 7 solutions together (better ranking, but complex/biased) vs. judge each solution independently?

2. **Cost scale presentation**: How to present costs - per-task, monthly, or yearly? (To be discussed with Marco)

## Future Considerations

**Subtask Routing**: For complex tasks, extract subtasks and route easier ones to cheaper models while the main model handles the full task. Challenges:
- How to create subtasks
- How to assign subtasks to appropriate model tiers
- How to verify cheaper model completed subtasks correctly
