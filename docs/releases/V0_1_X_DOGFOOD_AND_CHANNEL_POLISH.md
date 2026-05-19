# ProofFlow v0.1.x Dogfood and Channel Polish — Dogfood Report

> Generated for milestone v0.1.x dogfood-and-channel-polish; not a release artifact

<!--
本文件是 milestone「v0.1.x dogfood-and-channel-polish」的 Dogfood_Report 骨架。
- 章节顺序严格遵循 Requirement 11.2，11 段中英文标题不可调整。
- 占位行仅为 design §Schema 1–6 的字段提示，**不**预填 Pass / Fail，由后续任务回填证据。
- 简体中文叙述 + 英文 EARS 关键词与 shell 命令字符串。
- 含空格的 Windows 路径必须双引号包裹；不允许内嵌本地绝对路径或用户名。
-->

## 摘要 / Summary

> 由 Task 12.1 回填于 `2026-05-19T02:34:03+08:00`，聚合「环境 / Environment」「命令矩阵 / Command Matrix」「三渠道证据 / Channel Evidence」「发现与处置 / Findings and Triage」「CI 状态 / CI Status」「Demo 资产与示例 Proof Packet / Demo and Example Packet」「不变量保护与遗留 / Invariants and Deferred」「验证与复现 / Verify and Reproduce」八段已实采证据；EARS 关键词与 shell 命令字符串保留英文。

本里程碑「v0.1.x dogfood and channel polish」是一次 **process / audit milestone**，主要交付物是文档与证据资产而不是产品代码。本里程碑核心交付包含：(a) 本份 `docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md`（Dogfood_Report 主体，按 Requirement 11.2 严格 11 段顺序 + 9 条 Property audit checklist + 13 条 Definition of Done 勾选清单）；(b) `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`（Public_Proof_Packet_Example，针对 Latest_Main commit `50524582ecf2433e11fa4a8f82bb51a66319aedd` 在隔离 `<TMP>` 环境中通过 Codex MCP 5-tool 调用真实生成）。

本里程碑严格遵守四条硬约束：(1) **不切新 release tag**——Existing_Release_Tag 9 集合 `{v0.1.0, v0.1.0-rc1, v0.1.3, v0.1.3.1, v0.1.4, v0.1.5, v0.1.6, v0.1.6.1, v0.1.8}` 在 milestone start / close / Pre-Merge Gate re-check / post-closure capture-4 四次 capture 全程 byte-identical（`git ls-remote --tags origin` SHA-256 = `0B4AAEAC…329E`；`gh release list` SHA-256 = `CACAB81B…979F`）。(2) **main-only**——所有 Polish_PR 候选通过独立 `polish/<short-slug>` 分支提，从未直接 push `main`；closure PR #121 与 5 份 Quickstart_Doc_Set 修复 PR #122–#126 均已 squash merged 到 `main`，其中 #121 仍仅作为 GHA channel evidence DOC PR，#122–#126 作为 F-1 ~ F-5 的 In_Scope_Fix 载体。(3) **不弱化 Trust_Baseline**——Policy Gate scope 仍严格 `{move_file, rename_file}`（task 2.2 `rc2_policy_gate_smoke.py` 14/14 Pass）；hash-guarded undo 与 sensitive-file omission 用例在 backend pytest 中 Pass（task 2.1 313 passed / 3 skipped）；live DB restore 仍 deferred（task 2.2 `backup_restore_api_smoke.py` 经 `_assert_isolated_paths` 守卫验证，post-run `backend\data\proofflow.db` mtime / size 与 baseline 完全一致）；3 条 smoke 全 Pass。(4) **不引入新产品功能**——本里程碑 0 OPPORTUNISTIC_FIX shape PR、0 net-new feature 关键词命中、0 Policy Gate action 类型扩展。

三渠道结果按 design §Schema 3 严格采集：**MCP_Channel = Pass**（Codex client + 5/6 tools `proofflow_scan` / `proofflow_suggest` / `proofflow_approve_execute` / `proofflow_decide` / `proofflow_export_packet` 实际触发，packet path = `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`）；**GHA_Channel = Pass**（PR #121 触发 `proofflow-pr-review.yml`，4 字段全在：`pr_url` / `run_url` / `artifact_id 7074206493` / `comment_url`，与 CI Status 表 `proofflow-pr-review.yml` Run URL 交叉一致；旧 Run `26045394262` / 旧 artifact `7063049346` 对应 PR #121 首版 head_sha `1ec968be34`，由 closure push commit `6da1b4c` 触发的新 Run `26074265258` 覆盖，主字段以新 Run 为准）；**VSCode_Channel = Deferred**（`vscode-extension` commit SHA `a94d190ce03332c1c480e8d887be2ebf8df9daba`；本里程碑执行环境无可视 VS Code 窗口可抓取，按 design §Error Handling「把降级如实记录而不是粉饰为 Pass」原则挂 PLANS anchor `vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`）。CI 6 个 workflow 在 Latest_Main 全部 `conclusion=success`（`backend.yml` / `frontend.yml` / `lint.yml` / `mcp-server.yml` push-on-main 直查；`proofflow-pr-review.yml` 复用 PR #121 Run；`publish-mcp.yml` 取 `mcp-v0.1.2` baseline）。

7 条 Findings（F-1 ~ F-7）按 Requirement 7.2 / 7.5 严格判定并在 post-closure audit refresh 后更新：F-1 ~ F-5 是 5 份 Quickstart_Doc_Set polish（README.md / README.zh-CN.md / docs/ledger_quickstart_mcp.md / docs/codex_workflow.md / docs/V0_1_DOGFOOD.md），已通过 PR #122–#126 squash merged 到 `main`，归类为 `In_Scope_Fix` 且 `link` 列为裸 merged PR URL；F-6 是 VSCode 截图与 Demo_Asset GIF 同根因 deferred（用户 Option E 决策合并 anchor）挂 `vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`；F-7 是 AgentGuard public packet 缺席（用户 Option C 决策仅交付 LocalProof 一份）挂 `agentguard-public-packet-deferred-from-v0-1-x-dogfood`。7 行 8 字段全填，5 行 `In_Scope_Fix` + 2 行 `Out_Of_Scope_Finding`，0 静默丢弃。

### what changed / 本次改动

- 新增 `docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md`（11 H2 段 + 9 条 Property audit checklist + 13 行 DoD 勾选清单），由 task 1.1 ~ 12.1 增量回填实采证据。
- 新增 `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`（task 7.1 通过 Codex MCP 5-tool 真实生成，顶部含 Latest_Main commit SHA + ISO8601 + generator command 用 `<TMP>` 占位符脱敏 + 「not a release artifact」声明 + Case ID `8fadcdce-…`）。
- 新增 `docs/assets/README.md` 与 `docs/examples/README.md`（task 1.3 目录脚手架 + Windows 路径双引号约束说明）。
- 更新 `CHANGELOG.md` `## Unreleased` 段插入 Dogfood_Report 仓库相对路径链接（task 1.2，不切新 release tag、不修改任何 Existing_Release_Tag 段）。
- post-closure audit refresh 将 5 份 Quickstart_Doc_Set 的 polish 修复从本地 working tree 状态升级为已合并证据：PR #122–#126 分别落地 README.md / README.zh-CN.md / docs/ledger_quickstart_mcp.md / docs/codex_workflow.md / docs/V0_1_DOGFOOD.md 的 `Push-Location` / `Pop-Location`、端口 `8787`、`proofflow.main:app`、`pip install proofflow-mcp` 与含空格路径双引号修复。
- 新增并维护 `PLANS.md` 三段 Backlog anchor（task 9.3）：`vscode-channel-screenshots-deferred-from-v0-1-x-dogfood` / `agentguard-public-packet-deferred-from-v0-1-x-dogfood` 仍支撑 F-6 / F-7；`quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood` 已由 post-closure audit refresh 标记 CLOSED，并附 PR #122–#126 URL。
- 新增 task 1.1 ~ 12.1 系列 transcripts 在 `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/` 目录下，作为 audit trail。

### why / 为什么

- 满足 Requirement 1 ~ 13 全部 EARS acceptance criteria（process / audit milestone 形态约束）：Dogfood_Report 11 H2 段 + 三渠道 evidence-backed pass / deferred + 6 workflow CI green + Trust_Baseline 6 条不变量 + Tag immutability。
- 落地 design §Correctness Properties 9 条 audit-style invariants（Property 1 ~ 9）作为 milestone close 时 DoD-13 的同文档锚点验收路径，**不**引入 Hypothesis / QuickCheck / fast-check 等 PBT 框架（design §Testing Strategy 显式 Non-Goal）。
- 在 fresh Windows clone 单一 PowerShell 会话上，复现一次端到端「ProofFlow 仍能在 Latest_Main 上以三渠道形态 audit 真实 AI agent 行为」的可粘贴证据，为 Codex OSS 评审与新用户首次成功体验提供「双签」级 Public_Proof_Packet_Example。
- 维持 v0.1 Trust_Baseline：Policy Gate scope / hash-guarded undo / sensitive-file omission / live DB restore deferred / Existing_Release_Tag immutability / AGENTS.md「destructive action 三段式」全部 0 改动，使 v0.2 的下一阶段开发在不破坏现有 audit 契约的前提下推进。

### how to verify or reproduce / 如何验证

- 引用「验证与复现 / Verify and Reproduce」H2 段 Property 1 ~ 9 audit checklist：每个 Property 子节包含 `check command` / `expected` / `result` 三字段，全部可在 fresh Windows clone 单一 PowerShell 会话粘贴执行（含空格路径双引号包裹；`Push-Location "<repo root>"` / `Pop-Location` 配对锁定 cwd）。
- 关键复现命令组合：(a) Property 1 `python` 解析 Pass / Fail / Deferred token 行 + ripgrep `<TBD` 全文 0 命中；(b) Property 4 `git ls-remote --tags origin` + `gh release list --limit 100 --json tagName,publishedAt` 双 capture `Get-FileHash -Algorithm SHA256` 与 `0B4AAEAC…329E` / `CACAB81B…979F` 比对；(c) Property 5 `python -m pytest -q -k "undo or omission or hash_guard or sensitive"` + 3 smoke 全 Pass。
- audit trail：本里程碑全程 transcripts 集中于 `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/`（task 1.1 ~ 12.1）。

### what was intentionally not done / 有意未做

- VSCode_Channel inline audit + Approve Gate 截图与 Demo_Asset GIF 同根因 deferred（本里程碑执行环境无可视 VS Code 窗口可抓取），按 design §Error Handling 严禁伪造 / 占位 / 后期合成 evidence；3 路径 `docs/assets/proofflow-v0_1_x-vscode-inline-audit.png` / `proofflow-v0_1_x-vscode-approve-gate.png` / `proofflow-v0_1_x-vscode-flow.gif` 在本里程碑期间一律保持 `Path.exists() = False`。
- AgentGuard Public_Proof_Packet_Example 缺席（按用户 Option C 仅交付 LocalProof 一份）；与 Trust_Baseline 不变量无关，挂 PLANS anchor 留待下个 dogfood 周期补齐。
- PR #127 自身 GHA evidence 仅作为 audit refresh PR body self-evidence，不写入本报告的 GHA_Channel 主字段；GHA_Channel 主证据保持绑定 PR #121，避免把刷新 PR 的自检结果写成里程碑主证据造成自指循环。
- Definition of Done 13 条勾选清单 13 行 `<TBD>` 锚点占位由 task 12.2 后续回填，不在本任务范围；**未**引入任何 PBT 框架；**未**改动 Existing_Release_Tag 9 集合 / Policy Gate 注册路径 / `backend/data/` 目录 / 任何源码（`backend/` / `frontend/` / `mcp-server/` / `scripts/` / `.github/`）。

### recommended next step / 推荐下一步

- 引用「推荐下一步 / Recommended Next Step」H2 段。

## 范围与非目标 / Scope and Non-Goals

> 由 Task 12.1 回填于 `2026-05-19T02:34:03+08:00`。In scope 5 条来自 task 1.1 骨架 Schema 复用 + 实采化；Non-Goals 8 条逐条复用 design §Non-Goals（强约束），任一条触及 SHALL be rejected and routed to a separate spec。

In scope:

- Dogfood end-to-end run on a fresh Windows clone against Latest_Main（task 2.1 / 2.2 / 2.3 实采：8 条 Command Matrix 行全部 `actual_status = Pass`，含 `python -m pytest`（`backend/`，313 passed / 3 skipped）/ `npm ci` / `npm test`（vitest 7 files / 29 tests passed）/ `npm run build` / 4 条 smoke）。
- Three Distribution_Channel evidence collection（MCP_Channel / VSCode_Channel / GHA_Channel，task 4.1 / 4.2 / 4.3 / 4.4 实采按 design §Schema 3 三 block 形态 + channel-specific required fields）。
- Quickstart_Doc_Set validation in a single PowerShell session（task 6.1 / 6.2 / 6.3 实采：5 份文档全部跑过，stale 步骤在 working tree 已修复，task 6.3 lint `^cd ` / 非 8787 端口 / 含空格路径未引号 三段命中数 0/0/0）。
- Demo_Asset under `docs/assets/` and Public_Proof_Packet_Example under `docs/examples/`（task 7.1 / 7.2 / 7.3 / 7.4 实采：LocalProof packet 落地 + Demo_Asset GIF 同根因 deferred 形态合规 + 3 处 user-facing Quickstart placeholder note）。
- Opportunistic Polish_PRs landed on `main` only（task 9.1 / 9.2 / 9.3 + post-closure audit refresh 实采：PR #121 为 GHA channel evidence DOC PR、非 In_Scope_Fix；F-1 ~ F-5 对应的 In_Scope_Fix Polish_PR merged 集合 = {#122, #123, #124, #125, #126}，均为 DOC shape 并通过独立 `polish/quickstart-*` 分支合并；按 design §GHA Channel Trigger Strategy 与 Requirement 8.1）。

Non-Goals（强约束，触及任一条 SHALL be rejected and routed to a separate spec）:

