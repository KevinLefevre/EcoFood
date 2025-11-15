from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SessionContext:
  """
  Shared context passed between agents during a workflow.
  """

  session_id: str
  data: Dict[str, Any] = field(default_factory=dict)

  def set(self, key: str, value: Any) -> None:
    self.data[key] = value

  def get(self, key: str, default: Any | None = None) -> Any:
    return self.data.get(key, default)

  def snapshot(self) -> Dict[str, Any]:
    return dict(self.data)

