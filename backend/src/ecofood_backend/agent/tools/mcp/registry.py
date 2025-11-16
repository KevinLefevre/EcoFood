from __future__ import annotations

import importlib
from typing import Any, Dict


_TOOL_MODULES: Dict[str, str] = {
  "recipes": ".recipes",
  "nutrition": ".nutrition",
  "household": ".household",
  "plans": ".plans",
  "pantry": ".pantry",
  "calendar": ".calendar_tools",
  "shopping": ".shopping",
  "chef": ".chef",
}


def get_tool_set(name: str) -> Dict[str, Any]:
  """
  Lazily load a single tool set (namespace) by name.

  Example names:
  - "recipes"
  - "nutrition"
  - "household"
  - "plans"
  - "pantry"
  - "calendar"
  - "shopping"
  """

  try:
    module_name = _TOOL_MODULES[name]
  except KeyError as exc:
    available = ", ".join(sorted(_TOOL_MODULES))
    raise KeyError(f"Unknown MCP tool set {name!r}. Available: {available}") from exc

  module = importlib.import_module(module_name, __package__)
  tools: Dict[str, Any] = getattr(module, "TOOLS")
  return tools


def get_all_tools() -> Dict[str, Any]:
  """
  Load and merge all MCP tool sets into a single registry.

  Use this only when you truly want every tool; for specialized
  agents, prefer `get_tool_set(...)`.
  """

  combined: Dict[str, Any] = {}
  for name in _TOOL_MODULES:
    tools = get_tool_set(name)
    combined.update(tools)
  return combined
