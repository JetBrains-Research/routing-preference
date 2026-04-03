<STEPS>
1. Read the issue description carefully and identify:
   - Whether it is a bug report or a feature request
   - For bug reports: the described defect and its root cause if it has been stated
   - For feature requests: the desired behavior and any stated constraints

2. Summarize what the issue is asking the Agent to do.

3. Read the patch.diff and identify what problem the Agent appears to be solving,
   based on what was changed, not whether those changes are correct.

4. Compare your summary from Step 2 to your observation from Step 3:
   - Are they aligned?
   - If not, what specifically was missed or misread?
   - Is the gap minor (secondary detail) or meaningful (core requirement)?

5. Assign a score using the BASIS descriptions. If the issue is ambiguous and
   the Agent picked a reasonable interpretation, do not penalize, score based
   on the interpretation chosen, not the one you would have preferred.

6. Output your score and reasoning.
</STEPS>