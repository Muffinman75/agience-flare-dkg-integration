"""Unit tests for the MCP stdio server tool definitions and message handling."""

import json

import pytest

from agience_dkg_integration.mcp_server import TOOLS, _handle_message


class TestToolDefinitions:
    """Verify MCP tool schemas are well-formed."""

    def test_three_tools_defined(self):
        assert len(TOOLS) == 3

    def test_tool_names(self):
        names = {t["name"] for t in TOOLS}
        assert names == {"agience_wm_write", "agience_promote", "agience_search"}

    def test_wm_write_required_fields(self):
        """Only context_graph_id is statically required.

        title/artifact_type/artifact_id/content are conditionally required: either
        supplied directly or sourced from --from-agience-artifact (governed mode).
        The conditional check lives in `_execute_tool` and is covered by the
        governed-mode tests below.
        """
        wm = next(t for t in TOOLS if t["name"] == "agience_wm_write")
        required = wm["inputSchema"]["required"]
        assert required == ["context_graph_id"]
        properties = wm["inputSchema"]["properties"]
        assert "from_agience_artifact" in properties
        assert "title" in properties
        assert "artifact_type" in properties
        assert "content" in properties

    def test_wm_write_governance_described_in_tool(self):
        """The tool description must explicitly differentiate vs `dkg-create`."""
        wm = next(t for t in TOOLS if t["name"] == "agience_wm_write")
        desc = wm["description"]
        assert "dkg-create" in desc
        assert "agience:" in desc

    def test_promote_description_calls_out_curator(self):
        promo = next(t for t in TOOLS if t["name"] == "agience_promote")
        desc = promo["description"].lower()
        assert "curator" in desc

    def test_promote_required_fields(self):
        promo = next(t for t in TOOLS if t["name"] == "agience_promote")
        required = promo["inputSchema"]["required"]
        assert "turn_uri" in required
        assert "context_graph_id" in required

    def test_search_required_fields(self):
        search = next(t for t in TOOLS if t["name"] == "agience_search")
        required = search["inputSchema"]["required"]
        assert "query" in required
        assert "context_graph_id" in required

    def test_all_tools_have_descriptions(self):
        for tool in TOOLS:
            assert tool.get("description"), f"{tool['name']} missing description"
            assert len(tool["description"]) > 20


class TestMessageHandling:
    """Verify JSON-RPC message routing."""

    def test_initialize_returns_server_info(self):
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }
        resp = _handle_message(msg)
        assert resp["id"] == 1
        assert resp["result"]["serverInfo"]["name"] == "agience-dkg"
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in resp["result"]["capabilities"]

    def test_tools_list_returns_all_tools(self):
        msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = _handle_message(msg)
        assert resp["id"] == 2
        tools = resp["result"]["tools"]
        assert len(tools) == 3
        names = {t["name"] for t in tools}
        assert "agience_wm_write" in names
        assert "agience_promote" in names
        assert "agience_search" in names

    def test_initialized_notification_returns_none(self):
        msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = _handle_message(msg)
        assert resp is None

    def test_unknown_method_returns_error(self):
        msg = {"jsonrpc": "2.0", "id": 3, "method": "foo/bar", "params": {}}
        resp = _handle_message(msg)
        assert resp["error"]["code"] == -32601
        assert "foo/bar" in resp["error"]["message"]

    def test_unknown_method_notification_returns_none(self):
        msg = {"jsonrpc": "2.0", "method": "foo/bar"}
        resp = _handle_message(msg)
        assert resp is None

    def test_unknown_tool_returns_error(self, monkeypatch):
        monkeypatch.setenv("DKG_TOKEN", "test-token")
        msg = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
        resp = _handle_message(msg)
        assert resp["result"]["isError"] is True
        assert "Unknown tool" in resp["result"]["content"][0]["text"]
