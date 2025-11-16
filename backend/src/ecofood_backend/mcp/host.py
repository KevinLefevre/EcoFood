from __future__ import annotations

from typing import Any, Dict, List

from mcp_sdk import McpHost

from .calendar_server import calendar_server

_host = McpHost()
_host.register_server("calendar", calendar_server)


def call_calendar_export(events: List[Dict[str, Any]]) -> Dict[str, Any]:
  client = _host.get_client("calendar")
  return client.call_tool("calendar.export-ics", events=events)


def get_calendar_client():
  return _host.get_client("calendar")