1. 不引入新产品功能（含 Roadmap #59 multi-agent / #60 vector RAG / #61 webhooks 等）。
2. 不扩展 Policy Gate 的 action 类型范围（保持 `{move_file, rename_file}`；`mkdir_dir` 由 action_safety 处理，不在 Policy Gate 范围内扩展）。
3. 不解封 live DB restore；Foundation 阶段「No Restore to live DB」不变量不动。
4. 不切新的 GitHub release tag；不移动 / 删除 / 重发任何 Existing_Release_Tag（`v0.1.0` / `v0.1.0-rc1` / `v0.1.3` / `v0.1.3.1` / `v0.1.4` / `v0.1.5` / `v0.1.6` / `v0.1.6.1` / `v0.1.8`）。
5. 不引入云上传 / cloud sync / 远程 telemetry / Docker 范围扩展 / 多用户工作流。
6. 不把 Demo_Asset 上传到任何外部对象存储或第三方视频站；所有资产必须落进 `docs/`。
7. 不引入「自动 AI 代码编辑」类功能；human-in-the-loop final review 仍是不可绕过的一步。
8. 不弱化 AGENTS.md 中已有的安全不变量与「destructive action 三段式（dry-run / approval / undo）」要求。

## 环境 / Environment

> 由 Task 2.3 回填于 `2026-05-18T23:45:17+08:00`，聚合 transcripts `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/2_1_backend_frontend.md` 与 `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/2_2_smoke_matrix.md` 中的实采字段。
> 不写入机器名或本地绝对路径；含空格的 Windows 路径双引号包裹。

| Field | Value | Source command |
| --- | --- | --- |
| `os_build` | `Microsoft Windows NT 10.0.19045.0` | `[System.Environment]::OSVersion.VersionString` |
| `python_version` | `Python 3.12.10` | `python --version` |
| `node_version` | `v24.15.0` | `node --version` |
| `npm_version` | `11.12.1` | `npm --version` |
| `commit_sha` | `50524582ecf2433e11fa4a8f82bb51a66319aedd` | `git rev-parse HEAD` |
| `branch_name` | `main` | `git rev-parse --abbrev-ref HEAD` |
| `dogfood_started_at` | `2026-05-18T23:35:00+08:00` | manual（覆盖 transcript 2.1 vitest `Start at 23:39:38` 之前的 pytest 与 `npm ci` 起始时刻；用于 bound 本里程碑迄今 evidence 采集起点） |
| `dogfood_finished_at` | `2026-05-18T23:45:17+08:00` | manual（`Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"`，本里程碑迄今 evidence 采集终点） |

环境隔离（dogfood 实际形态；仅记录形态，不记录真实路径中的用户名）：

- `$env:PROOFFLOW_TMP = "$env:TEMP\proofflow-dogfood-$(Get-Date -Format yyyyMMdd-HHmmss)"`
- `$env:PROOFFLOW_DB_PATH = "$env:PROOFFLOW_TMP\proofflow.db"`
- `$env:PROOFFLOW_DATA_DIR = "$env:PROOFFLOW_TMP\data"`

> 注：`scripts/*_smoke.py` 内部会再次 `tempfile.mkdtemp(...)` 并以脚本自身路径覆盖 `PROOFFLOW_DB_PATH` / `PROOFFLOW_DATA_DIR`，因此外部注入对脚本最终路径无实际影响；仍按上述形态注入以满足 fresh PowerShell session 的 copy-paste 友好约束（详见 transcript `2_2_smoke_matrix.md` §环境隔离策略）。`backup_restore_api_smoke.py` 内含 `_assert_isolated_paths` 守卫，从源码层面拒绝写入仓库 `backend\data\`。

## 命令矩阵 / Command Matrix

> 由 Task 2.3 回填于 `2026-05-18T23:45:17+08:00`，聚合 transcripts `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/2_1_backend_frontend.md`（4 条 backend/frontend）与 `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/2_2_smoke_matrix.md`（4 条 smoke）。
> 任何「未跑过的命令」也必须以 `actual_status = Fail` + `evidence: not run, reason: <降级原因>` 写入；不允许从矩阵中删除。本次 8 条全部 `actual_status = Pass`。
> 含空格的 Windows 路径双引号包裹；不内嵌真实用户名或机器名（tmp 路径用 `<TMP>` 占位符）。

| `cmd` | `cwd` | `expected` | `actual_status` | `evidence` | `notes` |
| --- | --- | --- | --- | --- | --- |
| `python -m pytest -q` | `backend\` | `exit 0; 0 failed tests` | `Pass` | `LASTEXITCODE=0; 313 passed, 3 skipped in 46.22s`（transcript `2_1_backend_frontend.md` §1） | `python --version → Python 3.12.10; pytest 9.0.3; 3 skipped 为平台条件用例` |
| `npm ci --no-audit --no-fund` | `frontend\` | `lockfile-consistent install; exit 0` | `Pass` | `LASTEXITCODE=0; added 119 packages in 10s; Test-Path "frontend\node_modules" → True (93 子目录)`（transcript `2_1_backend_frontend.md` §2） | `node --version → v24.15.0; npm --version → 11.12.1; lockfile drift 未复现` |
| `npm test --silent` | `frontend\` | `exit 0; 0 failed tests` | `Pass` | `LASTEXITCODE=0; vitest 4.1.6 → Test Files 7 passed (7) / Tests 29 passed (29) / Duration 12.83s`（transcript `2_1_backend_frontend.md` §3） | `package.json scripts.test → vitest run` |
| `npm run build` | `frontend\` | `tsc -b && vite build artifacts written; exit 0` | `Pass` | `LASTEXITCODE=0; vite v8.0.13 built in 480ms; "frontend\dist\index.html" + "frontend\dist\assets\index-*.{js,css}" 均存在`（transcript `2_1_backend_frontend.md` §4） | `package.json scripts.build → tsc -b && vite build` |
| `python .\scripts\rc_api_smoke.py` | `.` | `exit 0; RC API surface green` | `Pass` | `exit 0; ProofFlow v0.1.0 API smoke passed.; LocalProof case e4cd00be-... (4 actions); AgentGuard case 20767e5b-...; Proof Packet "<TMP>\proofflow-rc-api-smoke-t_33s0b5\data\proof_packets\20767e5b-...ac0bf.md"`（transcript `2_2_smoke_matrix.md` Command 1） | 隔离 env 注入：`$env:PROOFFLOW_TMP / PROOFFLOW_DB_PATH / PROOFFLOW_DATA_DIR` 指向 `$env:TEMP\proofflow-dogfood-<ts>`；脚本内部 `tempfile.mkdtemp` 再隔离 |
| `python .\scripts\rc2_policy_gate_smoke.py` | `.` | `exit 0; Policy Gate scope = {move_file, rename_file}` | `Pass` | `exit 0; RC2 Policy Gate Smoke: 14 passed, 0 failed; pending_decision fail-closed (step 4 + step 7); decision 解锁后 file moved (step 6)`（transcript `2_2_smoke_matrix.md` Command 2） | Policy Gate action types invariant 保持：仅 `move_file` 注册路径被验证 |
| `python .\scripts\backup_restore_api_smoke.py` | `.` | `exit 0; no live DB restore path` | `Pass` | `exit 0; ProofFlow backup/restore API smoke passed.; Backup ID backup-20260518T154048Z-6e24d224; Restored DB path "<TMP>\proofflow-backup-restore-smoke-51p9cm92\restore\proofflow-restored.db" ≠ live DB`（transcript `2_2_smoke_matrix.md` Command 3） | 不变量 `No Restore to live DB in foundation phase`：脚本源码 `_assert_isolated_paths` 拒绝写入仓库 `backend\data\`；post-run audit `backend\data\proofflow.db` mtime 与 size 与 baseline 完全一致 |
| `python .\scripts\ci_agentguard_review.py --help` | `.` | `exit 0; help text printed` | `Pass` | `exit 0; < 1 秒返回 argparse usage: usage: ci_agentguard_review.py [-h] [--repo-root REPO_ROOT] [--base-ref BASE_REF] [--output-dir OUTPUT_DIR] [--artifact-name ARTIFACT_NAME] [--include-untracked | --no-include-untracked]`（transcript `2_2_smoke_matrix.md` Command 4） | 仅本地可执行性 smoke；实际 PR review 由 GHA_Channel（task 4.3）触发 |

## 三渠道证据 / Channel Evidence

> 由 Task 4.4 回填于 `2026-05-19T00:44:26+08:00`，聚合 transcripts `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/4_1_mcp_channel.md` / `4_2_vscode_channel.md` / `4_3_gha_channel.md`。
> 每个 block 严格按 design §Schema 3 字段顺序：`Outcome` → `Evidence` → `Tool / Workflow / View` → `Backing Polish_PR / Backlog_Entry` → `Notes`；channel-specific 额外字段（MCP 的 `Client` / `Tools invoked`、VSCode 的 `vscode-extension commit SHA at deferral`）按 design §Correctness Properties Property 2 「channel-specific required fields」契约就近挂在 `Outcome` 与 `Evidence` 之间，**不**改动 5 个核心字段的相对顺序。
> Evidence type 来自固定枚举：`command` / `log_excerpt` / `screenshot` / `recording` / `proof_packet_path` / `pr_url` / `run_url` / `artifact_id` / `comment_url`。
> `Outcome` 仅取 `Pass` / `Deferred`，**不**使用 `Mostly Pass` / `Skipped (assumed ok)` 含糊词；`Outcome = Deferred` 行已挂 Backlog_Entry（GitHub issue URL 或 `PLANS.md#anchor`）并在 `Notes` 给出降级理由。

### Channel: MCP

- Outcome: Pass
- Client: Codex（通过 `.codex/config.toml` + 仓库根 `.mcp.json` 加载 `proofflow-mcp` 的 6-tool surface）
- Tools invoked (5 of 6): `proofflow_scan` / `proofflow_suggest` / `proofflow_approve_execute` / `proofflow_decide` / `proofflow_export_packet`（`proofflow_review` 在 LocalProof workflow 不适用，by-design 由 GHA_Channel `proofflow-pr-review.yml` 覆盖 review 路径）
- Evidence:
  - `command`: `python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787 --reload` (cwd `backend/`)
  - `command`: `proofflow_export_packet(case_id="8fadcdce-245d-4b90-8531-f28916575a6e")`（Codex MCP tool 调用形态，由 AI client 通过 `.mcp.json` 加载的 `proofflow-mcp` server 转发到 backend `http://127.0.0.1:8787`）
  - `log_excerpt`: `Scan complete. Case ID: 8fadcdce-245d-4b90-8531-f28916575a6e` / `Decision created. Decision ID: e0d9092c-58b9-420f-98dc-f8bdcd63e2dd` / `Action executed successfully. (move_file, undo=restore_file with from_sha256 guard)` / `Proof Packet exported for Case 8fadcdce-245d-4b90-8531-f28916575a6e.`（来自 transcript `4_1_mcp_channel.md` §「用户提供的 log 摘录」）
  - `proof_packet_path`: `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`
- Tool / Workflow / View: `proofflow-mcp` (`.mcp.json`) → 5 tools: `proofflow_scan` / `proofflow_suggest` / `proofflow_approve_execute` / `proofflow_decide` / `proofflow_export_packet`
- Backing Polish_PR / Backlog_Entry: n/a (Outcome=Pass; not part of PR-bound Polish_PR set)
- Notes: `proofflow_review` 在本次 LocalProof file_cleanup 工作流中 by-design 不适用，其 surface 由 GHA_Channel 的 `.github/workflows/proofflow-pr-review.yml` 在真实 PR #121 上覆盖（design §Channel 1 / §Channel 3 已显式分工），因此「5/6 tools invoked」满足 Requirement 2.2「invoked at least one of the six tools」与 Property 2「at least one tool name in the 6-tool enum」的下限契约。Public Proof Packet `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md` 顶部已记录 Latest_Main commit SHA `50524582ecf2433e11fa4a8f82bb51a66319aedd`、ISO8601 生成时间、完整 generator command（路径用 `<TMP>` 占位符）、声明「Generated for milestone v0.1.x dogfood; not a release artifact」、Case ID `8fadcdce-…`，且 packet 内 `[A-Z]:\\Users\\` / `[A-Z]:/Users/` 真实绝对路径形态 grep 0 命中（脱敏 self-check 通过）。本任务采集过程仅 read_file / grep_search / fs_write transcript，**不**触及 Existing_Release_Tag 集合 / Policy Gate action 类型集合（仍仅 `move_file` / `rename_file`）/ live DB restore / `backend/data/` 目录。Audit trail：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/4_1_mcp_channel.md`。

### Channel: VSCode

- Outcome: Deferred
- vscode-extension commit SHA at deferral: `a94d190ce03332c1c480e8d887be2ebf8df9daba`
- Evidence:
  - `<empty: no screenshot/recording produced this milestone>`
