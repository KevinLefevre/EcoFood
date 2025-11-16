from __future__ import annotations

import os
from typing import Optional

try:
  import google.generativeai as genai
except ImportError:  # pragma: no cover - optional dependency
  genai = None

_MODEL = None
_MODEL_NAME = None


class GeminiClientError(RuntimeError):
  """Raised when Gemini configuration or invocation fails."""


def _ensure_model():
  global _MODEL, _MODEL_NAME
  if _MODEL is not None:
    return _MODEL
  if genai is None:
    raise GeminiClientError(
      "google-generativeai is not installed. Install with `pip install ecofood-backend[gemini]`."
    )
  api_key = os.getenv("GEMINI_API_KEY")
  if not api_key:
    raise GeminiClientError("GEMINI_API_KEY environment variable is missing.")
  genai.configure(api_key=api_key)
  model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
  _MODEL = genai.GenerativeModel(model_name)
  _MODEL_NAME = model_name
  return _MODEL


def generate_text(prompt: str) -> dict[str, str]:
  """
  Generate text from Gemini using the configured model.

  Returns a dict containing the model name and raw text output.
  """

  model = _ensure_model()
  response = model.generate_content(prompt)
  text = getattr(response, "text", None)
  if not text and hasattr(response, "candidates"):
    parts = []
    for candidate in response.candidates:
      content = getattr(candidate, "content", None)
      if content and hasattr(content, "parts"):
        parts.extend(getattr(part, "text", "") for part in content.parts if hasattr(part, "text"))
    text = "\n".join(part for part in parts if part).strip()
  if not text:
    raise GeminiClientError("Gemini returned an empty response.")
  return {"text": text, "model": _MODEL_NAME or "unknown"}
