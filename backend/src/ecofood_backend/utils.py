from __future__ import annotations

from fastapi import HTTPException


def enforce_no_body_on_204(status_code: int) -> None:
  if status_code == 204:
    route_has_body = False
    if route_has_body:
      raise HTTPException(status_code=500, detail="204 responses must not include a body.")