- Tool / Workflow / View: LocalProof Case + AgentGuard Case + Approve Gate（计划但未在本里程碑执行）
- Backing Polish_PR / Backlog_Entry: `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`
- Notes: 降级理由：本里程碑 dogfood 执行环境暂无可抓取的 VS Code 可视窗口，无法在本里程碑内真实产出 inline audit + Approve Gate 截图与 demo flow GIF。按 design §Error Handling「把降级如实记录而不是粉饰为 Pass」与 Requirement 2.5，`Outcome` 标记为 `Deferred` 而非 `Pass`，并显式挂 `Backing Polish_PR / Backlog_Entry` 锚点 `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`。本里程碑严禁伪造、占位、或后期合成 evidence（**no fake-evidence、no placeholder PNG/GIF**）：仓库内 `docs/assets/proofflow-v0_1_x-vscode-inline-audit.png` / `docs/assets/proofflow-v0_1_x-vscode-approve-gate.png` / `docs/assets/proofflow-v0_1_x-vscode-flow.gif` 三个路径在本里程碑期间一律保持 `Path.exists() = False`，避免 Property 1（Dogfood evidence completeness）误判命中。下一个 dogfood 周期补齐 evidence 时必须满足的 acceptance criteria（关键操作步骤、必须落地的 evidence 文件、隐私脱敏 5 项、回填位置）见 `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood` 与 transcript `4_2_vscode_channel.md` §Acceptance criteria。Audit trail：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/4_2_vscode_channel.md`。

### Channel: GHA

- Outcome: Pass
- Evidence:
  - `pr_url`: <https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/121>
  - `run_url`: <https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/26074265258>
  - `artifact_id`: `7074206493`
  - `comment_url`: <https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/121#issuecomment-4479556510>
- Tool / Workflow / View: `.github/workflows/proofflow-pr-review.yml`（job `agentguard-review`，由 `pull_request` 事件触发，复用 `scripts/ci_agentguard_review.py` 跑 AgentGuard review、上传 Proof Packet artifact、并发表稳定 PR 评论）
- Backing Polish_PR / Backlog_Entry: <https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/121>
- Notes: PR #121 是**纯文档 Polish_PR**（DOC shape，design §Schema 6），**非 In_Scope_Fix**——其用途显式声明为「专门为触发 GHA review 而提」，与 design §GHA Channel Trigger Strategy / Requirement 2.4 一致：当本里程碑当下无 In_Scope_Fix 可作 review 载体时，提一个纯文档微小 PR 触发 workflow，不构造假修复也不污染 In_Scope_Fix 集合。触发路径合规：PR 走 `pull_request` 事件触发 workflow，**未**在 `main` 上直接 push、**未**重新触发任何 Existing_Release_Tag（`v0.1.0` / `v0.1.0-rc1` / `v0.1.3` / `v0.1.3.1` / `v0.1.4` / `v0.1.5` / `v0.1.6` / `v0.1.6.1` / `v0.1.8`）上的 workflow（满足 Requirement 8.1 / 8.2 / 8.4）。同 PR #121 同时复用为 task 8.3（Pre-Merge Gate Checklist 6 项）/ 9.2（In_Scope_Fix 与 DOC shape 区分登记）/ 10.6（Property 6 — Polish-only diff shape 分类）的 audit 载体；`comment_url` 同时是本 GHA block 与「发现与处置 / Findings and Triage」表对应行的交叉引用锚点（ProofFlow auto-comment 是 update-in-place 模式：closure push 后同一条 `#issuecomment-4479556510` 由新 Run 覆盖更新，`updated_at = 2026-05-19T03:25:26Z`，URL 不变）。四条 URL 已通过本地 regex / 一致性矩阵校验（pr_url ↔ comment_url `pull/121` 一致；pr_url ↔ run_url owner/repo `Hyperion-GPU/ProofFlow-v0.1` 一致；artifact_id 纯数字 `7074206493`），**不**对外网发请求（AGENTS.md `localhost as the default trust boundary`）。GHA Run 历史：首版 PR head_sha `1ec968be34` 触发 Run `26045394262` (artifact `7063049346`, conclusion=success, createdAt `2026-05-18T16:09:26Z`)；closure push commit `6da1b4c` 触发新 Run `26074265258` (artifact `7074206493`, conclusion=success, createdAt `2026-05-19T03:25:08Z`)，与 PR 最终 head_sha 对齐——主字段以新 Run 为准，旧 Run 保留作为首版 evidence 历史。Audit trail：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/4_3_gha_channel.md`。

## 发现与处置 / Findings and Triage

> 由 Task 9.1 回填于 `2026-05-19T02:03:35+08:00`，登记 7 条 Dogfood_Finding；2026-05-19T14:08+08:00 由 task 9.2 post-closure audit refresh 把 F-1 ~ F-5 5 行的 `classification` 从 `Out_Of_Scope_Finding` 升级为 `In_Scope_Fix`（5 个 polish/quickstart-* PR 已 squash merged 到 `main`，PR #122 / #123 / #124 / #125 / #126，merged commits `7a49da4` / `277fb0c1` / `3a5195be` / `fdac327a` / `2575785b`），`link` 字段从 PLANS anchor 替换为对应 merged PR URL；F-6 / F-7 仍为 `Out_Of_Scope_Finding`，引用既有 deferred anchor（VSCode + Demo_Asset GIF / AgentGuard public packet 留待下个 dogfood 周期补齐）。Audit trail：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/9_1_findings.md` + post-closure refresh transcript（本次 audit refresh PR 落地后由 task 9.2 写入）。
> 每行八字段全部必填；`In_Scope_Fix` 行 `link` 必须为已 merged 的 PR URL；`Out_Of_Scope_Finding` 行 `link` 必须为 GitHub issue URL（标题前缀 `[backlog from v0.1.x dogfood]`）或 `PLANS.md#<anchor>`。
> 「无 link」行不允许（Requirement 7.5 / 13.7）；不允许 `Mostly Pass` / `Skipped (assumed ok)` / 含糊词。

| `id` | `title` | `repro` | `observed` | `expected` | `classification` | `triage_reason` | `link` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `F-1` | README.md Quickstart 段裸 cd 与 && 串联使 PowerShell 单会话执行链断裂 | 单一 PowerShell 单会话粘贴 README.md `## Quickstart` `### Docker` / `### Manual` 段与 `## Development` 段全部命令；不允许人工临时手动调整 `cd` | L113 `cd ProofFlow-v0.1`、L138 `cd backend && pip install -r requirements.txt` + L140 `python -m uvicorn proofflow.main:app --port 8787`、L142 `cd frontend && npm ci && npm run dev`、L290 `cd backend && python -m pytest`、L291 `cd frontend && npm run test`、L292 `cd mcp-server && pip install -e ".[dev]" && python -m pytest` 共 5 处裸 `cd` + `&&` 串联；后续 L296–L300 `python scripts/...` 在 cwd 已被 L292 切到 `mcp-server/` 后必须人工 `cd ..` 才能跑通（implicit-cwd carryover） | 每段子目录命令使用 `Push-Location <subdir>; ...; Pop-Location` 包裹，结束后 cwd 自动回到仓库根，使后续 `python scripts/...` 可在同一会话粘贴执行；端口固定 `8787`；`npm run dev` 长驻进程在第二个 PowerShell 会话执行的提示显式给出 | `In_Scope_Fix` | task 6.2 已在 working tree 修复（`Push-Location` / `Pop-Location` 形态、端口 `8787`、`npm run dev` 第二会话提示），task 6.3 lint 0 stale；用户 Option B 暂不打包成 PR，按 Requirement 7.5 backlog honesty 暂归 `Out_Of_Scope_Finding` 并挂 `PLANS.md#quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood`；2026-05-19 `polish/quickstart-readme` 打包成 PR #122 squash merged 到 `main` (commit `7a49da471b0af7cc2b7445f50e51d5e0146a5473`)，由 task 9.2 post-closure audit refresh 升级 classification → `In_Scope_Fix`、`link` → merged PR URL | https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/122 |
| `F-2` | README.zh-CN.md backend 入口/端口与 README.md 不一致 + 引用不存在的 requirements.txt | 单一 PowerShell 单会话按 README.zh-CN.md `## 快速开始` 段顺序粘贴 backend / frontend / mcp-server 三块命令 | L56 / L66 / L74 三处裸 `cd`；L61 `uvicorn app.main:app --reload` 缺 `--port 8787`（uvicorn 默认 `:8000`）且 entry 应为 `proofflow.main:app`（与 `backend/app/main.py` 兼容垫片不一致地暴露给用户）；L78 `pip install -r requirements.txt`（在 `mcp-server/`）引用不存在的 `mcp-server/requirements.txt`；L79 `python -m proofflow_mcp.server` 与 README.md L172 `pip install proofflow-mcp` console-script 入口契约相矛盾；6 类 lint 共命中 6 处 | 三段子目录命令使用 `Push-Location` / `Pop-Location` 包裹；backend 段 entry 与端口与 README.md / V0_1_DOGFOOD.md 完全一致（`python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787 --reload`）；MCP server 段对齐 README.md `pip install proofflow-mcp` + `.mcp.json` 配置；保留可选「源码安装」路径并显式说明「`mcp-server/` 由 `pyproject.toml` 管理依赖，无独立 `requirements.txt`」；6 类 lint 全部 0 命中 | `In_Scope_Fix` | task 6.2 已在 working tree 修复（`Push-Location` / `Pop-Location` 形态 + 端口 `8787` + entry `proofflow.main:app` + MCP 入口收敛到 `pip install proofflow-mcp` console-script），task 6.3 lint 0 stale；用户 Option B 暂不打包成 PR，按 Requirement 7.5 backlog honesty 暂归 `Out_Of_Scope_Finding` 并挂 `PLANS.md#quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood`；2026-05-19 `polish/quickstart-readme-zhcn` 打包成 PR #123 squash merged 到 `main` (commit `277fb0c1def1e95c12a3d2a1eaaf96fb6deddc6d`)，由 task 9.2 post-closure audit refresh 升级 classification → `In_Scope_Fix`、`link` → merged PR URL | https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/123 |
| `F-3` | docs/ledger_quickstart_mcp.md smoke 命令依赖 implicit cwd 仓库根 | 按文档顺序在 PowerShell 中复制粘贴 L13–L17 与 L19–L23 两个 bash 块；不允许人工临时手动调整 cwd | L15 `python scripts/ledger_mcp_smoke.py --cleanup` / L21 `python scripts/ledger_risk_hints_smoke.py --cleanup` 两条命令的 `scripts/...` 路径依赖 implicit cwd = 仓库根，文档前文未显式声明 cwd 也未用 `Push-Location` 包裹；Prerequisites bullet 列出 `D:\ProofFlow v0.1` 但路径未双引号包裹 | 在每个 smoke 块前用 `Push-Location .` 显式锁定 cwd，fenced block 类型从 ```bash``` 改为 ```powershell```；Prerequisites bullet 中的示例路径用 `"D:\ProofFlow v0.1"` 双引号包裹并加注「PowerShell quotes the path because it contains a space」；其余 11 段 MCP tool 调用 JSON 示例不动 | `In_Scope_Fix` | task 6.2 已在 working tree 修复（两个 smoke 块 `Push-Location .` 包裹 + Prerequisites 双引号），task 6.3 lint 0 stale；用户 Option B 暂不打包成 PR，按 Requirement 7.5 backlog honesty 暂归 `Out_Of_Scope_Finding` 并挂 `PLANS.md#quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood`；2026-05-19 `polish/quickstart-ledger-mcp` 打包成 PR #124 squash merged 到 `main` (commit `3a5195be9458ad5de52e566557e1c3c79b160920`)，由 task 9.2 post-closure audit refresh 升级 classification → `In_Scope_Fix`、`link` → merged PR URL | https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/124 |
| `F-4` | docs/codex_workflow.md Setup 裸 cd ProofFlow-v0.1/backend 导致 Step 3 cwd 错位 | 在父目录开始按 `## Setup` 段 Step 1 → Step 2 → Step 3 顺序粘贴；不允许人工临时手动调整 cwd | L18 `cd ProofFlow-v0.1/backend`（裸 `cd` + 正斜杠分隔符与跨文档反斜杠风格漂移）；L19 / L20 `pip install -r requirements.txt` / `python -m uvicorn proofflow.main:app --port 8787` 依赖 L18 留下的 implicit cwd = `backend/`；L40 `pip install -e mcp-server/` 期望 cwd = 仓库根，但前文 L18 已 `cd` 到 `backend/`，新读者粘贴时会在 `backend/` 上下文跑该命令而失败；L155 `python scripts/mcp_smoke.py --cleanup` 同样依赖仓库根 cwd 假设 | L18–L20 改为 `Push-Location ProofFlow-v0.1\backend; pip install -r requirements.txt; python -m uvicorn proofflow.main:app --port 8787; Pop-Location`，分隔符统一为反斜杠；L40 单独成段 `Push-Location ProofFlow-v0.1; pip install -e mcp-server\; Pop-Location`；L155 Verification 段 `Push-Location ProofFlow-v0.1; python .\scripts\mcp_smoke.py --cleanup; Pop-Location`；fenced block 全部改为 ```powershell``` | `In_Scope_Fix` | task 6.2 已在 working tree 修复（Setup 三段 + Verification 段 `Push-Location` / `Pop-Location` 包裹 + 分隔符统一），task 6.3 lint 0 stale；用户 Option B 暂不打包成 PR，按 Requirement 7.5 backlog honesty 暂归 `Out_Of_Scope_Finding` 并挂 `PLANS.md#quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood`；2026-05-19 `polish/quickstart-codex` 打包成 PR #125 squash merged 到 `main` (commit `fdac327a384e6fde37d9f5469beaac8b2272d9bd`)，由 task 9.2 post-closure audit refresh 升级 classification → `In_Scope_Fix`、`link` → merged PR URL | https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/125 |
| `F-5` | docs/V0_1_DOGFOOD.md 5 个 PowerShell 块裸 cd "..." 违反 Property 3 lint | 单一 PowerShell 单会话顺序粘贴 `docs/V0_1_DOGFOOD.md` `## Commands` 段全部 5 个 PowerShell 块；不允许人工临时手动调整 cwd | L31 `cd "<repo root>"` / L46 `cd "<repo root>\backend"` / L53 `cd "<repo root>\backend"` / L60 `cd "<repo root>\frontend"` 路径双引号合规但仍是裸 `cd`，按 Property 3 lint 规则 `^cd ` 命中 = 0 视为 stale；L33 / L37 / L48 / L55 / L62–L65 全部依赖前一步 `cd` 的 implicit cwd（含 L37 `python .\scripts\rc_api_smoke.py` 隐式假设 L31 的 `<repo root>` cwd 仍然有效） | 5 个 PowerShell 块统一改造为 `Push-Location "<repo root>"` / `Push-Location "<repo root>\backend"` / `Push-Location "<repo root>\frontend"` 包裹，每段以 `Pop-Location` 结尾；保留所有命令的实际语义；含空格路径双引号继续保持；端口 `8787` 与 entry `proofflow.main:app` 已合规无需改动；标注 backend uvicorn / `npm run dev` 长驻进程建议第二个会话 | `In_Scope_Fix` | task 6.2 已在 working tree 修复（5 个 PowerShell 块 `Push-Location` / `Pop-Location` 包裹 + 长驻进程注释），task 6.3 lint 0 stale；用户 Option B 暂不打包成 PR，按 Requirement 7.5 backlog honesty 暂归 `Out_Of_Scope_Finding` 并挂 `PLANS.md#quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood`；2026-05-19 `polish/quickstart-v01-dogfood` 打包成 PR #126 squash merged 到 `main` (commit `2575785bcb7b9f70239cbf993f5ad53e062ed7fa`)，由 task 9.2 post-closure audit refresh 升级 classification → `In_Scope_Fix`、`link` → merged PR URL | https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/126 |
| `F-6` | VSCode_Channel inline audit + Approve Gate 截图与 Demo_Asset GIF 同根因 deferred | 启动 `vscode-extension/` 扩展连接 backend `http://127.0.0.1:8787`，触发一次 LocalProof Case 与一次 AgentGuard Case，按 design §Channel 2 操作步骤录制 inline 标注 + Approve Gate 解锁 + Undo + 端到端 demo flow | 本里程碑执行环境暂无可视 VS Code 窗口可抓取，3 个 evidence 文件（`docs/assets/proofflow-v0_1_x-vscode-inline-audit.png` / `docs/assets/proofflow-v0_1_x-vscode-approve-gate.png` / `docs/assets/proofflow-v0_1_x-dogfood-<channel>.gif`）`Path.exists() = False`；Channel Evidence VSCode block `Outcome = Deferred`（task 4.2 / 4.4 已记录） | `docs/assets/proofflow-v0_1_x-vscode-inline-audit.png` + `docs/assets/proofflow-v0_1_x-vscode-approve-gate.png` + 可选 `docs/assets/proofflow-v0_1_x-vscode-flow.gif` 真实落入 `docs/assets/`；Demo_Asset `docs/assets/proofflow-v0_1_x-dogfood-<channel>.gif` 同步落地（≤ 8 MB / ≤ 60 秒 / ≤ 1280×720 + 5 项隐私脱敏）；Dogfood_Report Channel Evidence VSCode block 与 Demo and Example Packet section 同步升级为 `Pass` | `Out_Of_Scope_Finding` | 用户 Option E 决策：VSCode 截图与 Demo_Asset GIF 同根因（无可视 VS Code 窗口可抓取）合并到既有 anchor，避免 backlog 重复；按 design §Error Handling「把降级如实记录而不是粉饰为 Pass」与 Requirement 2.5 / 5.1 / 5.2，本里程碑严禁伪造或占位 evidence | `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood` |
| `F-7` | AgentGuard Public Proof Packet Example 缺席（仅交付 LocalProof 一份） | 在隔离环境跑 `python .\scripts\generate_real_docs_output.py --case-type agentguard --output "<TMP>\packet.md"` 或等价命令生成 AgentGuard packet，复制到 `docs/examples/proof_packet_v0_1_x_agentguard_dogfood.md` | 本里程碑仅交付 `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md` 一份 LocalProof packet（task 7.1 / 7.4 已记录），未补 AgentGuard 路线；与 design §Public Proof Packet Example Design「至少 1 份 AgentGuard packet 优先；理想再加 1 份 LocalProof packet」存在偏离 | `docs/examples/proof_packet_v0_1_x_agentguard_dogfood.md` 落地，含 Latest_Main commit SHA + ISO8601 生成时间 + 生成命令字符串（`<TMP>` 占位符）+ 声明「Generated for milestone v0.1.x dogfood; not a release artifact」+ AgentGuard Statement / Findings / Decisions 链；与 README v0.1.6 dogfood 故事衔接（AgentGuard PR review 路径） | `Out_Of_Scope_Finding` | 用户 Option C 决策：本里程碑只交付 LocalProof 一份；与 Trust_Baseline 不变量无关，不需要独立 spec 触发，挂 PLANS.md anchor 留待下个 dogfood 周期补齐 | `PLANS.md#agentguard-public-packet-deferred-from-v0-1-x-dogfood` |

