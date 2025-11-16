from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Any, Callable, Dict


@dataclass
class ToolInput:
  properties: Dict[str, Any] | None = None
  required: list[str] | None = None


@dataclass
class _Tool:
  name: str
  description: str
  input_schema: ToolInput | None
  func: Callable[..., Any]


class McpServer:
  def __init__(self, name: str, version: str) -> None:
    self.name = name
    self.version = version
    self._tools: Dict[str, _Tool] = {}

  def tool(
    self,
    *,
    name: str,
    description: str,
    input_schema: ToolInput | None = None,
  ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
      self._tools[name] = _Tool(name, description, input_schema, func)
      return func

    return decorator

  def list_tools(self) -> Dict[str, Dict[str, Any]]:
    return {
      name: {
        "description": tool.description,
        "input_schema": tool.input_schema.properties if tool.input_schema else None,
      }
      for name, tool in self._tools.items()
    }

  def invoke(self, tool_name: str, **kwargs: Any) -> Any:
    if tool_name not in self._tools:
      raise KeyError(f"Tool {tool_name!r} not registered on {self.name}.")
    tool = self._tools[tool_name]
    return tool.func(**kwargs)

  def run(self) -> None:  # pragma: no cover - CLI convenience
    print(f"MCP server '{self.name}' v{self.version} running with {len(self._tools)} tool(s). Press Ctrl+C to exit.")
    try:
      Event().wait()
    except KeyboardInterrupt:
      print("Server stopped.")


class McpClient:
  def __init__(self, server: McpServer) -> None:
    self._server = server

  def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
    return self._server.invoke(tool_name, **kwargs)


class McpHost:
  def __init__(self) -> None:
    self._clients: Dict[str, McpClient] = {}

  def register_server(self, alias: str, server: McpServer) -> None:
    if alias in self._clients:
      raise ValueError(f"Server alias {alias!r} already registered.")
    self._clients[alias] = McpClient(server)

  def get_client(self, alias: str) -> McpClient:
    if alias not in self._clients:
      raise KeyError(f"Server alias {alias!r} is not registered.")
    return self._clients[alias]
