<BASIS>
Rank solutions from best to worst understanding of the issue's intent.

Higher rank — solution demonstrates stronger understanding:
- Captures the full intent: core requirement, stated constraints, and relevant context from the issue
- Reads the issue accurately: correctly diagnoses the cause of a bug, or correctly interprets the requested feature's expected behavior
- Addresses every aspect explicitly asked for, not just the headline problem
- Reflects an understanding that would not require a reviewer to send it back for missing anything

Lower rank — solution demonstrates weaker understanding:
- Misses secondary constraints or stated context even while addressing the core
- Responds to surface signals (keywords, file names, terminology) rather than underlying intent
- Misdiagnoses the cause of a bug, or misinterprets a stated constraint or the expected input/output behavior
- Addresses a different problem than the one described, or ignores critical information in the issue

Tiebreakers when two solutions appear equally correct in understanding:
1. Prefer the solution that reflects more of the issue's stated constraints
2. Prefer the solution whose approach accounts for more of the relevant context

Note: you are ranking how well each solution UNDERSTOOD the issue, not whether the implementation is technically correct. Do not penalize for bugs here.
</BASIS>
