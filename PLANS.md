# ProofFlow MVP Plan

## Milestone 0: Repository skeleton

- [x] Create root docs and local run instructions.
- [x] Add FastAPI backend skeleton with health check.
- [x] Add Vite React TypeScript frontend skeleton.
- [x] Document the local-first workflow model.
- [x] Add automated tests after the first real service contract exists.

## Milestone 1: LocalProof

- [x] Define SQLite schema for cases, artifacts, evidence, actions, decisions.
- [x] Add local file registration without copying or deleting originals by
  default.
- [x] Store hashes, file metadata, and evidence notes.
- [x] Show case timeline and artifact list in the frontend.
- [x] Export a minimal proof packet.

## Milestone 2: AgentGuard

- [x] Add code review case type.
- [x] Record review claims as evidence-backed findings.
- [x] Track proposed actions and human decisions.
- [x] Link findings to files, commands, test output, or diffs.
- [x] Reject unsupported AI or heuristic claims in review summaries.

## Milestone 3: Proof packet

- [x] Generate a local packet containing inputs, evidence, actions, decisions,
  reproduction steps, and known limits.
- [x] Keep exports deterministic enough to compare across runs.
- [x] Add a verification checklist for packet completeness.

## Milestone: Harden v0.1

- [x] Harden AgentGuard untracked file ingestion with sensitive-file omission and
  a 256 KiB synthetic diff cap.
- [x] Preserve evidence-backed metadata and claims for omitted or capped
  untracked files without storing sensitive content.
- [x] Add previewable `mkdir_dir` actions so LocalProof suggested moves are
  executable when category directories are missing.
- [x] Keep `move_file` strict: it still requires an existing destination parent
  and does not create directories implicitly.
- [x] Make `scripts/demo_seed.py` compatible with Python 3.11 readonly reset
  handling.
- [x] Align CaseDetail run metadata display with backend `test_returncode`.
- [x] Refresh README and agent invariants for the current v0.1 trust baseline.

## Milestone: Dogfood v0.1

- [x] Align `make dev-backend` with the documented backend port `8787`.
- [x] Add full LocalProof action lifecycle controls in the page: approve,
  execute, undo, and reject.
- [x] Show LocalProof action preview, result, undo, metadata, and dependency
  context for dogfood review.
- [x] Add focused frontend smoke checks for Dashboard, AgentGuard, LocalProof,
  and CaseDetail.
- [x] Add a backend v0.1 action lifecycle and packet invariant acceptance test.
- [x] Add a local dogfood guide for demo seed, backend/frontend startup, smoke
  checks, LocalProof, AgentGuard, and Proof Packet export.

## Milestone: v0.1 RC Action Safety Gate

- [x] Add scoped filesystem action validation.
- [x] Add LocalProof `source_root` / `target_root` / `allowed_roots` metadata.
- [x] Add hash-guarded undo for `move_file` and `rename_file`.
- [x] Block ProofFlow DB/data/proof_packets paths from filesystem actions.
- [x] Add legacy action safety upgrade coverage.
- [x] Document action safety, reset, backup, and restore behavior.

## Milestone: v0.1 RC Release Gate

- [x] Add backend CI matrix.
- [x] Add frontend CI for tests and build.
- [x] Add RC checklist.
- [x] Add changelog.
- [x] Add dogfood Proof Packet example.

## Milestone: v0.1.0-rc1 Version Stamp & Publish Prep

- [x] Centralize backend release metadata.
- [x] Expose version, stage, and release name from `/health`.
- [x] Show the RC release stamp on the Dashboard.
- [x] Add release notes draft.
- [x] Add local release check helper.

## Milestone: v0.1.0-rc1 Dogfood Bug Bash

- [x] Log the post-release RC1 dogfood bug bash path.
- [x] Archive post-RC1 smoke helper changes in the Unreleased changelog.
- [x] Keep the `v0.1.0-rc1` tag fixed while documenting post-RC1 `main`
  changes separately.
