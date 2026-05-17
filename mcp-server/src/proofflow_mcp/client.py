"""HTTP client wrapper for the ProofFlow backend REST API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class ProofFlowError(Exception):
    """Raised when a ProofFlow API call fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ProofFlowClient:
    """Async HTTP client for the ProofFlow backend."""

    def __init__(self) -> None:
        self._base_url = os.getenv("PROOFFLOW_BASE_URL", "http://127.0.0.1:8787")
        self._timeout = float(os.getenv("PROOFFLOW_TIMEOUT", "30"))
        self._http: httpx.AsyncClient | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            headers: dict[str, str] = {}
            api_key = os.getenv("PROOFFLOW_API_KEY")
            if api_key:
                headers["X-ProofFlow-Token"] = api_key
            self._http = httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout, headers=headers
            )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]]:
        http = await self._get_http()
        try:
            response = await http.request(method, path, **kwargs)
        except httpx.ConnectError:
            raise ProofFlowError(
                "ProofFlow backend is not running. "
                "Start it with: cd backend && python -m uvicorn proofflow.main:app --port 8787"
            )
        except httpx.TimeoutException:
            raise ProofFlowError(
                f"ProofFlow backend timed out after {self._timeout}s"
            )

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise ProofFlowError(
                f"ProofFlow API error ({response.status_code}): {detail}",
                status_code=response.status_code,
            )

        return response.json()

    # --- Health ---

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    # --- Cases ---

    async def list_cases(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/cases")

    async def get_case_packet(self, case_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/cases/{case_id}/packet")

    # --- LocalProof ---

    async def scan(
        self,
        folder_path: str,
        recursive: bool = True,
        max_files: int = 500,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/localproof/scan",
            json={"folder_path": folder_path, "recursive": recursive, "max_files": max_files},
        )

    async def suggest_actions(
        self, case_id: str, target_root: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/localproof/suggest-actions",
            json={"case_id": case_id, "target_root": target_root},
        )

    # --- AgentGuard ---

    async def review(
        self,
        repo_path: str,
        base_ref: str = "HEAD",
        include_untracked: bool = True,
        test_command: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "repo_path": repo_path,
            "base_ref": base_ref,
            "include_untracked": include_untracked,
        }
        if test_command is not None:
            body["test_command"] = test_command
        return await self._request("POST", "/agentguard/review", json=body)

    async def triage_issue(
        self,
        title: str,
        body: str = "",
        source_url: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": title,
            "body": body,
            "labels": labels or [],
        }
        if source_url is not None:
            payload["source_url"] = source_url
        return await self._request("POST", "/issue-triage", json=payload)

    # --- Agent Work Ledger ---

    async def start_work_contract(
        self,
        objective: str,
        repo_path: str,
        allowed_scope: list[str] | None = None,
        forbidden_actions: list[str] | None = None,
        required_tests: list[str] | None = None,
        done_criteria: list[str] | None = None,
        evidence_requirements: list[str] | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/ledger/start",
            json={
                "objective": objective,
                "repo_path": repo_path,
                "allowed_scope": allowed_scope or [],
                "forbidden_actions": forbidden_actions or [],
                "required_tests": required_tests or [],
                "done_criteria": done_criteria or [],
                "evidence_requirements": evidence_requirements or [],
            },
        )

    async def record_event(
        self,
        case_id: str,
        event_type: str,
        summary: str,
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/ledger/cases/{case_id}/events",
            json={
                "event_type": event_type,
                "summary": summary,
                "content": content,
                "metadata": metadata or {},
            },
        )

    async def capture_snapshot(
        self,
        case_id: str,
        repo_path: str,
        phase: str,
        base_ref: str = "HEAD",
        include_untracked: bool = True,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/ledger/cases/{case_id}/snapshots",
            json={
                "repo_path": repo_path,
                "phase": phase,
                "base_ref": base_ref,
                "include_untracked": include_untracked,
            },
        )

    async def record_evidence(
        self,
        case_id: str,
        evidence_type: str,
        content: str,
        source_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "evidence_type": evidence_type,
            "content": content,
            "metadata": metadata or {},
        }
        if source_ref is not None:
            body["source_ref"] = source_ref
        return await self._request(
            "POST", f"/ledger/cases/{case_id}/evidence", json=body
        )

    async def record_claim(
        self,
        case_id: str,
        claim_text: str,
        evidence_ids: list[str],
        severity: str = "info",
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/ledger/cases/{case_id}/claims",
            json={
                "claim_text": claim_text,
                "severity": severity,
                "evidence_ids": evidence_ids,
            },
        )

    async def evaluate_contract(self, case_id: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/ledger/cases/{case_id}/evaluate"
        )

    async def finish_work_ledger(
        self, case_id: str, summary: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if summary is not None:
            body["summary"] = summary
        return await self._request(
            "POST", f"/ledger/cases/{case_id}/finish", json=body
        )

    # --- Actions ---

    async def list_actions(self, case_id: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"/cases/{case_id}/actions")

    async def approve_action(self, action_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/actions/{action_id}/approve")

    async def execute_action(self, action_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/actions/{action_id}/execute")

    async def undo_action(self, action_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/actions/{action_id}/undo")

    # --- Reports ---

    async def export_report(self, case_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/reports/cases/{case_id}/export",
            json={"format": "markdown"},
        )

    # --- Search ---

    async def search(self, query: str, limit: int = 25) -> dict[str, Any]:
        return await self._request(
            "GET", "/search", params={"q": query, "limit": limit}
        )

    # --- Decisions ---

    async def create_decision(
        self,
        case_id: str,
        title: str,
        status: str,
        rationale: str,
        result: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "title": title,
            "status": status,
            "rationale": rationale,
            "result": result,
        }
        if metadata:
            body["metadata"] = metadata
        return await self._request(
            "POST", f"/cases/{case_id}/decisions", json=body
        )
