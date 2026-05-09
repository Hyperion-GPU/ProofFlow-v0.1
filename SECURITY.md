# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in ProofFlow, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

1. **Preferred**: Use [GitHub Security Advisories](https://github.com/Hyperion-GPU/ProofFlow-v0.1/security/advisories/new) to report privately.
2. **Alternative**: Email security@proofflow.dev with details.

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Fix timeline**: Depends on severity; critical issues targeted within 7 days

### What to Expect

- We will acknowledge your report promptly
- We will work with you to understand and validate the issue
- We will develop and release a fix
- We will credit you in the release notes (unless you prefer anonymity)

## Security Design

ProofFlow is designed as a **local-first** tool. Key security properties:

- All data stays on the user's machine (SQLite + local filesystem)
- CORS locked to localhost origins by default
- Optional API key authentication (`PROOFFLOW_API_KEY`)
- Rate limiting support (`PROOFFLOW_RATE_LIMIT`)
- Filesystem action scope restrictions (`allowed_roots`)
- No telemetry, no external network calls

## Scope

This security policy covers:
- The ProofFlow backend (`backend/`)
- The MCP server (`mcp-server/`)
- The VS Code extension (`vscode-proofflow/`)
- The web frontend (`frontend/`)
