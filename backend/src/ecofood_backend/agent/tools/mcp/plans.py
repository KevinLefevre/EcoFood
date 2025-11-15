from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import PlanTaggingResult


_PLAN_STORE: Dict[str, Dict[str, Any]] = {}
_PLAN_COUNTER = 0


def _next_plan_id() -> str:
  global _PLAN_COUNTER
  _PLAN_COUNTER += 1
  return f"plan-{_PLAN_COUNTER}"


def plans_save_and_tag(plan: Dict[str, Any], tags: Optional[List[str]] = None) -> Dict[str, Any]:
  """
  Store a plan in an in-memory registry and attach basic tags.

  This is a stub implementation to support early agent workflows.
  Persistence will be moved into the database later.
  """

  plan_id = _next_plan_id()
  normalized_tags = sorted({t.strip().lower() for t in (tags or []) if t.strip()})

  _PLAN_STORE[plan_id] = {
    "plan": plan,
    "tags": normalized_tags,
    "created_at": datetime.utcnow().isoformat() + "Z",
  }

  result = PlanTaggingResult(
    plan_id=plan_id,
    applied_tags=normalized_tags,
    status="stored",
  )
  return asdict(result)


TOOLS: Dict[str, Any] = {
  "plans.save-and-tag": plans_save_and_tag,
}