## CI 状态 / CI Status

> 由 Task 8.1 回填于 `2026-05-19T01:35:56+08:00`，gh CLI 实跑（`gh --version` → 2.92.0；`gh auth status` → `Hyperion-GPU` keyring，Active account=true）取最新 `--branch main --limit 1` HEAD run；不可用时按 design §Risk 降级。Audit trail：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/8_1_ci_status.md`。
> 采集来源：`gh run list --workflow <w> --branch main --limit 1 --json databaseId,headSha,status,conclusion,url,createdAt`。
> 4 个 push-on-main workflow（`backend.yml` / `frontend.yml` / `lint.yml` / `mcp-server.yml`）`--branch main` 直接命中 origin/main HEAD `15b52e6741cd82efd6a1bb1ff6b8649b02b84d8b`（GitHub `repos/.../branches/main` 实查证；本地 working tree HEAD `50524582ecf2433e11fa4a8f82bb51a66319aedd` 含 task 7.x 文档 commits 尚未 push 到 origin/main，因此 Environment 章节的 `commit_sha` 与本节 `head_sha` 形态不同步——这不破坏 design §Property 8 「`conclusion = success`」的契约，origin/main 视图与 GHA runner 实跑视图一致）。
> 2 个非 push-on-main workflow 按 design §Risk 与 task 8.1 prompt §Step 1 降级：`proofflow-pr-review.yml` 由 `pull_request` 触发，`--branch main` 返回空集合，复用 task 4.3 已经记录的 PR #121 Run URL（与「三渠道证据 / Channel Evidence」GHA block 同条 Run，**不**伪造 main HEAD URL）；`publish-mcp.yml` 由 release tag 触发，最近 5 次 release 触发的 run 因 workflow guard 均 `conclusion = skipped`，挑最近一次 `conclusion = success` 的 run（`mcp-v0.1.2`，2026-05-06T16:40:46Z）作为 baseline。
> `gh` CLI 在本任务整体可用，无 GitHub UI 手动复制 Run URL 的降级路径；6 行表中 6/6 `Status = Pass`。

| Workflow | Latest_Main HEAD Run URL | Status | Notes |
| --- | --- | --- | --- |
| `backend.yml` | <https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/26042200104> | Pass | conclusion=success; head_sha=15b52e6741; created_at=2026-05-18T15:10:18Z |
| `frontend.yml` | <https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/26042200116> | Pass | conclusion=success; head_sha=15b52e6741; created_at=2026-05-18T15:10:18Z |
| `lint.yml` | <https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/26042200151> | Pass | conclusion=success; head_sha=15b52e6741; created_at=2026-05-18T15:10:18Z |
| `mcp-server.yml` | <https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/26042200157> | Pass | conclusion=success; head_sha=15b52e6741; created_at=2026-05-18T15:10:18Z |
| `proofflow-pr-review.yml` | <https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/26074265258> | Pass | 与 task 4.3 PR #121 Run URL 交叉一致；workflow 由 `pull_request` 触发，无 main HEAD run；conclusion=success; head_sha=6da1b4c5a0; created_at=2026-05-19T03:25:08Z（task 12.3 closure push commit `6da1b4c` 触发的新 Run；旧首版 Run `26045394262` head_sha=1ec968be34 created_at=2026-05-18T16:09:26Z 保留作为首版 evidence 历史） |
| `publish-mcp.yml` | <https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/25448439375> | Pass | baseline run；本里程碑不触发新发布；workflow 由 release tag 触发，最近 5 次 release 触发的 runs（`v0.1.8` / `v0.1.6.1` / `v0.1.6` / `v0.1.5` / `v0.1.4`）因 workflow guard 均 conclusion=skipped；最近一次 conclusion=success 为 release `mcp-v0.1.2`；conclusion=success; head_sha=a2113e7158; created_at=2026-05-06T16:40:46Z |

## Demo 资产与示例 Proof Packet / Demo and Example Packet

> 由 Task 7.4 回填于 `2026-05-19T01:31:37+08:00`，聚合 transcripts `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/7_1_public_packet.md` / `7_2_demo_asset_gif.md` / `7_3_demo_asset_reference.md`。
> 全部 path 仓库相对；与「三渠道证据 / Channel Evidence」MCP block 中 `proof_packet_path` 字段交叉一致。
> 不允许内嵌 `$PROOFFLOW_DATA_DIR` 内的临时路径；packet 顶部元数据中的本地路径用 `<TMP>` 占位符。

| Field | Value |
| --- | --- |
| `demo_asset_path` | `Deferred (see PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood)` |
| `demo_asset_referenced_from` | `README.md (placeholder note, deferred); README.zh-CN.md (placeholder note, deferred); docs/ledger_quickstart_mcp.md (placeholder note, deferred)` |
| `public_packet_path` | `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md` |
| `public_packet_generator_cmd` | `MCP client Codex -> proofflow_scan(folder_path="<TMP>\localproof-source") -> proofflow_suggest(target_root="<TMP>\localproof-organized") -> proofflow_approve_execute -> proofflow_decide -> proofflow_export_packet(case_id="8fadcdce-245d-4b90-8531-f28916575a6e")` |
| `public_packet_commit_sha` | `50524582ecf2433e11fa4a8f82bb51a66319aedd` |

字段交叉对齐与降级处置说明（audit-friendly 叙述）：

- **Demo_Asset 同根因 deferred**：Demo_Asset GIF 与 VSCode_Channel inline audit / Approve Gate 截图同根因（本里程碑执行环境无可视 VS Code 窗口可抓取）deferred 到下个 dogfood 周期；按用户 Option E 决策合并到既有 anchor `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`，**不**创建新 anchor、**不**在 `docs/assets/` 下落任何 placeholder GIF / PNG / mp4 文件，避免 Property 1（Dogfood evidence completeness）与 Property 9（Dogfood report shape and cross-references）被误判命中。
- **Public_Proof_Packet_Example 选型**：本里程碑仅交付 LocalProof 一份（`docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`）；与 design §Public Proof Packet Example Design 中「优先 AgentGuard」建议存在偏离，按用户 Option C 决策把 AgentGuard 那一份挂 anchor `PLANS.md#agentguard-public-packet-deferred-from-v0-1-x-dogfood`（与 Trust_Baseline 不变量无关，不需要独立 spec 触发）。
- **与「三渠道证据 / Channel Evidence」MCP block 交叉一致**：同一份 LocalProof packet 既作 MCP_Channel 的 `proof_packet_path`（task 4.1 视角，写入「三渠道证据」MCP block），又作 Public_Proof_Packet_Example（task 7.1 视角，写入本节 `public_packet_path`）；两次独立 verify 均通过（task 4.1 + task 7.1 transcript 各一组 6 项 metadata + 脱敏 self-check），构成「双签」级别的证据，无需为两个视角维护两份不同的 packet。
- **与 user-facing Quickstart 三份引用交叉一致**：`demo_asset_referenced_from` 列出的 `README.md` / `README.zh-CN.md` / `docs/ledger_quickstart_mcp.md` 三处 placeholder note 由 task 7.3 写入（用户 Option F：3 份全覆盖而非 Requirement 5.2 下限的 1 份），形态为 blockquote `(deferred)` / `（Deferred）` 字样并指向同一 backlog anchor，**未**插入任何形如 `![…](docs/assets/proofflow-v0_1_x-...gif)` 的伪图片标签；下个 dogfood 周期 Demo_Asset GIF 真实落入 `docs/assets/` 后，由后续 Polish_PR（DEMO_ASSET shape）把 placeholder note 升级为真实 `![…](docs/assets/...)` 图片引用，并同步把 anchor 标记为 closed。

## 不变量保护与遗留 / Invariants and Deferred

> Tag immutability snapshots 表与紧随其后的叙述段由 Task 8.2 回填于 `2026-05-19T01:46:10+08:00`，audit trail：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/8_2_tag_baseline.md`。
> Pre-Merge Gate Checklist 表 + Deferred items 段由 Task 8.3 回填于 `2026-05-19T01:53:50+08:00`，对 6 个 Polish_PR 候选跑 §Pre-Merge Gate Checklist；post-closure audit refresh 后，closure PR #121 与 5 条 quickstart polish PR #122–#126 均已 squash merged 到 `main`，6 行 gate 结果均升级为实采；audit trail：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/8_3_pre_merge_gate.md`。

Existing_Release_Tag 集合（不可新增 / 移动 / 删除 / 重发）：

- `v0.1.0`, `v0.1.0-rc1`, `v0.1.3`, `v0.1.3.1`, `v0.1.4`, `v0.1.5`, `v0.1.6`, `v0.1.6.1`, `v0.1.8`

Tag immutability snapshots:

