# Proof Packet

A proof packet is a local export that explains what ProofFlow saw, did, and
decided.

## Minimum contents

- Case summary: title, workflow type, timestamps, and status.
- Inputs: files, diffs, prompts, commands, or notes that started the work.
- Artifacts: local objects inspected during the case.
- Evidence: hashes, excerpts, command output, screenshots, or human notes.
- Actions: proposed and completed workflow steps.
- Decisions: accepted, rejected, deferred, or changed actions.
- Reproduction: commands or steps needed to verify the result.
- Limits: missing evidence, assumptions, skipped checks, and known risks.

## Evidence standard

AI or heuristic output can appear in a proof packet, but it is not proof by
itself. It must be linked to evidence or clearly marked as an assumption.

## v0.1 export direction

The v0.1 export is local Markdown. It should favor clarity and reproducibility
over presentation.
