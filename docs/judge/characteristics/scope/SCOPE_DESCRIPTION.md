<NAME>
Scope Adherence
</NAME>

<SHORT_DESCRIPTION>
Whether the solution stays within the boundaries of what the issue requested.
</SHORT_DESCRIPTION>

<LONG_DESCRIPTION>
Scope adherence evaluates how much the solution extends beyond what the issue asked for. It is strictly about excess, and not about what was missed or whether the solution works.

This means:
- A solution that only fixes half the issue but touches nothing extra scores 5/5
- A solution that perfectly fixes the issue but also refactors unrelated code scores lower
- Whether the extra changes are correct or not is irrelevant to this score

Note: What the solution missed is evaluated by Intent Understanding which is independent from this characteristic. Whether the solution works is evaluated by Functional Correctness which is again unrelated and independent.
</LONG_DESCRIPTION>

<BASIS>
Score 5 — Fully contained
The solution only touches what is directly necessary to address the issue. No unrelated changes exist.

Score 4 — Minimal excess
The solution stays within scope for the most part but includes one minor unrelated or unnecessary change, for examples a small formatting fix or an incidental rename that is not part of what should have been fixed.

Score 3 — Noticeable excess
The solution includes changes that are clearly beyond the issue, for example refactoring unrelated logic or adding unrequested functionality, but the core of the solution remains within the issue's scope.

Score 2 — Significant excess
The solution makes substantial changes beyond the issue. The unrelated changes are significant enough that they dominate the intended issue.

Score 1 — Entirely out of scope
The solution consists primarily or entirely of changes unrelated to the issue.
</BASIS>