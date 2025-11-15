"""
MCP-aligned tools for EcoFood.

The functions defined here are designed to be:
- Stateless and deterministic given their inputs.
- Explicit about their input and output schemas.
- Easy to expose via a Model Context Protocol (MCP) server.

They are not yet wired to a specific MCP library; that integration
will be added separately.
"""

from .registry import get_all_tools, get_tool_set

__all__ = [
  "get_all_tools",
  "get_tool_set",
]
