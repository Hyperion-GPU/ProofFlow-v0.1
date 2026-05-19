# ProofFlow

[English](README.md) | [简体中文](README.zh-CN.md)

**面向 AI coding 的 Agent Work Ledger。**

Vibe coding is fast. Blind trust is not enough.

ProofFlow 让 AI coding agents 的行为变得可评审、可追踪、可回退：先记录 work contract，再写清 algorithm decision 和 cost budget，然后捕获 snapshot，把 claim 绑定到 evidence，评估 done criteria，最后导出 Proof Packet。

**最新版本：** [v0.1.8 - Agent Work Ledger for AI coding](https://github.com/Hyperion-GPU/ProofFlow-v0.1/releases/tag/v0.1.8)

▶ **观看 72 秒演示：** [From AI agent claims to verifiable Proof Packets](https://github.com/Hyperion-GPU/ProofFlow-v0.1/releases/tag/v0.1.3)<br>
📦 **Proof Packet 示例：** [`code review`](docs/examples/proof_packet_codex_review.md) · [`issue triage`](docs/examples/proof_packet_issue_triage.md) · [`agent work ledger`](docs/examples/proof_packet_agent_work_ledger.md) · [`ledger dogfood`](docs/examples/proof_packet_agent_work_ledger_dogfood.md)

**Agent Work Ledger 指南：** [`docs/agent_work_ledger.md`](docs/agent_work_ledger.md)

**5 分钟 MCP quickstart：** [`docs/ledger_quickstart_mcp.md`](docs/ledger_quickstart_mcp.md)

[![ProofFlow AgentGuard demo screenshot](docs/assets/proofflow-demo-thumbnail.png)](https://github.com/Hyperion-GPU/ProofFlow-v0.1/releases/tag/v0.1.3)

[![Backend](https://img.shields.io/badge/backend-FastAPI-0f5132)](#architecture)
[![Frontend](https://img.shields.io/badge/frontend-React-0f5132)](#architecture)
[![Database](https://img.shields.io/badge/database-SQLite-0f5132)](#architecture)
[![License](https://img.shields.io/badge/license-MIT-0f5132)](LICENSE)

## ProofFlow 是什么

ProofFlow 是一个 local-first audit layer，用来包在 Codex-assisted 和 MCP-compatible AI coding agent 工作流外面。它不阻止快速 AI 辅助开发，而是把快速开发变成可以被维护者审查、复现和回滚的工程流程。

核心闭环：

1. Agent 提出 claim。
2. ProofFlow 捕获 evidence graph。
3. Policy gate 检查高风险 action。
4. Undo metadata 记录回退路径。
5. Proof Packet 导出给 PR review、release audit 或 maintainer handoff。

## 为什么需要

AI coding agents 已经可以读代码、改代码、运行命令并自动化开源维护任务。但在真实 OSS 仓库里，维护者不能只相信一句“我修好了”。

ProofFlow 关注的是证据和控制权：

- No Evidence, no trusted Claim.
- No Preview, no Action.
- No Undo, no destructive Action.
- No Test, no accepted code workflow.
- Final review belongs to human maintainers.

## 快速开始

> **Demo 资产（Deferred）**：本里程碑（v0.1.x dogfood-and-channel-polish）
> 因执行环境无可视 VS Code 窗口可抓取，端到端 Demo_Asset GIF 与 VSCode_Channel
> inline audit / Approve Gate 截图统一推迟到下个 dogfood 周期。Backlog 锚点：
> [`PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood`](PLANS.md#vscode-channel-screenshots-deferred-from-v0-1-x-dogfood)。

以下命令在 PowerShell 中执行，cwd 为仓库根；每段使用 `Push-Location` /
`Pop-Location` 配对，结束后会回到仓库根，便于在同一会话内连续粘贴执行。
backend 端口固定为 `8787`，与 `make dev-backend` 与 `README.md` 一致。
`npm run dev` 是长驻进程，建议在第二个 PowerShell 会话中执行 frontend 段，
以便保留第一个会话用于查看 backend uvicorn 输出。

### Backend

```powershell
Push-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787 --reload
Pop-Location
```

### Frontend

```powershell
Push-Location frontend
npm install
npm run dev
Pop-Location
```

### MCP server

ProofFlow 已发布到 PyPI，包名 `proofflow-mcp`，console-script 入口
`proofflow-mcp` 与 README.md / `.mcp.json` 保持一致：

```powershell
pip install proofflow-mcp
```

将以下内容加入项目的 `.mcp.json`：

```json
{
  "mcpServers": {
    "proofflow": {
      "command": "proofflow-mcp",
      "env": { "PROOFFLOW_BASE_URL": "http://127.0.0.1:8787" }
    }
  }
}
```

如需从源码安装（用于 mcp-server 开发），在仓库根执行：

```powershell
Push-Location .
pip install -e mcp-server\
Pop-Location
```

`mcp-server/` 没有独立 `requirements.txt`，依赖由 `pyproject.toml` 管理。

## 架构

ProofFlow v0.1 由三个本地组件组成：

- `backend/`：FastAPI 服务，负责 case、claim、evidence、policy decision、undo metadata 和 proof packet。
- `frontend/`：React UI，用于查看 evidence graph、policy gate 状态和 packet 输出。
- `mcp-server/`：MCP-compatible server，让 AI coding agents 可以把 claim、evidence 和 action preview 写入 ProofFlow。

默认信任边界是 localhost。项目不依赖云同步、远程 telemetry 或托管数据库。

## 核心能力

- **Evidence-backed claims**：agent 的 claim 必须绑定 diff、文件、命令、测试结果或 reviewer notes。
- **Evidence graph**：把 Claim -> Evidence -> Files -> Tests -> Diff -> Decision 串成可读链路。
- **Policy gate**：高风险 action 需要 preview、approval 和 undo metadata。
- **Undo metadata**：危险操作必须有 snapshot、before/after 和 rollback route。
- **Proof Packet**：将 claims、evidence links、policy decisions、test results、undo metadata 和 maintainer notes 导出为可审计包。

## 安全边界

ProofFlow 的目标不是替代维护者判断，而是让维护者拥有更好的证据。

- 它不会暗示 AI agent 的修改自动可信。
- 它不会把 destructive action 当成普通日志记录。
- 它不会跳过 human maintainer review。
- 它不会把 Codex-compatible workflow 描述成任何官方背书或批准。

## 开发与验证

常用检查：

```bash
python -m pytest
npm test
```

如果只修改文档，建议至少检查 Markdown 链接和 GitHub 渲染效果。

## 项目状态

ProofFlow v0.1 是面向本地 OSS 维护工作流的 MVP。当前重点是把 AI-assisted coding 的输出变成可证明、可审查、可回退的本地证据链，而不是扩展成云平台或安装教程。

## License

MIT
