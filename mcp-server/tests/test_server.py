"""Tests for MCP server tool listing and dispatch."""

import pytest

from proofflow_mcp.server import TOOLS, _server


def test_all_tools_defined():
    """All 11 MVP tools are registered."""
    names = {t.name for t in TOOLS}
    expected = {
        "proofflow_health",
        "proofflow_scan",
        "proofflow_suggest",
        "proofflow_review",
        "proofflow_status",
        "proofflow_approve_execute",
        "proofflow_export_packet",
        "proofflow_search",
        "proofflow_list_cases",
        "proofflow_list_actions",
        "proofflow_undo",
    }
    assert names == expected


def test_tool_schemas_have_required_fields():
    """Each tool has a valid inputSchema with type and properties."""
    for tool in TOOLS:
        schema = tool.inputSchema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema


def test_tool_descriptions_not_empty():
    """Each tool has a non-empty description."""
    for tool in TOOLS:
        assert tool.description
        assert len(tool.description) > 10
