from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class Recipe:
  id: str
  title: str
  summary: str
  cuisine: str
  diet_tags: List[str]
  prep_minutes: int
  cook_minutes: int
  calories_per_person: int
  ingredients: List[Dict[str, Any]]
  steps: List[str]
  required_tools: List[str] = field(default_factory=list)
  source_url: Optional[str] = None

  def to_dict(self) -> Dict[str, Any]:
    from dataclasses import asdict

    return asdict(self)


@dataclass
class PantryItemUsage:
  name: str
  quantity: Optional[float] = None
  unit: Optional[str] = None
  days_until_expiry: Optional[int] = None


@dataclass
class PlanTaggingResult:
  plan_id: str
  applied_tags: List[str]
  status: Literal["stored", "stub"]


@dataclass
class CalendarEvent:
  title: str
  date: str  # ISO date: YYYY-MM-DD
  time: Optional[str] = None  # Optional HH:MM, 24h
  description: Optional[str] = None
