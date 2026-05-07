<BASIS>
Rank solutions from most to least logically correct under the agent's own understanding of the issue.

Higher rank — solution is more logically sound:
- Produces correct output under the agent's understanding of the issue, with no bugs in the main case
- Handles edge cases correctly; failure conditions are accounted for
- Logic resolves cleanly — no syntax errors, infinite loops, or unreachable correct outcomes

Lower rank — solution has logical problems:
- Bugs or unclear errors in edge cases while the main case still works
- Contains a logical flaw that causes incorrect behavior in some conditions
- Significant logical flaw producing wrong output even under the agent's own understanding
- Non-functional: syntax errors, infinite loops, or logic that cannot resolve correctly

Tiebreakers when two solutions appear equally correct:
1. Prefer the solution handling more edge cases
2. Prefer the solution with fewer latent bugs or failure modes

Note: you are ranking correctness under the agent's OWN understanding of the issue. If the agent misread the issue, that belongs under intent, not here. Here, ask only: does the code do what the agent intended?
</BASIS>
