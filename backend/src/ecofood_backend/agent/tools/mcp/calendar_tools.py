from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from .models import CalendarEvent


def build_calendar_ics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
  """
  Export a set of meal events to an iCalendar (ICS) string.

  Expected event shape:
  {
    "title": str,
    "date": "YYYY-MM-DD",
    "time": "HH:MM" | None,
    "description": str | None
  }
  """

  parsed_events: List[CalendarEvent] = []
  for raw in events:
    parsed_events.append(
      CalendarEvent(
        title=str(raw.get("title", "")).strip(),
        date=str(raw.get("date", "")).strip(),
        time=(str(raw["time"]).strip() if raw.get("time") else None),
        description=(
          str(raw["description"]).strip() if raw.get("description") else None
        ),
      )
    )

  def fmt_dt(ev: CalendarEvent) -> str:
    # If no time is provided, default to 18:00 local (6pm).
    base_time = ev.time or "18:00"
    dt = datetime.fromisoformat(f"{ev.date}T{base_time}")
    return dt.strftime("%Y%m%dT%H%M%S")

  lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//EcoFood//MealPlanner//EN",
  ]

  now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

  for idx, ev in enumerate(parsed_events, start=1):
    if not ev.title or not ev.date:
      continue
    dtstart = fmt_dt(ev)
    uid = f"ecofood-{idx}-{dtstart}@local"

    lines.extend(
      [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART:{dtstart}",
        f"SUMMARY:{ev.title}",
      ]
    )
    if ev.description:
      # Replace newlines with escaped form per ICS spec.
      desc = ev.description.replace("\n", "\\n")
      lines.append(f"DESCRIPTION:{desc}")
    lines.append("END:VEVENT")

  lines.append("END:VCALENDAR")

  ics_text = "\r\n".join(lines) + "\r\n"
  return {"ics": ics_text, "event_count": len(parsed_events)}


def calendar_export_ics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
  from ....mcp.host import call_calendar_export

  return call_calendar_export(events)


TOOLS: Dict[str, Any] = {
  "calendar.export-ics": calendar_export_ics,
}
