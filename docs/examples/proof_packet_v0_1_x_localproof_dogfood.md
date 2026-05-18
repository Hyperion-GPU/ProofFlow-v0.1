# ProofFlow v0.1.x LocalProof Dogfood Proof Packet (Public Example)

- Latest_Main commit SHA: 50524582ecf2433e11fa4a8f82bb51a66319aedd
- Generated At: 2026-05-19T00:05:55+08:00
- Generator Command: MCP client Codex -> proofflow_scan(folder_path="<TMP>\localproof-source") -> proofflow_suggest(target_root="<TMP>\localproof-organized") -> proofflow_approve_execute -> proofflow_decide -> proofflow_export_packet(case_id="8fadcdce-245d-4b90-8531-f28916575a6e")
- Statement: Generated for milestone v0.1.x dogfood; not a release artifact.
# Proof Packet: File cleanup scan: localproof-source

Generated: `2026-05-18T16:04:25.747134Z`

## Case Summary

- Case ID: `8fadcdce-245d-4b90-8531-f28916575a6e`
- Title: File cleanup scan: localproof-source
- Workflow type: `file_cleanup`
- Status: `open`
- Created: `2026-05-18T16:02:48.179271Z`
- Updated: `2026-05-18T16:02:48.179271Z`
- Summary: LocalProof scan for <TMP>\localproof-source

## Artifacts

- `7ebc31e0-87d1-4d77-813c-6c005f313e54` notes.txt
  - Kind: `text`; Role: `supporting`
  - Path: `<TMP>\localproof-source\notes.txt`
  - SHA-256: `9cfee804d940c636814ef41762bfaf7373f38e75eba7d19861fc1878aa5bb297`
- `d3b486b7-9c5e-44f9-86b9-88d8548e743c` project-plan.md
  - Kind: `text`; Role: `supporting`
  - Path: `<TMP>\localproof-source\project-plan.md`
  - SHA-256: `e420d0606f10e8b74ef221b150870062bf8605fc12affb4775165d813c09ca17`

## Claims & Evidence

No claims recorded.

## Actions

- Create Notes directory
  - Action ID: `b2ec239b-c384-4813-9951-2847662f6d65`
  - Kind: `mkdir_dir`
  - Status: `executed`
  - Reason: Deterministic LocalProof prerequisite: destination directory
  - Preview: `{"dir_path":"<TMP>\\localproof-organized\\Notes"}`
  - Result: `{"already_exists":false,"created":true,"dir_path":"<TMP>\\localproof-organized\\Notes","executed_at":"2026-05-18T16:03:24.634923Z","operation":"mkdir_dir"}`
  - Undo: `{"created_at":"2026-05-18T16:03:24.634923Z","created_by_action":true,"dir_path":"<TMP>\\localproof-organized\\Notes","operation":"remove_dir"}`
- Move notes.txt to Notes
  - Action ID: `a07995b6-de1c-4b52-9368-888b5ecde2e6`
  - Kind: `move_file`
  - Status: `executed`
  - Reason: Deterministic LocalProof rule: note
  - Preview: `{"from_path":"<TMP>\\localproof-source\\notes.txt","to_path":"<TMP>\\localproof-organized\\Notes\\notes.txt"}`
  - Result: `{"executed_at":"2026-05-18T16:04:15.454153Z","from_path":"<TMP>\\localproof-source\\notes.txt","operation":"move_file","sha256":"9cfee804d940c636814ef41762bfaf7373f38e75eba7d19861fc1878aa5bb297","size_bytes":41,"to_path":"<TMP>\\localproof-organized\\Notes\\notes.txt"}`
  - Undo: `{"created_at":"2026-05-18T16:04:15.454153Z","from_path":"<TMP>\\localproof-organized\\Notes\\notes.txt","from_sha256":"9cfee804d940c636814ef41762bfaf7373f38e75eba7d19861fc1878aa5bb297","from_size_bytes":41,"operation":"restore_file","to_path":"<TMP>\\localproof-source\\notes.txt"}`
- Move project-plan.md to Notes
  - Action ID: `de03c7e7-bac4-44f2-ba28-185b7e125f62`
  - Kind: `move_file`
  - Status: `pending`
  - Reason: Deterministic LocalProof rule: note
  - Preview: `{"from_path":"<TMP>\\localproof-source\\project-plan.md","to_path":"<TMP>\\localproof-organized\\Notes\\project-plan.md"}`
  - Result: `not recorded`
  - Undo: `not recorded`

## Decisions

- Decision on action a07995b6-de1c-4b52-9368-888b5ecde2e6
  - Decision ID: `e0d9092c-58b9-420f-98dc-f8bdcd63e2dd`
  - Status: `accepted`
  - Rationale: Dogfood MCP_Channel validation: owner reviewed the previewed temp source and target paths under <TMP> and approved execution for a public-safe LocalProof sample.
  - Result: accepted

## Runs & Test Results

No runs recorded.

## Remaining Risks

No non-info open risks recorded.