- [x] Link the RC API smoke helper from dogfood and release checklist docs.

## Milestone: Managed Backup / Restore Foundation

- [x] Define the managed backup / restore design, invariants, manifest shape,
  API contract, and contract tests.
- [x] Foundation backup/restore Phase 2-4 complete.
- [ ] Live DB restore remains deferred/blocked until stricter pre-restore backup
  and confirmation gates exist.

## Future scope

- [ ] Add richer destructive action types only after a new preview/undo review.
- [ ] Explore vector RAG after v0.1 local trust boundaries are accepted.
- [ ] Explore ComfyUI execution after v0.1 local trust boundaries are accepted.
- [ ] Explore multi-user workflows after localhost v0.1 is stable.
- [ ] Explore cloud sync after local-first recovery paths are stable.
- [ ] Explore AI-assisted code edits only after evidence and action review gates
  are stricter than the current v0.1 baseline.

## Backlog from v0.1.x dogfood

### vscode-channel-screenshots-deferred-from-v0-1-x-dogfood

Source: Dogfood_Report v0.1.x dogfood-and-channel-polish, Channel Evidence → VSCode_Channel block, Outcome = Deferred.

> Scope expansion: 本 anchor 同时承载 task 4.2 VSCode_Channel screenshots 缺口与 task 7.2 Demo_Asset GIF 缺口（用户 Option E：合并为同一个 Backlog_Entry，避免 backlog 重复）。anchor slug 仍为 `vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`，task 4.4 已写入的 VSCode block 引用无须修改。

- Why deferred: Dogfood 执行环境暂无可抓取的 VS Code 可视窗口，无法在本里程碑内真实产出 inline audit 与 Approve Gate 截图；按 design §Error Handling 与 Requirement 2.5，`Outcome = Deferred` 必须挂 Backlog_Entry，禁止伪造或占位 evidence。Demo_Asset GIF（task 7.2）与 VSCode 截图同根因（无可视窗口可抓取），并入本 anchor 一同推迟。
- vscode-extension commit SHA at deferral: `a94d190ce03332c1c480e8d887be2ebf8df9daba`
- Required deliverables（在能拿到 VS Code 可视窗口的下个 dogfood 周期补齐）:
  - `docs/assets/proofflow-v0_1_x-vscode-inline-audit.png`
  - `docs/assets/proofflow-v0_1_x-vscode-approve-gate.png`
  - 可选：`docs/assets/proofflow-v0_1_x-vscode-flow.gif`
  - `docs/assets/proofflow-v0_1_x-dogfood-<channel>.gif`（Demo_Asset，`<channel>` ∈ {`mcp`, `vscode`, `gha`}，与三渠道证据块的 `Tool / Workflow / View` 字段保持一致；本里程碑 `docs/assets/` 下不落任何 GIF / placeholder 文件）
- Acceptance:
  - 打开 `vscode-extension/` 工程的扩展，连接到本地 backend（`http://127.0.0.1:8787`），触发一次 LocalProof Case 与一次 AgentGuard Case；
  - inline 标注命中正确 `source_location` 行号区间；
  - Approve Gate 解锁一个 `pending_decision` action 并立即 Undo（验证 hash-guarded undo 仍然工作）；
  - 脱敏：录制前关闭 Windows 通知；终端窗口标题不含真实绝对路径或用户名；侧边栏不暴露其它私有仓库或未提交文件名；`.mcp.json` / `.codex/config.toml` 中的 token 用占位符（如 `<MCP_TOKEN>`）替换；如不慎录入敏感内容须 reshoot 而非后期模糊（与 `docs/assets/README.md` 一致）。
