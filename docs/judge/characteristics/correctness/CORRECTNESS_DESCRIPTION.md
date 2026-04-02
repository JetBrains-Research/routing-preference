<NAME>
Functional Correctness
</NAME>

<SHORT_DESCRIPTION>
Whether the solution works correctly, regardless of what it targets.
</SHORT_DESCRIPTION>

<LONG_DESCRIPTION>
Functional correctness evaluates the logical soundness of the solution. Not what problem it addresses or how much of the issue it covers.

This means:
- A patch that perfectly implements the wrong thing can still score 5/5 here
- A patch that addresses the right problem but is logically broken scores 1/5
- All code in the patch is evaluated, including code outside the issue scope

Note: What the solution targets is evaluated by Intent Understanding. What the solution changes beyond the issue scope is evaluated by Scope Adherence. Any concerns about coverage or scope are beyond this characteristic.
</LONG_DESCRIPTION>

<BASIS>
Score 5 — Fully correct
The solution is logically sound and produces the correct output under the agent's own understanding of the issue. No bugs or failure conditions exist in the logic.

Score 4 — Correct in the main case, minor gap
The solution works correctly for the most part but might have bugs or unclear errors in some edge cases. The core fix or feature functions per agent's understanding of the issue.

Score 3 — Partially correct, works in some cases
The solution works under some conditions but contains a logical flaw that would cause incorrect behavior in others.

Score 2 — Largely incorrect
The solution contains a significant logical flaw and would not produce correct output even under the assumption and understanding that the agent has had from the issue.

Score 1 — Non-functional
The solution is broken and would not produce correct output under any conditions. This includes syntax errors, infinite loops, or logic that can never resolve correctly.
</BASIS>