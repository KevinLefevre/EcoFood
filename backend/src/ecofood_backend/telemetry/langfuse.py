from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency
  from langfuse import Langfuse
except Exception:  # pragma: no cover - degrade gracefully if not installed
  Langfuse = None  # type: ignore

try:  # pragma: no cover - optional dependency, v3 only
  from langfuse.types import TraceContext
except Exception:  # pragma: no cover - not available on v2
  TraceContext = None  # type: ignore


logger = logging.getLogger(__name__)

_client: Optional[Langfuse] = None  # type: ignore


def _get_client() -> Optional[Langfuse]:  # type: ignore
  global _client
  if Langfuse is None:
    logger.debug("Langfuse SDK not installed; telemetry disabled")
    return None
  if _client is not None:
    return _client
  secret = os.getenv("LANGFUSE_SECRET_KEY")
  public = os.getenv("LANGFUSE_PUBLIC_KEY")
  host = os.getenv("LANGFUSE_HOST_URL") or os.getenv("LANGFUSE_BASE_URL")
  if not secret or not public or not host:
    logger.debug("Langfuse credentials missing; telemetry disabled")
    return None
  try:
    # Langfuse v3 prefers base_url; older v2 rejects it. Try v3 signature first, then fall back.
    try:
      _client = Langfuse(secret_key=secret, public_key=public, host=host.rstrip("/"), base_url=host.rstrip("/"))
    except TypeError:
      _client = Langfuse(secret_key=secret, public_key=public, host=host.rstrip("/"))
    logger.info("Langfuse telemetry enabled: host=%s", host)
  except Exception:  # pragma: no cover - guard against SDK misconfig
    logger.exception("Failed to initialize Langfuse client; telemetry disabled")
    _client = None
  return _client


def start_trace(trace_id: str, name: str, metadata: Optional[Dict[str, Any]] = None):
  client = _get_client()
  if not client:
    return None
  try:
    meta = metadata or {}
    # Prefer legacy API (v2) if present.
    if hasattr(client, "trace"):
      return client.trace(id=trace_id, name=name, input=meta, metadata=meta)

    # Fallback for Langfuse v3 (OTel-backed).
    ctx_trace_id = trace_id
    if TraceContext and hasattr(client, "create_trace_id"):
      if not isinstance(trace_id, str) or len(trace_id) != 32 or any(c not in "0123456789abcdef" for c in trace_id.lower()):
        ctx_trace_id = client.create_trace_id()
        extra = meta or {}
        extra["original_trace_id"] = trace_id
        meta = extra
    ctx = TraceContext(trace_id=ctx_trace_id) if TraceContext else None
    return client.start_span(trace_context=ctx, name=name, input=meta, metadata=meta)
  except Exception:  # pragma: no cover - don’t crash planning on telemetry failures
    logger.exception("Unable to start Langfuse trace %s", trace_id)
    return None


def finish_trace(trace, status: str, output: Optional[Dict[str, Any]] = None) -> None:
  client = _get_client()
  if not client or trace is None:
    return
  try:
    trace.update(status_message=status, metadata={"status": status}, output=output or {})
    if hasattr(trace, "end"):
      trace.end()
    client.flush()  # ensure buffered events are sent promptly
  except Exception:  # pragma: no cover
    logger.exception("Unable to finalize Langfuse trace")


def record_agent_span(
  trace,
  *,
  name: str,
  stage: str,
  inputs: str,
  output_keys: str,
  elapsed: float,
  status: str = "success",
  error: Optional[str] = None,
) -> None:
  client = _get_client()
  if not client or trace is None:
    return
  try:
    metadata = {
      "stage": stage,
      "output_keys": output_keys,
      "status": status,
      "error": error,
    }
    output_body = {"elapsed_seconds": elapsed, "status": status}
    # Legacy API
    if hasattr(client, "span"):
      client.span(
        trace_id=getattr(trace, "id", None),
        name=name,
        input=inputs,
        output=output_body,
        metadata=metadata,
      )
      return
    # v3 API: create child span from the active trace/span
    if hasattr(trace, "start_span"):
      span = trace.start_span(name=name, input=inputs, metadata=metadata)
      span.update(output=output_body, status_message=status)
      if hasattr(span, "end"):
        span.end()
      return
  except Exception:  # pragma: no cover
    logger.exception("Unable to record Langfuse span for %s", name)