| Checkpoint | `git ls-remote --tags origin` digest | `gh release list` digest | Diff vs baseline |
| --- | --- | --- | --- |
| milestone start | `sha256=0B4AAEAC314AC6FF9B88B9EED2D3914479BB67F2B457F22DECB684CD4E88329E; 19 lines @ 2026-05-19T01:44:52+08:00` | `sha256=CACAB81B75FFBE57DD0B5BDB05019818E3EB8BADF4BA86B525876D65D754979F; 12 release objects (json 719 bytes) @ 2026-05-19T01:44:52+08:00` | baseline |
| Pre-Merge Gate re-check (PR #121 closure push) | `sha256=0B4AAEAC314AC6FF9B88B9EED2D3914479BB67F2B457F22DECB684CD4E88329E; 19 lines @ 2026-05-19T01:53:50+08:00` | `sha256=CACAB81B75FFBE57DD0B5BDB05019818E3EB8BADF4BA86B525876D65D754979F; 12 release objects (json 719 bytes) @ 2026-05-19T01:53:50+08:00` | **0 lines** vs baseline |
| 每次 Polish_PR 合并后 (closure PR #121 merged + 5 quickstart polish PRs #122–#126 squash merged) | `sha256=0B4AAEAC314AC6FF9B88B9EED2D3914479BB67F2B457F22DECB684CD4E88329E; 19 lines @ 2026-05-19T14:08:05+08:00` | `sha256=CACAB81B75FFBE57DD0B5BDB05019818E3EB8BADF4BA86B525876D65D754979F; 12 release objects (json 719 bytes) @ 2026-05-19T14:08:05+08:00` | **0 lines** vs baseline (post-merge capture-4: 6 PR squash merges 全部完成；6 个 squash commit 上 `git tag --points-at <SHA>` 全部空集) |
| milestone close | `sha256=0B4AAEAC314AC6FF9B88B9EED2D3914479BB67F2B457F22DECB684CD4E88329E; 19 lines @ 2026-05-19T01:46:10+08:00` | `sha256=CACAB81B75FFBE57DD0B5BDB05019818E3EB8BADF4BA86B525876D65D754979F; 12 release objects (json 719 bytes) @ 2026-05-19T01:46:10+08:00` | **0 lines** (`Compare-Object` 行级 diff = `$null`；`-ceq` 字节比较 = `True`；`Get-FileHash -Algorithm SHA256` 两次 capture 完全一致) |

Tag immutability audit 结论与 9 集合 verify（per-tag `publishedAt` 与 `git ls-remote` SHA40 在两次 capture 间不变性）：

- 两次 capture 的 `git ls-remote --tags origin` stdout SHA-256 与 `gh release list --limit 100 --json tagName,publishedAt` stdout SHA-256 在 milestone start 与 milestone close 之间分别 byte-identical（`0B4AAEAC…329E` / `CACAB81B…979F`），diff 为 0 行；由此直接推出 Existing_Release_Tag 9 集合（`v0.1.0` / `v0.1.0-rc1` / `v0.1.3` / `v0.1.3.1` / `v0.1.4` / `v0.1.5` / `v0.1.6` / `v0.1.6.1` / `v0.1.8`）每条 tag 的 `publishedAt` 与对应 `git ls-remote` SHA40 在 milestone 期间不变（9/9 verified；逐项明细见 transcript `8_2_tag_baseline.md` § Existing_Release_Tag 9 集合 verify 表）。
- 「每次 Polish_PR 合并后」一行 post-closure audit refresh 升级：closure PR #121 在 `2026-05-19T04:23:44Z` merge commit `a6874cb0` 进 main，5 个 quickstart polish PR (`polish/quickstart-readme` / `polish/quickstart-readme-zhcn` / `polish/quickstart-ledger-mcp` / `polish/quickstart-codex` / `polish/quickstart-v01-dogfood`) 在 2026-05-19 squash merged 到 `main`（commits `7a49da4` / `277fb0c1` / `3a5195be` / `fdac327a` / `2575785b`）；6 次 PR merge 全部完成后于 `2026-05-19T14:08:05+08:00` 重 capture（capture-4），SHA-256 与 milestone start byte-identical（diff = 0 行），6 个 squash commit 上 `git tag --points-at <SHA>` 全部空集——Tag immutability 不变量贯穿 6 次 PR merge 守住，Existing_Release_Tag 9 集合仍 9/9 verified unchanged。
- `mcp-v0.1.0` / `mcp-v0.1.1` / `mcp-v0.1.2` 是 MCP server release 命名空间，本里程碑同样**不**触动（`publishedAt` 在两次 capture 间不变；与 task 8.1 transcript `publish-mcp.yml` 的 `mcp-v0.1.2` baseline run 引用一致），作为 background invariant 列出但**不**属于 Existing_Release_Tag 9 集合。`refs/tags/v0.2.0`（`d7b7addadaffaa5879f70bd6636f05600d23cbb3`）在 git 层面存在但不在 `gh release list` 12 项 release object 中，本里程碑同样不触动，亦作 background invariant 记录。
- 全程仅使用 read-only 命令（`git ls-remote --tags origin` / `gh release list` / `Get-Date` / `Compare-Object` / `Get-FileHash`），**未**跑任何 `git tag` / `gh release create` / `gh release delete` / `gh release edit` / `git push --tags` 等修改性命令；与 Requirement 8.1 / 8.2 / 8.4 与 design §Pre-Merge Gate Checklist 第 1 条「Tag immutability check」一致。详细命令、stdout 摘录、SHA-256 与逐 tag verify 表见 transcript `.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/8_2_tag_baseline.md`，下游消费者：task 8.3（Pre-Merge Gate）/ task 10.4（Property 4 audit checklist）/ task 12.3（CHANGELOG.md `Unreleased` 复核）。

Pre-Merge Gate Checklist（每个 Polish_PR 合并前 + 合并后即时各跑一次）:

| PR | tag immutability | Policy Gate scope = {move_file, rename_file} | Trust_Baseline regression (rc/rc2/backup_restore) | GHA green | Diff shape ∈ §Schema 6 五种 | merged-tag re-check |
| --- | --- | --- | --- | --- | --- | --- |
| https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/121 (`polish/mcp-channel-dogfood`, final head_sha `754b3a2`, squash merge `a6874cb0554ed69bfec1982acbd51add872d2361`) | Pass (capture-1/-2/-3/-4 SHA-256 byte-identical: ls-remote `0B4AAEAC…329E`; gh release list `CACAB81B…979F`) | Pass (`gh pr diff 121 --name-only` 8 文件全部位于 `docs/` / `*.md` / `CHANGELOG.md` / `PLANS.md`，0 文件触及 `backend/proofflow/services/policy_gate_*.py` 或任何源码路径；Policy Gate scope 保持 `{move_file, rename_file}`) | Pass (task 2.2 transcript: rc_api_smoke / rc2_policy_gate_smoke / backup_restore_api_smoke / ci_agentguard_review.py --help 全 Pass；DOC-only diff 不触敏感文件 omission) | Pass (task 4.3 首版 Run `26045394262` + closure push Run <https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/26074265258> conclusion=success；PR #127 self-check Run `26080468655` 仅留 PR body，不改 GHA_Channel 主证据) | DOC (8 文件全部位于 `docs/` / `*.md` / `CHANGELOG.md` / `PLANS.md`，命中 §Schema 6 第 1 类) | Pass (`git tag --points-at a6874cb0554ed69bfec1982acbd51add872d2361` 空集；Existing_Release_Tag 9 集合 0 改动) |
| `polish/quickstart-readme` (PR #122 squash merged 2026-05-19, F-1) | Pass (post-merge capture-4 SHA-256 byte-identical: ls-remote `0B4AAEAC…329E`; gh release list `CACAB81B…979F`) | Pass (`gh pr diff 122 --name-only` 单文件 `README.md`，0 文件触及 `backend/proofflow/services/policy_gate_*.py` 或任何源码路径) | Pass (DOC-only diff，task 2.2 baseline 持续守护；rc/rc2/backup_restore smoke 在 main HEAD 仍 Pass) | Pass (PR #122 GHA `proofflow-pr-review.yml` conclusion=success) | DOC (单文件 `README.md`，命中 §Schema 6 第 1 类) | Pass (`git tag --points-at 7a49da471b0af7cc2b7445f50e51d5e0146a5473` 空集；Existing_Release_Tag 9 集合 0 改动) |
| `polish/quickstart-readme-zhcn` (PR #123 squash merged 2026-05-19, F-2) | Pass (capture-4 byte-identical) | Pass (`gh pr diff 123 --name-only` 单文件 `README.zh-CN.md`) | Pass (DOC-only diff) | Pass (PR #123 GHA conclusion=success) | DOC (单文件 `README.zh-CN.md`) | Pass (`git tag --points-at 277fb0c1def1e95c12a3d2a1eaaf96fb6deddc6d` 空集；Existing_Release_Tag 9 集合 0 改动) |
| `polish/quickstart-ledger-mcp` (PR #124 squash merged 2026-05-19, F-3) | Pass (capture-4 byte-identical) | Pass (`gh pr diff 124 --name-only` 单文件 `docs/ledger_quickstart_mcp.md`) | Pass (DOC-only diff) | Pass (PR #124 GHA conclusion=success) | DOC (单文件 `docs/ledger_quickstart_mcp.md`) | Pass (`git tag --points-at 3a5195be9458ad5de52e566557e1c3c79b160920` 空集；Existing_Release_Tag 9 集合 0 改动) |
| `polish/quickstart-codex` (PR #125 squash merged 2026-05-19, F-4) | Pass (capture-4 byte-identical) | Pass (`gh pr diff 125 --name-only` 单文件 `docs/codex_workflow.md`) | Pass (DOC-only diff) | Pass (PR #125 GHA conclusion=success) | DOC (单文件 `docs/codex_workflow.md`) | Pass (`git tag --points-at fdac327a384e6fde37d9f5469beaac8b2272d9bd` 空集；Existing_Release_Tag 9 集合 0 改动) |
| `polish/quickstart-v01-dogfood` (PR #126 squash merged 2026-05-19, F-5) | Pass (capture-4 byte-identical) | Pass (`gh pr diff 126 --name-only` 单文件 `docs/V0_1_DOGFOOD.md`) | Pass (DOC-only diff) | Pass (PR #126 GHA conclusion=success) | DOC (单文件 `docs/V0_1_DOGFOOD.md`) | Pass (`git tag --points-at 2575785bcb7b9f70239cbf993f5ad53e062ed7fa` 空集；Existing_Release_Tag 9 集合 0 改动) |

Pre-Merge Gate Checklist 落地说明：本表 6 行覆盖本里程碑的 6 个 Polish_PR 全集（closure PR #121 + 5 个 quickstart polish PR #122–#126）。post-closure audit refresh 后 6 行 6 列均有实采：tag immutability 使用 capture-4 与 milestone start byte-identical 的 SHA-256 结论，Policy Gate scope / Trust_Baseline 均由 DOC-only diff 与 task 2.2 smoke baseline 支撑，GHA green 由各 PR checks / Run 记录支撑，Diff shape 均为 §Schema 6 DOC，merged-tag re-check 对 6 个 squash commit 跑 `git tag --points-at <SHA>` 均为空集。

Deferred items（明确不在本里程碑落地的 Trust_Baseline 范畴）:

- live DB restore 仍 deferred：与 design §Non-Goals 3 / AGENTS.md 「Managed backup / restore invariants」中 `No Restore to live DB in foundation phase` 一致；本里程碑 `scripts/backup_restore_api_smoke.py` 已通过 `_assert_isolated_paths` 守卫验证（task 2.2 transcript），post-run audit `backend\data\proofflow.db` mtime / size 与 baseline 完全一致。
- Policy Gate action 类型集合保持 `{move_file, rename_file}`，本里程碑无新增：与 design §Non-Goals 2 / Requirement 9.1 一致；6 个 Polish_PR 全集 Diff shape 均为 DOC（PR #121 + PR #122–#126），trivially 不触及 Policy Gate 注册路径；行为级回归由 task 2.2 transcript `scripts/rc2_policy_gate_smoke.py` 14/14 Pass 持续守护。
- 其它 Out_Of_Scope_Finding 的 Backlog_Entry 列表：
  - `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`（VSCode_Channel inline audit / Approve Gate 截图 + Demo_Asset GIF 二合一 deferred；本里程碑执行环境暂无可视 VS Code 窗口可抓取，按用户 Option E 决策合并到既有 anchor，不创建新 anchor、不在 `docs/assets/` 下落 placeholder GIF / PNG / mp4）
  - `PLANS.md#agentguard-public-packet-deferred-from-v0-1-x-dogfood`（AgentGuard Public_Proof_Packet_Example deferred；本里程碑仅交付 LocalProof 一份 packet，按用户 Option C 决策把 AgentGuard 那一份挂 anchor，与 Trust_Baseline 不变量无关，不需要独立 spec 触发）

## 验证与复现 / Verify and Reproduce

> 由 Task 10.1 ~ 10.9 回填于 `2026-05-19T02:20:44+08:00`（Property 3 由 Task 6.3 同步落地）；audit trail 见 transcripts 6.3 / 8.1 / 8.2 / 8.3 / 9.1 / 9.2 / 9.3。
> 本节落地 design §Correctness Properties 的 9 条 audit-style invariants，**不**引入 Hypothesis / QuickCheck / fast-check 等 PBT 框架。
> 全部检查命令可在 fresh Windows clone 单一 PowerShell 会话中粘贴执行（含空格路径双引号包裹；`Push-Location "<repo root>"` / `Pop-Location` 配对锁定 cwd）。

### Property 1: Dogfood evidence completeness

- check command:

  ```powershell
  Push-Location "<repo root>"
  python - <<'PY'
  import re, pathlib
  p = pathlib.Path("docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md")
  text = p.read_text(encoding="utf-8")
  pattern = re.compile(r"\b(Pass|Fail|Deferred)\b")
  evidence_re = re.compile(
      r"(Push-Location|cwd[:=]|`[^`]+`|"
      r"docs/(assets|examples|releases)/[^\s)`]+|"
      r"https://github\.com/[^\s)`]+/(pull|actions/runs|issues)/\d+|"
      r"sha256[=:]|exit\s*0|conclusion\s*=\s*success)",
      re.IGNORECASE,
  )
  assumption_re = re.compile(r"assumption", re.IGNORECASE)
  bad = []
  for i, line in enumerate(text.splitlines(), 1):
      if not pattern.search(line):
          continue
      if line.lstrip().startswith(("#", ">")):
          continue
      if evidence_re.search(line) or assumption_re.search(line):
          continue
      bad.append((i, line.strip()[:120]))
  print(f"violations={len(bad)}")
  for i, l in bad[:10]:
      print(f"L{i}: {l}")
  PY
  rg -n "\\bTBD\\b" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  Pop-Location
  ```

- expected:
  - 每条 Pass / Fail / Deferred token 行/块 命中以下任一证据形态：完整命令字符串（含 `cwd` 段或 `Push-Location` 标识）、仓库相对 `docs/(assets|examples|releases)/...` 路径且 `Path.exists()`、`https://github.com/<owner>/<repo>/(pull|actions/runs|issues)/...` URL、`sha256=` digest、`conclusion = success`；例外行须含 `assumption`（大小写不敏感）。
  - 占位 token 全文命中仅限「摘要 / Summary」「范围与非目标 / Scope and Non-Goals」「Definition of Done 13 行勾选项」「推荐下一步 / Recommended Next Step」四段（由 task 12.1 / 12.2 后续回填）；`验证与复现 / Verify and Reproduce` H2 段下 9 个 Property 子节 0 占位。
- result:
  - 「环境 / Environment」（task 2.3 落地）：8 字段 + 来源命令 + 隔离 env 注入字符串均挂证据。
  - 「命令矩阵 / Command Matrix」（task 2.3 落地）：8 行 Pass，每行 `cmd` / `cwd` / `expected` / `actual_status` / `evidence` 5 字段实采，引用 transcripts `2_1_backend_frontend.md` / `2_2_smoke_matrix.md`。
  - 「三渠道证据 / Channel Evidence」（task 4.4 落地）：MCP block 5 tools + `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`（`Path.exists()`）；VSCode block Outcome=Deferred + `vscode-extension` SHA `a94d190ce03332c1c480e8d887be2ebf8df9daba` + Backing PLANS anchor；GHA block 4 字段全 URL 形态命中正则。
  - 「发现与处置 / Findings and Triage」（task 9.1 落地 + post-closure audit refresh）：F-1 ~ F-7 7 行 8 字段全填，F-1 ~ F-5 `link` 列为裸 merged PR URL，F-6 / F-7 `link` 列为 PLANS anchor。
  - 「CI 状态 / CI Status」（task 8.1 落地）：6 行 Run URL 全部 `^https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/[0-9]+$`，全部 Pass 含 `conclusion=success`。
  - 「Demo 资产与示例 Proof Packet」（task 7.4 落地）：`public_packet_path` 仓库相对 + commit SHA `50524582ec…` + Demo_Asset 显式 deferred + PLANS anchor 引用。
  - 「不变量保护与遗留」（task 8.2 / 8.3 落地 + post-closure audit refresh）：4 次 capture SHA-256 byte-identical (`0B4AAEAC…329E` / `CACAB81B…979F`)；Pre-Merge Gate Checklist 表 PR #121 + PR #122–#126 6 行均为 6 项实采，merged-tag re-check 均为空集。
  - **0 处** Pass / Fail / Deferred claim 缺证据；占位 token 在「验证与复现」H2 段下 9 个 Property 子节 0 命中（摘要 / 范围与非目标 / Definition of Done / 推荐下一步 4 段保留占位由 task 12.1 / 12.2 处理，与本 Property 1 audit 范围正交）。



### Property 2: Channel triple-coverage

- check command:

  ```powershell
  Push-Location "<repo root>"
  rg -n "^### Channel: (MCP|VSCode|GHA)" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  rg -n "Outcome: (Pass|Deferred)" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  rg -n "Client: (Claude Code|Codex)" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  rg -n "proofflow_(scan|suggest|approve_execute|decide|review|export_packet)" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  rg -n "proof_packet_path:" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  rg -n "vscode-extension commit SHA at deferral: ``[a-f0-9]{40}``" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  rg -n "(pr_url|run_url|artifact_id|comment_url):" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  rg -n "Backing Polish_PR / Backlog_Entry: " docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  Pop-Location
  ```

- expected:
  - 三个 H3 block (`### Channel: MCP` / `### Channel: VSCode` / `### Channel: GHA`) 必须存在；每个 `Outcome ∈ {Pass, Deferred}`。
  - MCP block: `Client: Codex` + ≥1 个 tool 名（来自 6 工具枚举）+ `proof_packet_path` 仓库相对非空。
  - VSCode block: `Outcome = Deferred` 时 `vscode-extension commit SHA at deferral: <40 hex>` + Backing PLANS anchor link；evidence 字段允许为 `<empty>` 字面量；`Outcome = Pass` 时须有 ≥1 个 `screenshot` / `recording` / `log_excerpt` 形态 evidence 且对应 `docs/assets/` 文件 `Path.exists()`。
  - GHA block: `pr_url` / `run_url` / `artifact_id` / `comment_url` 4 字段全在；其中 `pr_url` / `run_url` / `comment_url` 形态 `^https://github\.com/<owner>/<repo>/...$`。
  - 任一 `Outcome = Deferred` block 必须有 Backing Polish_PR / Backlog_Entry link。
- result:
  - 3 个 H3 block 全在（task 4.4 写入）。
  - **MCP** = Pass + Client `Codex` + 5 tools (`proofflow_scan` / `suggest` / `approve_execute` / `decide` / `export_packet`) + `proof_packet_path: docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`。
  - **VSCode** = Deferred + `vscode-extension commit SHA at deferral: a94d190ce03332c1c480e8d887be2ebf8df9daba` + `Backing Polish_PR / Backlog_Entry: PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`；evidence 字面 `<empty: no screenshot/recording produced this milestone>`（按 design §Error Handling 不伪造 Pass）。
  - **GHA** = Pass + 4 字段全在：`pr_url: https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/121` / `run_url: .../actions/runs/26074265258` / `artifact_id: 7074206493` / `comment_url: .../pull/121#issuecomment-4479556510`（旧 Run `26045394262` / 旧 artifact `7063049346` 对应首版 head_sha `1ec968be34`，由 closure push 新 Run 覆盖；comment update-in-place URL 不变）。
  - 所有 channel-specific required fields 命中契约。


### Property 3: Quickstart reproducibility on a fresh Windows clone

> 由 Task 6.3 回填于 `2026-05-19T01:18:43+08:00`（audit-style，**不**引入 PBT 框架；落地为可在 fresh Windows clone 上单一 PowerShell 会话粘贴执行的 ripgrep 检查清单）。
> 上游修复 transcript：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/6_2_quickstart_polish.md`；本任务 audit transcript：`.kiro/specs/v0.1.x-dogfood-and-channel-polish/transcripts/6_3_quickstart_lint.md`。

- check command:

  ```powershell
  Push-Location "<repo root>"
  rg -n "^cd " README.md README.zh-CN.md docs\ledger_quickstart_mcp.md docs\codex_workflow.md docs\V0_1_DOGFOOD.md
  rg -n "(:8000|:5000|--port 8000|--port 5000)" README.md README.zh-CN.md docs\ledger_quickstart_mcp.md docs\codex_workflow.md docs\V0_1_DOGFOOD.md
  rg -n "D:\\ProofFlow v0\.1" README.md README.zh-CN.md docs\ledger_quickstart_mcp.md docs\codex_workflow.md docs\V0_1_DOGFOOD.md | rg -v '"D:\\ProofFlow v0\.1"'
  Pop-Location
  ```

- expected:
  - `^cd ` 行首裸 `cd <path>` 命中数 = 0（未被 `Push-Location` 或绝对路径替代视为违规）
  - 非 `8787` 的后端端口形态（`:8000` / `:5000` / `--port 8000` / `--port 5000`）命中数 = 0
  - 含空格 Windows 路径（`D:\ProofFlow v0.1`）未被 `"..."` / JSON `"..."` 字符串字面量包裹的命中数 = 0
- result:
  - `^cd `：**0 命中**（grep_search Q1 跑过；5 份文档全部干净，与 task 6.2 §Self-check 表 6 项 lint 一致）
  - `(:8000|:5000|--port 8000|--port 5000)`：**0 命中**（grep_search Q2 跑过；task 6.2 修复后已全部固定为 `--port 8787`）
  - 含空格路径未被双引号包裹：**0 命中**（grep_search Q3 跑过；5 处 `D:\ProofFlow v0.1` / `D:\\ProofFlow v0.1` 形态左侧均有 `"` 包裹——`docs/V0_1_DOGFOOD.md` L33、`docs/ledger_quickstart_mcp.md` L11 / L40 / L143 / L235；其余 `ProofFlow v0.1` / `ProofFlow v0.1.0` / `ProofFlow v0.1.6` 是产品名/版本号，非命令上下文路径，不在 lint 范围）
- Quickstart_Doc_Set 验证子表：

| Document | Validated commit SHA | `actual_status` | Notes |
| --- | --- | --- | --- |
| `README.md` | `7a49da471b0af7cc2b7445f50e51d5e0146a5473` | Pass | task 6.1 stale 5 → task 6.2 working tree 修复后 0；2026-05-19 由 PR #122 squash merged 进 main，Validated commit SHA 升级为 polish merged commit SHA |
| `README.zh-CN.md` | `277fb0c1def1e95c12a3d2a1eaaf96fb6deddc6d` | Pass | task 6.1 stale 6 → task 6.2 working tree 修复后 0；含 entry `app.main:app` → `proofflow.main:app` + 端口固定 `8787` + MCP 入口收敛到 `pip install proofflow-mcp`；2026-05-19 由 PR #123 squash merged 进 main，Validated commit SHA 升级为 polish merged commit SHA |
| `docs/ledger_quickstart_mcp.md` | `3a5195be9458ad5de52e566557e1c3c79b160920` | Pass | task 6.1 stale 2 → task 6.2 working tree 修复后 0；2026-05-19 由 PR #124 squash merged 进 main，Validated commit SHA 升级为 polish merged commit SHA |
| `docs/codex_workflow.md` | `fdac327a384e6fde37d9f5469beaac8b2272d9bd` | Pass | task 6.1 stale 3 → task 6.2 working tree 修复后 0；2026-05-19 由 PR #125 squash merged 进 main，Validated commit SHA 升级为 polish merged commit SHA |
| `docs/V0_1_DOGFOOD.md` | `2575785bcb7b9f70239cbf993f5ad53e062ed7fa` | Pass | task 6.1 stale 4 → task 6.2 working tree 修复后 0；2026-05-19 由 PR #126 squash merged 进 main，Validated commit SHA 升级为 polish merged commit SHA |

### Property 4: Tag immutability

- check command:

  ```powershell
  Push-Location "<repo root>"
  $tmp = "$env:TEMP\proofflow-tag-immutability-$(Get-Date -Format yyyyMMdd-HHmmss)"
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  git ls-remote --tags origin | Out-File -FilePath "$tmp\ls-remote.txt" -Encoding utf8
  gh release list --limit 100 --json tagName,publishedAt | Out-File -FilePath "$tmp\releases.json" -Encoding utf8
  (Get-FileHash "$tmp\ls-remote.txt" -Algorithm SHA256).Hash
  (Get-FileHash "$tmp\releases.json" -Algorithm SHA256).Hash
  # baseline 比较：与 task 8.2 capture-1 / -2、task 8.3 capture-3 已记录的 SHA-256 比对
  # 期望与 0B4AAEAC...329E（ls-remote）和 CACAB81B...979F（releases.json）byte-identical
  Pop-Location
  ```

- expected:
  - milestone 起点（task 8.2 capture-1）/ 终点（task 8.2 capture-2）/ Pre-Merge Gate re-check（task 8.3 capture-3）三次 capture SHA-256 byte-identical。
  - Existing_Release_Tag 9 集合 `{v0.1.0, v0.1.0-rc1, v0.1.3, v0.1.3.1, v0.1.4, v0.1.5, v0.1.6, v0.1.6.1, v0.1.8}` 的 `publishedAt` 与 `git ls-remote` SHA40 在所有 capture 间不变。
  - 任意 Polish_PR 合并 commit 上 `git tag --points-at <SHA>` 为空集合；post-closure audit refresh 覆盖 closure PR #121 与 quickstart PR #122–#126 的 6 个 squash commit。
- result:
  - 3 次 capture byte-identical：`git ls-remote --tags origin` SHA-256 = `0B4AAEAC314AC6FF9B88B9EED2D3914479BB67F2B457F22DECB684CD4E88329E`（task 8.2 capture-1 `2026-05-19T01:44:52+08:00` / capture-2 `2026-05-19T01:46:10+08:00` / task 8.3 capture-3 `2026-05-19T01:53:50+08:00`）；`gh release list` SHA-256 = `CACAB81B75FFBE57DD0B5BDB05019818E3EB8BADF4BA86B525876D65D754979F`（同三次 capture）。
  - 9 集合 9/9 verified（详见「不变量保护与遗留」段 per-tag `publishedAt` 表）。
  - post-closure audit refresh 后，closure PR #121 与 5 个 quickstart polish PR #122–#126 均已 squash merged 到 `main`；capture-4 (`2026-05-19T14:08:05+08:00`) 与 milestone start SHA-256 byte-identical，且 6 个 squash commit (`a6874cb0554ed69bfec1982acbd51add872d2361` / `7a49da471b0af7cc2b7445f50e51d5e0146a5473` / `277fb0c1def1e95c12a3d2a1eaaf96fb6deddc6d` / `3a5195be9458ad5de52e566557e1c3c79b160920` / `fdac327a384e6fde37d9f5469beaac8b2272d9bd` / `2575785bcb7b9f70239cbf993f5ad53e062ed7fa`) 上 `git tag --points-at <SHA>` 均为空集；Tag immutability 继续满足。


### Property 5: Trust baseline preservation

- check command:

  ```powershell
  Push-Location "<repo root>"
  rg -n "^\s*(register|ALLOWED_ACTIONS|action_type)\s*[:=]" backend\proofflow\services\policy_gate_*.py
  rg -n "(move_file|rename_file)" backend\proofflow\services\policy_gate_action_classifier.py
  Push-Location backend
  python -m pytest -q -k "undo or omission or hash_guard or sensitive"
  Pop-Location
  python .\scripts\rc_api_smoke.py
  python .\scripts\rc2_policy_gate_smoke.py
  python .\scripts\backup_restore_api_smoke.py
  gh pr diff 121 --name-only
  gh pr diff 121 | rg "(restore_to_live|apply_to_live_db|cloud_sync|telemetry|webhook|multi_user)"
  Pop-Location
  ```

- expected:
  - Policy Gate action 注册位置仅出现 `move_file` 与 `rename_file`（无 `delete_file` / `apply_to_live_db` 等扩展）。
  - 3 个 smoke 脚本 `rc_api_smoke.py` / `rc2_policy_gate_smoke.py` / `backup_restore_api_smoke.py` 全部 `exit 0`。
  - PR diff 不含新增 `restore_to_live` / `apply_to_live_db` 类符号；`cloud_sync` / `telemetry` / `webhook` / `multi_user` 关键词命中数 = 0。
  - backend pytest 包含 hash-guarded undo 与 sensitive-file omission 用例 Pass。
- result:
  - **task 2.1** backend pytest（含 hash-guarded undo + sensitive-file omission 用例）：313 passed / 3 skipped in 46.22s（详见 transcript `2_1_backend_frontend.md` §1）。
  - **task 2.2** 3 smoke 全 Pass：`rc_api_smoke.py` `LASTEXITCODE=0; ProofFlow v0.1.0 API smoke passed.`；`rc2_policy_gate_smoke.py` `LASTEXITCODE=0; RC2 Policy Gate Smoke: 14 passed, 0 failed; pending_decision fail-closed`；`backup_restore_api_smoke.py` `LASTEXITCODE=0; Restored DB path "<TMP>\...\proofflow-restored.db" ≠ live DB`（`_assert_isolated_paths` 守卫验证；post-run `backend\data\proofflow.db` mtime / size 与 baseline 完全一致）。
  - **task 8.3** PR #121 diff `gh pr diff 121 --name-only` → 单文件 `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md`，**完全不在** `backend/proofflow/services/policy_gate_*.py` 或任何 backend / frontend / mcp-server / `.github/` 路径下；net-new feature 关键词黑名单（`cloud_sync` / `telemetry` / `webhook` / `multi_user` / `restore_to_live` / `apply_to_live_db`）0 命中。
  - Policy Gate scope 维持 `{move_file, rename_file}`（task 9.2 §OPPORTUNISTIC_FIX 边界确认 7 项 trivially 全部 Pass）；本里程碑 Trust_Baseline 6 条不变量（action safety scope / hash-guarded undo / sensitive-file omission / Policy Gate fail-closed / live DB restore deferred / Existing_Release_Tag immutability）保持。


### Property 6: Polish-only diff shape

- check command:

  ```powershell
  Push-Location "<repo root>"
  # 1. 列出 post-closure 已合并到 main 的 In_Scope_Fix Polish_PR（PR #122-#126）
  gh pr list --state merged --base main --search "merged:>=2026-05-18" --json number,title,headRefName,mergedAt,url
  # 2. 对 GHA evidence PR #121 与 quickstart In_Scope_Fix PR #122-#126 跑 diff shape 分类
  foreach ($pr in 121,122,123,124,125,126) { gh pr diff $pr --name-only }
  # 3. PR diff 黑名单关键词（任何被合并的 Polish_PR）
  foreach ($pr in 121,122,123,124,125,126) { gh pr diff $pr | rg "(cloud_sync|telemetry|webhook|multi_user|restore_to_live|apply_to_live_db)" }
  # 4. Findings 表 In_Scope_Fix 行 PR URL 与 merged Polish_PR 集合对齐
  rg -n "In_Scope_Fix" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  Pop-Location
  ```

- expected:
  - 每个 merged Polish_PR diff 文件清单可分类为 §Schema 6 五种 shape 之一（DOC / TEST / CI / DEMO_ASSET / OPPORTUNISTIC_FIX）；无法分类即 fail。
  - OPPORTUNISTIC_FIX shape PR `gh pr view <pr> --json body | rg "Fixes finding F-[0-9]+|Resolves #[0-9]+"` 命中。
  - net-new feature 关键词黑名单（`cloud_sync` / `telemetry` / `webhook` / `multi_user` / `restore_to_live` / `apply_to_live_db`）任一命中即拒绝合并。
  - Findings 表 `In_Scope_Fix` 行 PR URL 与本里程碑被合并的 Polish_PR 集合一一对应。
- result:
  - **本里程碑 post-closure In_Scope_Fix Polish_PR merged 集合 = {#122, #123, #124, #125, #126}**（task 9.2 audit refresh 确认）：5 个 polish/quickstart-* PR 均已 squash merged 到 `main`，分别支撑 F-1 ~ F-5。
  - **PR #121** diff = DOC shape（8 文件全部位于 `docs/` / `*.md` / `CHANGELOG.md` / `PLANS.md`）；PR description 显式声明其用途为 GHA channel evidence 触发载体、非 In_Scope_Fix（task 4.4 GHA block Notes 已记录）。OPPORTUNISTIC_FIX 不适用（DOC shape 不要求 `Fixes finding F-<n>` 锚点）。
  - **PR #122–#126** diff 均为 DOC shape：#122 单文件 `README.md`，#123 单文件 `README.zh-CN.md`，#124 单文件 `docs/ledger_quickstart_mcp.md`，#125 单文件 `docs/codex_workflow.md`，#126 单文件 `docs/V0_1_DOGFOOD.md`；均通过独立 `polish/quickstart-*` 分支合并。
  - **黑名单关键词**：PR #121–#126 diff 0 命中 `cloud_sync` / `telemetry` / `webhook` / `multi_user` / `restore_to_live` / `apply_to_live_db`；本里程碑 0 OPPORTUNISTIC_FIX shape PR。
  - **Findings 表 `In_Scope_Fix` 行**：5 行（F-1 ~ F-5），`link` 列为 PR #122–#126 裸 merged PR URL；`Out_Of_Scope_Finding` 行为 2 行（F-6 / F-7），继续挂 PLANS deferred anchor。
  - Findings 表 In_Scope_Fix 集合（{#122, #123, #124, #125, #126}）与本里程碑 post-closure 被合并的 In_Scope_Fix Polish_PR 集合一一对应；PR #121 作为 GHA channel evidence DOC PR 保持在 In_Scope_Fix 集合之外。


### Property 7: Backlog honesty

- check command:

  ```powershell
  Push-Location "<repo root>"
  python - <<'PY'
  import re, pathlib
  p = pathlib.Path("docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md")
  text = p.read_text(encoding="utf-8")
  # 抓 Findings 表 7 行（id 列形态 `F-<n>`）
  rows = re.findall(r"^\| `(F-\d+)` \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$",
                    text, re.MULTILINE)
  print(f"rows={len(rows)}")
  in_scope_pr_re = re.compile(r"^https://github\.com/[^/]+/[^/]+/pull/\d+$")
  out_scope_re = re.compile(r"^https://github\.com/[^/]+/[^/]+/issues/\d+$|^PLANS\.md#.+$|^`PLANS\.md#.+`$")
  for fid, title, repro, observed, expected, classification, triage, link in rows:
      link_clean = link.strip().strip("`")
      assert all([title, repro, observed, expected, classification, triage, link_clean]), f"{fid} 8字段非空校验失败"
      if "In_Scope_Fix" in classification:
          assert in_scope_pr_re.match(link_clean), f"{fid} link 不是合规 PR URL: {link_clean}"
      else:
          assert out_scope_re.match(link_clean), f"{fid} link 不是合规 issue/anchor: {link_clean}"
      print(f"{fid} OK class={classification.strip()} link={link_clean[:80]}")
  PY
  rg -n "^### (vscode-channel-screenshots-deferred-from-v0-1-x-dogfood|agentguard-public-packet-deferred-from-v0-1-x-dogfood|quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood)" PLANS.md
  Pop-Location
  ```

- expected:
  - Findings 表 7 行（F-1 ~ F-7），每行 8 字段（`id` / `title` / `repro` / `observed` / `expected` / `classification` / `triage_reason` / `link`）非空。
  - `In_Scope_Fix` 行 `link` 匹配 `^https://github\.com/<owner>/<repo>/pull/[0-9]+$` 且 PR 已 merged。
  - `Out_Of_Scope_Finding` 行 `link` 匹配 `^https://github\.com/<owner>/<repo>/issues/[0-9]+$` 或 `^PLANS\.md#.+$`；GitHub issue 可访问且未关闭为 `not planned`，`PLANS.md` 锚点 heading 在文件中真实存在。
- result:
  - **task 9.1** 写入 Findings 表 7 行（F-1 ~ F-7，8 字段全填）。
  - **task 9.2 post-closure refresh** 更新后 7/7 link 字段命中：F-1 ~ F-5 → 裸 merged PR URL (`https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/122` ~ `/pull/126`)；F-6 → `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`；F-7 → `PLANS.md#agentguard-public-packet-deferred-from-v0-1-x-dogfood`。
  - **task 9.3 §Step 2** 3 个 PLANS anchor heading 在 PLANS.md 真实存在：vscode anchor 5/5 字段、quickstart anchor 5/5 字段、agentguard anchor 4/5 字段（`D-9.3-1` low 偏差：缺独立 `- Reference:` 段；不阻塞 Property 7，audit trail 经 anchor `Source:` 字段与 task 7.1 / 7.4 transcripts 交叉引用未断裂）。
  - 7 行 classification 列：5 `In_Scope_Fix`（F-1 ~ F-5）/ 2 `Out_Of_Scope_Finding`（F-6 / F-7）；F-1 ~ F-5 已由 PR #122–#126 真实 merged PR URL 支撑，F-6 / F-7 仍有 PLANS anchor，按 Requirement 7.2 / 7.5 无静默丢弃。


### Property 8: CI green maintenance across the milestone

- check command:

  ```powershell
  Push-Location "<repo root>"
  foreach ($w in @("backend.yml", "frontend.yml", "lint.yml", "mcp-server.yml", "proofflow-pr-review.yml", "publish-mcp.yml")) {
      Write-Host "=== $w ==="
      gh run list --workflow $w --branch main --limit 1 `
        --json databaseId,headSha,status,conclusion,url,createdAt
  }
  # 降级路径：proofflow-pr-review.yml（pull_request 触发，main 直查空集 → 复用 task 4.3 PR #121 Run URL）
  # 降级路径：publish-mcp.yml（release tag 触发，最近 5 次 conclusion=skipped → 取最近一次 conclusion=success 的 baseline run）
  rg -n "actions/runs/[0-9]+" docs\releases\V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md
  Pop-Location
  ```

- expected:
  - 在 milestone 起点 / 每次 Polish_PR merge 后 / 关闭前三组时间点，对 6 个 workflow 跑 `gh run list`，断言 `conclusion = success`。
  - Schema 5 表格在终点 6 行齐全；Run URL 命中正则 `^https://github\.com/<owner>/<repo>/actions/runs/[0-9]+$`。
- result:
  - **task 8.1** 已在 Latest_Main HEAD `15b52e6741cd82efd6a1bb1ff6b8649b02b84d8b`（origin/main）采集 6 个 workflow Run URL，写入 Schema 5 表 6 行：
    - `backend.yml` → runs/26042200104 (conclusion=success)
    - `frontend.yml` → runs/26042200116 (conclusion=success)
    - `lint.yml` → runs/26042200151 (conclusion=success)
    - `mcp-server.yml` → runs/26042200157 (conclusion=success)
    - `proofflow-pr-review.yml` → runs/26074265258 (closure push commit `6da1b4c` 触发的新 Run；conclusion=success；与 task 4.3 PR #121 GHA channel block 交叉一致；首版 Run `26045394262` head_sha=1ec968be34 保留为首版 evidence 历史)
    - `publish-mcp.yml` → runs/25448439375 (降级路径：取最近一次 conclusion=success 的 baseline run `mcp-v0.1.2`，本里程碑不触发新发布)
  - 6/6 Run URL 全部命中正则 `^https://github\.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/[0-9]+$`；6/6 `Status = Pass` + `conclusion = success`。
  - post-closure audit refresh 后，PR #121 与 quickstart PR #122–#126 均已 merge；GHA_Channel 主证据仍绑定 PR #121 的 Run `26074265258`，PR #127 自身 GHA Run `26080468655` / artifact `7076402293` / comment `#issuecomment-4485025048` 仅作为 PR body self-evidence，不写入 GHA_Channel 主字段以避免自指循环。


### Property 9: Dogfood report shape and cross-references

- check command:

  ```powershell
  Push-Location "<repo root>"
  python - <<'PY'
  import pathlib
  p = pathlib.Path("docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md")
  print("Path.exists =", p.exists())
  expected = [
      "## 摘要 / Summary",
      "## 范围与非目标 / Scope and Non-Goals",
      "## 环境 / Environment",
      "## 命令矩阵 / Command Matrix",
      "## 三渠道证据 / Channel Evidence",
      "## 发现与处置 / Findings and Triage",
      "## CI 状态 / CI Status",
      "## Demo 资产与示例 Proof Packet / Demo and Example Packet",
      "## 不变量保护与遗留 / Invariants and Deferred",
      "## 验证与复现 / Verify and Reproduce",
      "## 推荐下一步 / Recommended Next Step",
  ]
  text = p.read_text(encoding="utf-8")
  positions = [text.find(h) for h in expected]
  print("11 H2 顺序:", "Pass" if all(p > 0 for p in positions) and positions == sorted(positions) else "Fail")
  PY
  rg -n "docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md" CHANGELOG.md
  rg -B1 "docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md" CHANGELOG.md | rg "## Unreleased|^docs/releases"
  python -c "import pathlib; print('public_packet=', pathlib.Path('docs/examples/proof_packet_v0_1_x_localproof_dogfood.md').exists())"
  python -c "import pathlib; print('demo_asset=', list(pathlib.Path('docs/assets').glob('proofflow-v0_1_x-dogfood-*')))"
  Pop-Location
  ```

- expected:
  - `Path.exists("docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md")` = True。
  - `grep -F "docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md" CHANGELOG.md` 命中且位于 `## Unreleased` 段下。
  - Markdown heading 序列与 R11.2 列表顺序一致（11 个 H2 段顺序）。
  - 五段必填子节（changed / why / verify / not done / next step）在固定中英文标题下出现（由 task 12.1 写入摘要章节后回填验证）。
  - grep 引用 `docs/examples/<public-packet>.md` 文件 `Path.exists()`（本里程碑接受 `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md` 一份）；Demo_Asset GIF deferred 用 placeholder note 而非伪图片（task 7.3 / 7.4 已落地）。
- result:
  - 文件存在（task 1.1 创建 + 后续任务回填）。
  - CHANGELOG link 命中（task 1.2 写入 `## Unreleased` 段下）。
  - 11 H2 顺序与 R11.2 列表一致（骨架由 task 1.1 按顺序生成；后续任务仅在指定子段内回填，未调整 H2 顺序）。
  - Public packet `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md` 存在（task 4.1 / 7.1 落地，与 MCP block `proof_packet_path` + Demo and Example Packet `public_packet_path` 交叉一致）。
  - Demo_Asset GIF 同根因 deferred 到 PLANS anchor `vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`（task 7.2）；3 处 user-facing Quickstart 用 placeholder note 而非伪图片引用（task 7.3 落地，README.md / README.zh-CN.md / docs/ledger_quickstart_mcp.md 各 1 处 `(deferred)` / `（Deferred）` 字样指向同一 backlog anchor，无 `![…](docs/assets/...gif)` 伪标签）。
  - **本任务 10.9 范围限定**：仅核对结构性约束（文件存在 / 11 H2 顺序 / CHANGELOG link / Public packet 存在 + Demo_Asset placeholder 形态）。「五段必填子节（changed / why / verify / not done / next step）在固定中英文标题下出现」由 task 12.1 在「摘要 / Summary」与「推荐下一步 / Recommended Next Step」H2 段写入；task 12.2 DoD 13 条勾选清单的同文档锚点会回链到本 Property 子节作为 audit 锚点，本任务 10.9 此时不阻塞 task 12.1 / 12.2 的后续回填。


### Definition of Done — 13 条勾选清单

> 由 Task 12.2 回填于 `2026-05-19T02:40:59+08:00`。13 条勾选挂同文档内可点击锚点指向证据章节；本里程碑 13/13 标记 `[x]`，每条对应 evidence 章节已由 task 1.1 ~ 12.1 实采落地，Deferred 部分（VSCode_Channel inline audit / Approve Gate 截图 + Demo_Asset GIF + AgentGuard public packet）按 Requirement 7.5 backlog honesty 挂 PLANS anchor（Findings 表 7 行 link 列双向交叉一致），不视为 milestone not done。

- [x] DoD-1 (R1): 在 fresh Windows clone 单一 PowerShell 会话采集 8 字段环境记录 + 8 行 Command Matrix（覆盖 R1.2 ~ R1.5 全部命令；`backend python -m pytest` / `frontend npm ci` / `npm test` / `npm run build` / `rc_api_smoke.py` / `rc2_policy_gate_smoke.py` / `backup_restore_api_smoke.py` / `ci_agentguard_review.py --help` 8/8 `actual_status = Pass`）。详见 [#环境 / Environment](#环境--environment) 与 [#命令矩阵 / Command Matrix](#命令矩阵--command-matrix)。
- [x] DoD-2 (R2): 三条 Distribution_Channel 各自 evidence-backed entry——MCP_Channel `Outcome = Pass`（Codex client + 5/6 tools + `proof_packet_path` 仓库相对）、GHA_Channel `Outcome = Pass`（PR #121 触发 `proofflow-pr-review.yml`，4 字段 `pr_url` / `run_url` / `artifact_id` / `comment_url` 全在）、VSCode_Channel `Outcome = Deferred` 挂 `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`。详见 [#三渠道证据 / Channel Evidence](#三渠道证据--channel-evidence)。
- [x] DoD-3 (R3): Dogfood_Report 中所有 Pass / Fail / Deferred claim 均挂证据（命令 / 日志摘录 / `docs/(assets|examples|releases)/...` 仓库相对路径 / GitHub URL / `sha256=` digest / `conclusion = success`），0 处缺证据；audit checklist 命令可在 fresh Windows clone 单一 PowerShell 会话中粘贴执行。详见 [#验证与复现 / Verify and Reproduce](#验证与复现--verify-and-reproduce) 之 [Property 1: Dogfood evidence completeness](#property-1-dogfood-evidence-completeness)。
- [x] DoD-4 (R4): 5 份 Quickstart_Doc_Set（`README.md` / `README.zh-CN.md` / `docs/ledger_quickstart_mcp.md` / `docs/codex_workflow.md` / `docs/V0_1_DOGFOOD.md`）在单一 PowerShell 会话验证完毕，各附 commit SHA + `actual_status`；ripgrep 三段 lint（`^cd ` / 非 `8787` 端口 / 含空格路径未引号）命中数 0/0/0；stale 步骤已由 PR #122–#126 拆分为 5 个 DOC-only quickstart polish PR 并 squash merged。详见 [Property 3: Quickstart reproducibility on a fresh Windows clone](#property-3-quickstart-reproducibility-on-a-fresh-windows-clone) 子表。
- [x] DoD-5 (R5): `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md` 落地（针对 Latest_Main commit `50524582…aedd` 由 Codex MCP 5-tool 真实生成 + 顶部 6 项必备元数据 + `<TMP>` 占位符脱敏）；Demo_Asset GIF 同根因 deferred 挂 `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`，3 处 user-facing Quickstart（`README.md` / `README.zh-CN.md` / `docs/ledger_quickstart_mcp.md`）以 placeholder note 引用而非伪图片标签。详见 [#Demo 资产与示例 Proof Packet / Demo and Example Packet](#demo-资产与示例-proof-packet--demo-and-example-packet)。
- [x] DoD-6 (R6): 6 个 workflow 在 Latest_Main HEAD `15b52e6741…` 全部 `conclusion = success`，6/6 Run URL 命中正则 `^https://github\.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/[0-9]+$`；`proofflow-pr-review.yml` 复用 PR #121 Run（与 GHA channel block 交叉一致），`publish-mcp.yml` 取 `mcp-v0.1.2` baseline。详见 [#CI 状态 / CI Status](#ci-状态--ci-status) 与 [Property 8: CI green maintenance across the milestone](#property-8-ci-green-maintenance-across-the-milestone)。
- [x] DoD-7 (R7): Findings 表 7 行（F-1 ~ F-7）8 字段全填，7/7 link 列命中合规——5 行 In_Scope_Fix → PR #122–#126 裸 merged PR URL，2 行 Out_Of_Scope_Finding → `PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood` / `PLANS.md#agentguard-public-packet-deferred-from-v0-1-x-dogfood`，0 静默丢弃。详见 [#发现与处置 / Findings and Triage](#发现与处置--findings-and-triage) 与 [Property 7: Backlog honesty](#property-7-backlog-honesty)。
- [x] DoD-8 (R8): 本里程碑无新 release tag；milestone start / close / Pre-Merge Gate re-check / post-merge capture-4 四次 capture `git ls-remote --tags origin` SHA-256 = `0B4AAEAC314AC6FF9B88B9EED2D3914479BB67F2B457F22DECB684CD4E88329E` 与 `gh release list` SHA-256 = `CACAB81B75FFBE57DD0B5BDB05019818E3EB8BADF4BA86B525876D65D754979F` byte-identical；Existing_Release_Tag 9 集合（`v0.1.0` / `v0.1.0-rc1` / `v0.1.3` / `v0.1.3.1` / `v0.1.4` / `v0.1.5` / `v0.1.6` / `v0.1.6.1` / `v0.1.8`）9/9 verified。详见 [#不变量保护与遗留 / Invariants and Deferred](#不变量保护与遗留--invariants-and-deferred) 与 [Property 4: Tag immutability](#property-4-tag-immutability)。
- [x] DoD-9 (R9): Pre-Merge Gate Checklist 6 项对 PR #121 与 PR #122–#126 6 行全部实采；每行 Diff shape = DOC，merged-tag re-check 空集；Trust_Baseline 6 条不变量（action safety scope / hash-guarded undo / sensitive-file omission / Policy Gate fail-closed / live DB restore deferred / Existing_Release_Tag immutability）保持。详见 [#不变量保护与遗留 / Invariants and Deferred](#不变量保护与遗留--invariants-and-deferred) 与 [Property 5: Trust baseline preservation](#property-5-trust-baseline-preservation)。
- [x] DoD-10 (R10): 8 行 Command Matrix 含空格 Windows 路径双引号包裹；MCP block 经 `proofflow_approve_execute` + `proofflow_decide` 闭环验证 destructive action 三段式（dry-run / approval / undo），且 `move_file` undo 由 `from_sha256` guard 保护；本里程碑无 owner 数据 / 本地数据库 / Proof Packet / artifact 删除事件。详见 [#命令矩阵 / Command Matrix](#命令矩阵--command-matrix) 与 [#三渠道证据 / Channel Evidence](#三渠道证据--channel-evidence) 与 [Property 5: Trust baseline preservation](#property-5-trust-baseline-preservation)。
- [x] DoD-11 (R11): 11 H2 段（摘要 / Summary → 推荐下一步 / Recommended Next Step）顺序与 R11.2 列表一致；摘要段含五段 delivery 子节（what changed / why / how to verify or reproduce / what was intentionally not done / recommended next step）；简体中文叙述 + 英文 EARS 关键词与 shell 命令字符串；`CHANGELOG.md` `## Unreleased` 段已链接 `docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md`。详见 [#摘要 / Summary](#摘要--summary) 与 [Property 9: Dogfood report shape and cross-references](#property-9-dogfood-report-shape-and-cross-references)。
- [x] DoD-12 (R12): post-closure merged In_Scope_Fix Polish_PR 集合 = {#122, #123, #124, #125, #126}，均为 DOC shape；PR #121 为 GHA channel evidence DOC PR、非 In_Scope_Fix。Findings 表 `In_Scope_Fix` 行 = 5、`Out_Of_Scope_Finding` 行 = 2；0 OPPORTUNISTIC_FIX shape PR、0 net-new feature 关键词（`cloud_sync` / `telemetry` / `webhook` / `multi_user` / `restore_to_live` / `apply_to_live_db`）命中，polish-only 形态成立。详见 [Property 6: Polish-only diff shape](#property-6-polish-only-diff-shape) 与 [#发现与处置 / Findings and Triage](#发现与处置--findings-and-triage)。
- [x] DoD-13 (R13): 9 条 audit-style invariants 全部以 `check command` / `expected` / `result` 三字段落地为可粘贴执行清单（**不**引入 Hypothesis / QuickCheck / fast-check 等 PBT 框架，与 design §Testing Strategy Non-Goal 一致）。详见 [#验证与复现 / Verify and Reproduce](#验证与复现--verify-and-reproduce)：[Property 1](#property-1-dogfood-evidence-completeness) / [Property 2](#property-2-channel-triple-coverage) / [Property 3](#property-3-quickstart-reproducibility-on-a-fresh-windows-clone) / [Property 4](#property-4-tag-immutability) / [Property 5](#property-5-trust-baseline-preservation) / [Property 6](#property-6-polish-only-diff-shape) / [Property 7](#property-7-backlog-honesty) / [Property 8](#property-8-ci-green-maintenance-across-the-milestone) / [Property 9](#property-9-dogfood-report-shape-and-cross-references)。

## 推荐下一步 / Recommended Next Step

> 由 Task 12.1 回填于 `2026-05-19T02:34:03+08:00`，与 design DoD-13（§Definition of Done）/ 不变量保护一致。

- quickstart polish follow-up 已完成：PR #122–#126 已将 5 份 Quickstart_Doc_Set 修复拆分为独立 DOC-only PR 并 squash merged；Dogfood_Report Findings 表 F-1 ~ F-5 已升级为 `In_Scope_Fix`，`PLANS.md#quickstart-polish-prs-pending-packaging-from-v0-1-x-dogfood` 已标记 CLOSED。
- 下个 dogfood 周期补 VSCode_Channel inline audit + Approve Gate 截图与 Demo_Asset GIF（复用 PLANS anchor `vscode-channel-screenshots-deferred-from-v0-1-x-dogfood` 的 Acceptance criteria：3 路径 `docs/assets/proofflow-v0_1_x-vscode-inline-audit.png` / `proofflow-v0_1_x-vscode-approve-gate.png` / `proofflow-v0_1_x-vscode-flow.gif` 真实落入 `docs/assets/` + 5 项隐私脱敏 + ≤ 8 MB / ≤ 60 秒 / ≤ 1280×720），并在 Channel Evidence VSCode block 把 Outcome 由 `Deferred` 升级为 `Pass`、3 处 user-facing Quickstart placeholder note 升级为真实 `![…](docs/assets/...)` 图片引用。
- 下个 dogfood 周期补 AgentGuard Public_Proof_Packet_Example（复用 PLANS anchor `agentguard-public-packet-deferred-from-v0-1-x-dogfood` §Acceptance criteria：`docs/examples/proof_packet_v0_1_x_agentguard_dogfood.md` 落地 + Latest_Main commit SHA + ISO8601 + generator command 用 `<TMP>` 占位符 + 「not a release artifact」声明 + AgentGuard Statement / Findings / Decisions 链 + 与 README v0.1.6 dogfood 故事衔接），并同步升级 Demo and Example Packet section 的 `public_packet_path` 字段为双 packet 引用。
- 按 Backlog_Entry 列表排期 v0.2 spec（与 design Definition of Done DoD-13 / §Correctness Properties 9 条 audit-style invariants 一致）：以本 Dogfood_Report 的 Findings 表 7 行 + 3 个 PLANS anchor 作为 v0.2 milestone 的 In_Scope_Fix 候选输入；新 spec 必须独立列 Non-Goals 与 Trust_Baseline 保护章节，沿用本里程碑的 EARS / Schema / Pre-Merge Gate Checklist 形态。
- **不变量保护**：保持 Existing_Release_Tag 9 集合 / Policy Gate scope `{move_file, rename_file}` / live DB restore deferred / hash-guarded undo / sensitive-file omission 5 个不变量在所有 follow-up 里程碑中持续维持；任一 follow-up Polish_PR 触及 design §Non-Goals 8 条任一项必须立即拒绝并路由到独立新 spec（Requirement 9.7 / 12.2）；Tag immutability 在每次 Polish_PR 合并前后双 capture `git ls-remote --tags origin` + `gh release list --limit 100 --json tagName,publishedAt` SHA-256 必须与本里程碑 baseline `0B4AAEAC…329E` / `CACAB81B…979F` byte-identical（DoD-8 / Property 4 同根 audit）。
