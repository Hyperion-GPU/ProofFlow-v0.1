# `docs/examples/` — milestone v0.1.x dogfood-and-channel-polish

> Generated for milestone v0.1.x dogfood-and-channel-polish; not a release artifact.

本目录承载本里程碑 (`v0.1.x dogfood-and-channel-polish`) 范围内针对 Latest_Main 重新生成的 **Public_Proof_Packet_Example**，供 Dogfood_Report (`docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md`) 的 `Demo 资产与示例 Proof Packet / Demo and Example Packet` 章节按 evidence type `proof_packet_path` 引用。

本目录中既有的早期 packet（`V0_1_DOGFOOD_PROOF_PACKET.md`、`proof_packet_agent_work_ledger*.md`、`proof_packet_codex_*.md`、`proof_packet_issue_triage.md`、`pr_comment_agent_work_ledger.md`）属于历史里程碑示例，**不**属于本里程碑 evidence；本里程碑新增 packet 请按下文命名约定落地，不要覆盖既有文件。

## 用途 / Purpose

- 给外部 reviewer / 新用户一份 **可复现** 的 ProofFlow Proof Packet 示例：能在 fresh Windows clone 上按 packet 顶部的 `生成命令` 一字不差复现出等价产物。
- 与 README v0.1.6 dogfood 故事衔接，作为「ProofFlow Reviewed ProofFlow」叙事的延续（AgentGuard packet 优先；理想再补一份 LocalProof packet）。
- 与 Dogfood_Report 三渠道证据 / Channel Evidence 中 `MCP_Channel` 块的 `proof_packet_path` 字段交叉一致（同一份 packet 通过 `proofflow_export_packet` 在 MCP 渠道导出，再复制为本目录下的公开版本）。

## 命名约定 / Public Packet Naming Convention

与 `design.md` §Public Proof Packet Example Design 对齐，本里程碑使用以下命名（仓库相对路径，全部小写，分隔符 `_`，版本段使用 `v0_1_x` 而非 `v0.1.x`）：

| Case 类型 | 推荐文件名 |
| --- | --- |
| AgentGuard packet（优先） | `docs/examples/proof_packet_v0_1_x_agentguard_dogfood.md` |
| LocalProof packet（理想补充） | `docs/examples/proof_packet_v0_1_x_localproof_dogfood.md` |

如时间紧只产出 1 份，**优先 AgentGuard**（与 README 现有 v0.1.6 dogfood 故事一脉相承，且能复用 GHA 渠道证据）。

## Packet 顶部必备元数据 / Required Header Fields

每份 Public_Proof_Packet_Example 顶部必须显式包含下列字段（与 `design.md` §Public Proof Packet Example Design / §Schema 7 一致）：

1. `Latest_Main commit SHA`（40 hex，使用 `git rev-parse HEAD` 在生成时刻 capture）。
2. `生成时间 / Generated At`（ISO8601，例如 `2026-04-27T10:57:45+08:00`）。
3. `生成命令 / Generator Command`（完整可粘贴 PowerShell 字符串；任何临时路径必须用 `<TMP>` 占位符替换，**不**允许内嵌真实本地绝对路径或用户名）。
4. 显式声明：`Generated for milestone v0.1.x dogfood; not a release artifact`。

示例（伪 packet 头，仅展示形态，不要直接拷贝为真实 packet）：

```markdown
# ProofFlow v0.1.x AgentGuard Dogfood Proof Packet (Public Example)

- Latest_Main commit SHA: `<40-hex-sha>`
- Generated At: `2026-04-27T10:57:45+08:00`
- Generator Command: `python .\scripts\generate_real_docs_output.py --case-type agentguard --output "<TMP>\packet.md"`
- Statement: Generated for milestone v0.1.x dogfood; not a release artifact.
```

## 隐私脱敏要求 / Privacy and Redaction

提交前必须满足下列硬约束（与 `docs/assets/README.md` 同一套隐私基线）：

1. **不允许内嵌本地绝对路径或用户名**——packet 全文（包括 Inputs / Artifacts / Claims / Evidence 各章节）都不得出现 `C:\Users\<name>\…`、`D:\Users\<name>\…` 这类含真实用户名的本地绝对路径。
2. 如必须引用临时路径，统一使用 `<TMP>` 占位符，例如 `<TMP>\proofflow-dogfood-<ts>\data\proof_packets\<id>.md`；**不**直接引用 `$PROOFFLOW_DATA_DIR` 内的真实临时路径。
3. 提交前用 `Select-String` / ripgrep 自查，例如：

   ```powershell
   Push-Location "D:\ProofFlow v0.1"
   Get-ChildItem .\docs\examples\proof_packet_v0_1_x_*.md |
     Select-String -Pattern '[A-Z]:\\Users\\' -CaseSensitive:$false
   Pop-Location
   ```

   命中即视为 evidence 不合规，必须删掉公开版本并用占位符重新生成（reshoot，**不**做后期手工编辑）。
4. 不得在 packet 中粘贴 `.mcp.json` / `.codex/config.toml` 中的真实 token / API key；如需展示，先用占位符（如 `<MCP_TOKEN>`）替换。
5. AgentGuard packet 中的 git diff 引用应避免暴露未提交私有文件内容；仅保留路径与 hash。

## Windows 路径与 PowerShell 约定

- Windows 路径若含空格（例如 `D:\ProofFlow v0.1\docs\examples`），在 packet 内引用的命令字符串与本 README 中所有示例命令都必须用双引号包裹，例如：

  ```powershell
  Push-Location "D:\ProofFlow v0.1"
  python .\scripts\generate_real_docs_output.py --output "<TMP>\packet.md"
  Pop-Location
  ```

- 不依赖隐式 `cd`；切换工作目录统一用 `Push-Location` / `Pop-Location` 配对。
- packet 中如展示 backend 端点，端口固定为 `8787`（与 README quickstart、`docs/V0_1_DOGFOOD.md` 一致），不允许出现 `:8000` / `:5000` / `--port 8000` 等其它端口示例。

## 引用回写

任何新增 packet 落地后，必须同步在 Dogfood_Report (`docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md`) 的 `Demo 资产与示例 Proof Packet / Demo and Example Packet` 章节字段 `public_packet_path` / `public_packet_generator_cmd`（`<TMP>` 占位符）/ `public_packet_commit_sha` 中登记，并与三渠道证据 / Channel Evidence 的 `MCP_Channel` 块的 `proof_packet_path` 字段交叉一致。