- Acceptance — Demo_Asset GIF（task 7.2）:
  - 录制内容：一次真实 AI coding agent 操作被 ProofFlow 端到端审计的过程（可复用本 anchor 上方 VSCode_Channel 的 Approve Gate 流，或 task 4.1 的 MCP_Channel 真实 AI 客户端会话），与 Requirement 5.1 / 5.2 一致；
  - 体积 / 时长 / 分辨率：GIF ≤ 8 MB，时长 ≤ 60 秒，分辨率 ≤ 1280×720（与 design §Demo Asset Generation Design 与 `docs/assets/README.md` 一致）；
  - 隐私脱敏（与 VSCode 截图共用同一组规则）：关闭 Windows 通知；终端标题 / PowerShell prompt / VS Code 标题栏 / 侧边栏不出现 `C:\Users\<name>\…` 等含真实用户名的本地绝对路径，统一用 `<TMP>` 占位符；侧边栏不暴露其它私有仓库或未提交文件；`.mcp.json` / `.codex/config.toml` 中的 token 用占位符（如 `<MCP_TOKEN>`）替换；如不慎录入敏感内容必须 **reshoot 而非后期模糊**；
  - 引用回写：在 `README.md` 首屏 demo 区、`README.zh-CN.md` 快速开始段顶部、`docs/ledger_quickstart_mcp.md` 首屏中至少一份显式引用该 GIF（与 task 7.3 联动，Requirement 5.2）。本里程碑 task 7.3 在 README/quickstart 中以 placeholder note（指向本 anchor）形态体现，**不**插入 fake `![…](docs/assets/...)` 图片标签。
- Reference:
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/4_2_vscode_channel.md`
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/7_2_demo_asset_gif.md`

### agentguard-public-packet-deferred-from-v0-1-x-dogfood

Source: Dogfood_Report v0.1.x dogfood-and-channel-polish, Demo and Example Packet section + task 7.1.

- Why deferred: 本里程碑公开 packet 只交付 1 份 LocalProof（`docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`），未补 AgentGuard 路线；按 design §Public Proof Packet Example Design「至少 1 份 AgentGuard packet 优先；理想再加 1 份 LocalProof packet」，AgentGuard 一份留待下个 dogfood 周期补齐。
- Required deliverables（在能拿到 AgentGuard 真实运行环境的下个 dogfood 周期补齐）:
  - `docs/examples/proof_packet_v0_1_x_agentguard_dogfood.md`
- Acceptance:
  - 在隔离环境（`$env:PROOFFLOW_DB_PATH` / `$env:PROOFFLOW_DATA_DIR` 指向 tmp）下跑 `python .\scripts\generate_real_docs_output.py --case-type agentguard --output "<TMP>\packet.md"` 或等价命令；
  - packet 顶部必备元数据：Latest_Main commit SHA、ISO8601 生成时间、生成命令字符串（路径用 `<TMP>` 占位符）、声明「Generated for milestone v0.1.x dogfood; not a release artifact」；
  - 与 README v0.1.6 dogfood 故事衔接（AgentGuard PR review 路径）；
  - 全文 `<TMP>` 占位符脱敏，`Select-String '[A-Z]:\\Users\\' -CaseSensitive:$false` 在该 packet 上 0 命中；
  - 在 Dogfood_Report `Demo 资产与示例 Proof Packet` 章节登记 `public_packet_path`，并把本 anchor 标记为 closed + 附 PR / commit 链接。
