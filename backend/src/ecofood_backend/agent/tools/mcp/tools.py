from __future__ import annotations

from typing import Any, Dict

from .registry import get_all_tools, get_tool_set


def load_tool_set(name: str) -> Dict[str, Any]:
  """
  Convenience wrapper returning a single tool set.

  This mirrors `registry.get_tool_set` but keeps a stable name
  for callers that already import from `.tools`.
  """

  return get_tool_set(name)


def load_all_tools() -> Dict[str, Any]:
  """
  Convenience wrapper returning all registered tools.

  Prefer `load_tool_set` for specialized agents.
  """

  return get_all_tools()

