# AgentGuard Code Review Workflow

AgentGuard is the ProofFlow branch for evidence-backed code review.

## Goal

Help a human review code with AI assistance while keeping every claim tied to
evidence.

## Minimum workflow

1. Create a review case.
2. Register artifacts such as files, diffs, command output, or test results.
3. Record findings as evidence-backed claims.
4. Propose actions such as fix, test, defer, or reject.
5. Record the human decision and final rationale.

## Review finding rule

A finding is valid only when it includes:

- claim,
- affected file or symbol,
- supporting evidence,
- impact,
- recommended action.

If the evidence is missing, the claim must be labeled as an assumption and should
not be treated as a final review result.

## Destructive actions

Any action that deletes, overwrites, moves, or rewrites user files must be
handled as:

```text
dry-run -> user approval -> execution -> undo path
```

This applies to cleanup scripts, formatters that rewrite many files, generated
patches, and database reset commands.

