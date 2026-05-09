# Contributing to ProofFlow

Thank you for your interest in contributing to ProofFlow! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 22+
- Git

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest  # verify: 274 tests pass
python -m uvicorn proofflow.main:app --port 8787 --reload
```

### Frontend

```bash
cd frontend
npm ci
npm run test  # verify: 24 tests pass
npm run dev   # starts on http://localhost:5173
```

### MCP Server

```bash
cd mcp-server
pip install -e ".[dev]"
python -m pytest  # verify: 24 tests pass
```

### VS Code Extension

```bash
cd vscode-proofflow
npm ci
npm run build
# Press F5 in VS Code to launch Extension Development Host
```

## How to Contribute

### Reporting Bugs

Use the [Bug Report](https://github.com/Hyperion-GPU/ProofFlow-v0.1/issues/new?template=bug_report.yml) template. Include:

- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python/Node version, ProofFlow version)

### Suggesting Features

Use the [Feature Request](https://github.com/Hyperion-GPU/ProofFlow-v0.1/issues/new?template=feature_request.yml) template.

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Add or update tests as needed
5. Run the test suite for affected components
6. Commit with a descriptive message (see Commit Style below)
7. Push and open a PR against `main`

## Code Style

### Python (backend, mcp-server)

- Formatter: [Black](https://github.com/psf/black) (default settings)
- Linter: [Ruff](https://github.com/astral-sh/ruff)
- Type hints encouraged for public APIs

### TypeScript (frontend, vscode-proofflow)

- Strict mode enabled
- Prefer named exports
- Use TypeScript interfaces over `any`

## Commit Style

```
<type>: <short description>

Types: feat, fix, docs, test, refactor, ci, chore
```

Examples:
- `feat: add webhook notification for gate decisions`
- `fix: correct action status transition from pending to approved`
- `docs: update MCP integration guide`

## Testing Requirements

- New features must include tests
- Bug fixes should include a regression test
- All existing tests must pass before merging

| Component | Command | Expected |
|-----------|---------|----------|
| Backend | `cd backend && python -m pytest` | 274+ tests pass |
| Frontend | `cd frontend && npm run test` | 24+ tests pass |
| MCP Server | `cd mcp-server && python -m pytest` | 24+ tests pass |

## Project Structure

```
ProofFlow-v0.1/
├── backend/          # FastAPI + SQLite (Python)
├── frontend/         # React 19 + Vite (TypeScript)
├── mcp-server/       # MCP protocol server (Python)
├── vscode-proofflow/ # VS Code extension (TypeScript)
├── docs/             # Architecture & design docs
└── scripts/          # Utility & smoke test scripts
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.