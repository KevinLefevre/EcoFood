from __future__ import annotations

from typing import Any, Dict, List

from mcp_sdk import McpServer, ToolInput

from ..agent.tools.mcp.calendar_tools import build_calendar_ics

calendar_server = McpServer(name="ecofood-calendar", version="1.0.0")


@calendar_server.tool(
  name="calendar.export-ics",
  description="Convert structured events into an ICS calendar payload.",
  input_schema=ToolInput(
    properties={
      "events": {
        "type": "array",
        "description": "List of calendar events with title/date/time/description.",
      }
    },
    required=["events"],
  ),
)
def export_calendar(events: List[Dict[str, Any]]) -> Dict[str, Any]:
  return build_calendar_ics(events)


def run_calendar_server() -> None:  # pragma: no cover - manual execution
  calendar_server.run()
