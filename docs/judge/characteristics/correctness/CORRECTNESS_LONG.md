<LONG_DESCRIPTION>
Functional correctness evaluates the logical soundness of the solution. Not what problem it addresses or how much of the issue it covers.

This means:
- A patch that perfectly implements the wrong thing can still score 5/5 here
- A patch that addresses the right problem but is logically broken scores 1/5
- All code in the patch is evaluated, including code outside the issue scope

Note: What the solution targets is evaluated by Intent Understanding. What the solution changes beyond the issue scope is evaluated by Scope Adherence. Any concerns about coverage or scope are beyond this characteristic.
</LONG_DESCRIPTION>