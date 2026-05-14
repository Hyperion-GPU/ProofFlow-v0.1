# ProofFlow

[English](README.md) | [简体中文](README.zh-CN.md)

**面向 Codex-compatible AI coding agent 工作流的本地优先审计层。**

Vibe coding is fast. Blind trust is not enough.

ProofFlow 让 AI coding agents 的行为变得可评审、可追踪、可回退：每个 claim 都需要 evidence，每个高风险 action 都需要 policy gate、undo metadata 和 human maintainer review。

▶ **观看 72 秒演示：** [From AI agent claims to verifiable Proof Packets](https://github.com/Hyperion-GPU/ProofFlow-v0.1/releases/tag/v0.1.3)<br>
📦 **Proof Packet 示例：** [`docs/examples/proof_packet_codex_review.md`](docs/examples/proof_packet_codex_review.md)

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

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### MCP server

```bash
cd mcp-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m proofflow_mcp.server
```

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