- Reference:
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/7_1_public_packet.md`
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/9_1_findings.md`
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/9_3_backlog_audit.md`

### quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood

Source: Dogfood_Report v0.1.x dogfood-and-channel-polish, Findings and Triage section (F-1 ~ F-5) + task 6.1 (`transcripts/6_1_quickstart_validation.md`) + task 6.2 (`transcripts/6_2_quickstart_polish.md`).

- Why deferred: task 6.2 已按用户 Option B 决定在 working tree 直接修复 5 份 Quickstart_Doc_Set 共 20 处裸 `cd` / `&&` 串联 / 错误 entry / 缺 port / 不存在引用，且 task 6.3 通过 audit-style lint 验证 Property 3 三组检查 0 命中（详见 transcript `6_3_quickstart_lint.md` 与 Dogfood_Report `验证与复现 / Verify and Reproduce` Property 3 段）；但用户决定**不**在本里程碑打包成 polish/* 系列 PR、**不**切分支、**不** `git push`，等待后续打包。按 Requirement 7.2「`In_Scope_Fix` 行 `link` 必须是 `https://github.com/<owner>/<repo>/pull/<n>` 且 PR 已 merged」严格判定，5 行 Finding 候选（F-1 ~ F-5）当下不能挂 `In_Scope_Fix` + merged PR URL，按 Requirement 7.5 backlog honesty 暂归 `Out_Of_Scope_Finding` 并挂本 anchor，待 5 个 PR merged 后由 task 9.2 升级回 `In_Scope_Fix` 并把 `link` 替换为真实 PR URL。
- Required deliverables（待用户后续打包成 polish/* 系列 PR 并 merge）:
  - `polish/quickstart-readme` PR merged（覆盖 F-1：`README.md` `### Docker` / `### Manual` / `## Development` 三段）
  - `polish/quickstart-readme-zhcn` PR merged（覆盖 F-2：`README.zh-CN.md` `## 快速开始` 整段）
  - `polish/quickstart-ledger-mcp` PR merged（覆盖 F-3：`docs/ledger_quickstart_mcp.md` Prerequisites + 两个 smoke 块）
  - `polish/quickstart-codex` PR merged（覆盖 F-4：`docs/codex_workflow.md` `## Setup` 三段 + `## Verification`）
  - `polish/quickstart-v01-dogfood` PR merged（覆盖 F-5：`docs/V0_1_DOGFOOD.md` `## Commands` 整段）
  - 每个 PR description 含 `Fixes finding F-<n>` 锚点回 Findings 表对应行
  - 每个 PR diff 仅触及 `docs/` 与 `*.md`（与 design §Schema 6 DOC shape 严格一致；不触及代码 / `.github/` / `mcp-server/` 包源 / 任何 Existing_Release_Tag）
  - 每个 PR 在合并前与合并后即时各跑一次 design §Pre-Merge Gate Checklist 6 项（task 8.3 已为 PR #121 跑过示范，本里程碑期间 5 个分支因未开 PR 6 列全部记 `n/a (PR not opened yet)`，PR 真实 open 后由后续里程碑 / task 8.3 增量回填实采）
- Acceptance:
  - 5 个 PR 全部 merged 到 `main`，且 PR 合并后 `git ls-remote --tags origin` 与 `gh release list --limit 100 --json tagName,publishedAt` 两次 capture 与 task 8.2 baseline byte-identical（Existing_Release_Tag 9 集合 0 变化）；
  - Dogfood_Report `发现与处置 / Findings and Triage` 表对应 5 行（F-1 ~ F-5）由 task 9.2 从 `Out_Of_Scope_Finding` 升级回 `In_Scope_Fix`，`link` 字段从本 anchor 替换为对应 merged PR URL（`https://github.com/<owner>/<repo>/pull/<n>` 形态），`triage_reason` 同步改写为「task 9.2 在 polish/* PR 合并后升级」；
  - Dogfood_Report `不变量保护与遗留 / Invariants and Deferred` 章节 §Pre-Merge Gate Checklist 表对应 5 行 6 列由 `n/a (PR not opened yet)` 替换为合并前 + 合并后即时实采；
  - task 6.3 `验证与复现 / Verify and Reproduce` Property 3 段 5 份 Quickstart_Doc_Set 子表中每行 `Validated commit SHA` 字段从 task 6.1 时刻值升级为 polish merged commit SHA（5 个 PR 各自 squash 合并的 main HEAD SHA），与 Requirement 4.6 / Property 3 audit checklist 一致；
  - 本 anchor 在 Dogfood_Report 与 PLANS.md 的引用同步标记为 closed，附 5 个 PR URL 与 5 个合并后 main HEAD commit SHA。
- Reference:
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/6_1_quickstart_validation.md`
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/6_2_quickstart_polish.md`
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/6_3_quickstart_lint.md`
  - `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/9_1_findings.md`
