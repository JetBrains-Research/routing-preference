<BASIS>
Score 5 — Complete and precise understanding
The Agent correctly identifies the full intent of the issue with no gaps. All key requirements, constraints, and context from the issue are reflected in what the solution sets out to do — regardless of whether the implementation is technically correct.

Score 4 — Mostly correct, one minor aspect missed or slightly misread
The Agent correctly identifies the core intent and addresses the primary requirement but may overlook one secondary constraint. The misreading is visible but inconsequential — the solution would still be accepted in a code review without mandatory changes on this basis.

Score 3 — Core intent identified, but one meaningful aspect is wrong
The Agent understands what the issue is broadly about but misreads something that matters. For bug reports: correctly identifies the bug but diagnoses the wrong cause. For feature requests: understands the general capability but misinterprets a stated constraint or misidentifies the expected input/output behavior. The solution would require a reviewer to send it back — not because of bugs, but because it does not fully address what was asked.

Score 2 — Partial understanding, responds to surface signals only
The Agent picks up on keywords or surface-level patterns in the issue text without correctly grasping the underlying intent. The solution uses the right terminology, file locations, or component names, but addresses a different problem than the one described or makes assumptions that directly contradict information in the issue. A correct reading of the issue would have led to a substantially different solution.

Score 1 — No meaningful understanding
The Agent misidentifies the problem entirely, ignores critical information in the issue, or produces a response not derivable from a genuine reading of the issue text. This includes not addressing the given bug or not implementing the requested feature.
</BASIS>