<BASIS>
Rank solutions from most to least contained within the issue's scope.

Higher rank — solution stays closer to what the issue asked:
- Only touches what is directly necessary to address the issue
- No unrelated changes
- At most one minor incidental change (e.g., a small formatting fix or rename that is not part of the issue)

Lower rank — solution includes changes beyond the issue:
- Unrelated refactoring, reformatting, or extra functionality beyond what was requested
- Changes clearly outside the issue's scope, even if the core of the solution is within it
- Substantial unrelated changes that dominate the intended issue
- Primarily or entirely changes unrelated to the issue

Tiebreakers when two solutions appear equally contained:
1. Prefer the solution that modifies fewer unrelated lines or files
2. Prefer the solution with smaller blast radius outside the issue's scope

Note: you are ranking how WELL-CONTAINED each solution is, not whether it is correct or high-quality. A minimal but buggy solution still ranks higher on scope than a sprawling one that also refactors unrelated code.
</BASIS>
