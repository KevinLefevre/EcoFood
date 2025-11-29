from __future__ import annotations

import asyncio
import logging
import os
import time
from functools import wraps
from typing import Any, Dict, Optional
import json

try:
  from google.generativeai.types import Schema
except Exception:  # pragma: no cover - fallback if types are missing
  Schema = None  # type: ignore

try:
  import google.generativeai as genai
except ImportError:  # pragma: no cover - optional dependency
  genai = None

try:
  from langfuse.decorators import langfuse_context, observe
  HAS_LANGFUSE = True
except ImportError:
  HAS_LANGFUSE = False
  langfuse_context = None  # type: ignore

_MODELS: Dict[str, Any] = {}
logger = logging.getLogger(__name__)


class GeminiClientError(RuntimeError):
  """Raised when Gemini configuration or invocation fails."""


def _configure_genai():
  if genai is None:
    raise GeminiClientError(
      "google-generativeai is not installed. Install with `pip install ecofood-backend[gemini]`."
    )
  api_key = os.getenv("GEMINI_API_KEY")
  if not api_key:
    raise GeminiClientError("GEMINI_API_KEY environment variable is missing.")
  genai.configure(api_key=api_key)


def _get_model_for_task(task_type: str = "default"):
  _configure_genai()
  
  # Map task types to env vars and defaults
  if task_type == "meal_planning":
    model_name = os.getenv("GEMINI_COMPLEX_TASK_MODEL", "gemini-2.5-pro")
    temperature = float(os.getenv("GEMINI_MEAL_TEMP", "0.4"))
    # meals can be verbose; allow a larger default output window
    max_tokens = int(os.getenv("GEMINI_MEAL_MAX_TOKENS", "100000"))
    response_schema = None
    if Schema is not None:
      response_schema = Schema(
        type=Schema.Type.OBJECT,
        properties={
          "plan": Schema(
            type=Schema.Type.ARRAY,
            items=Schema(
              type=Schema.Type.OBJECT,
              properties={
                "day": Schema(type=Schema.Type.STRING),
                "meal": Schema(type=Schema.Type.STRING),
                "title": Schema(type=Schema.Type.STRING),
                "summary": Schema(type=Schema.Type.STRING),
                "ingredients": Schema(
                  type=Schema.Type.ARRAY,
                  items=Schema(
                    type=Schema.Type.OBJECT,
                    properties={
                      "name": Schema(type=Schema.Type.STRING),
                      "quantity": Schema(type=Schema.Type.STRING),
                      "unit": Schema(type=Schema.Type.STRING),
                      "notes": Schema(type=Schema.Type.STRING),
                    },
                    required=["name"],
                  ),
                ),
                "steps": Schema(type=Schema.Type.ARRAY, items=Schema(type=Schema.Type.STRING)),
                "prep_minutes": Schema(type=Schema.Type.NUMBER),
                "cook_minutes": Schema(type=Schema.Type.NUMBER),
                "calories_per_person": Schema(type=Schema.Type.NUMBER),
                "co2_per_person": Schema(type=Schema.Type.NUMBER),
                "required_tools": Schema(type=Schema.Type.ARRAY, items=Schema(type=Schema.Type.STRING)),
              },
              required=["day", "meal", "title", "summary", "ingredients", "steps"],
            ),
            min_items=1,
          )
        },
        required=["plan"],
        additional_properties=False,
      )
  else:
    # Default/Fast model for profiling, reviews, etc.
    model_name = os.getenv("GEMINI_FAST_TASK_MODEL", "gemini-2.0-flash")
    temperature = float(os.getenv("GEMINI_FAST_TEMP", "0.4"))
    max_tokens = int(os.getenv("GEMINI_FAST_MAX_TOKENS", "2048"))
    response_schema = None

  cache_key = f"{model_name}:{temperature}:{max_tokens}:{bool(response_schema)}"
  if cache_key in _MODELS:
    return _MODELS[cache_key], model_name

  generation_config = {
    "temperature": temperature,
    "max_output_tokens": max_tokens,
    "response_mime_type": "application/json",
  }
  if response_schema:
    generation_config["response_schema"] = response_schema
  
  model = genai.GenerativeModel(model_name, generation_config=generation_config)
  _MODELS[cache_key] = model
  return model, model_name


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
  def decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
      last_exception = None
      for attempt in range(max_retries):
        try:
          return await func(*args, **kwargs)
        except Exception as exc:
          last_exception = exc
          if attempt == max_retries - 1:
            break
          
          delay = base_delay * (2 ** attempt)
          logger.warning(
            "Gemini call failed (attempt %d/%d): %s. Retrying in %.2fs...",
            attempt + 1,
            max_retries,
            str(exc),
            delay,
          )
          await asyncio.sleep(delay)
      
      if last_exception:
        raise last_exception
    return wrapper
  return decorator


def generate_text(prompt: str, task_type: str = "default") -> dict[str, str]:
  """
  Synchronous wrapper for text generation (legacy support).
  """
  try:
    return asyncio.run(generate_text_async(prompt, task_type))
  except RuntimeError:
    # Handle case where event loop is already running
    model, model_name = _get_model_for_task(task_type)
    response = model.generate_content(prompt)
    return _process_response(response, model_name)


@retry_with_backoff(
  max_retries=int(os.getenv("GEMINI_RETRY_MAX_ATTEMPTS", "3")),
  base_delay=float(os.getenv("GEMINI_RETRY_BASE_DELAY", "1.0"))
)
async def generate_text_async(prompt: str, task_type: str = "default") -> dict[str, str]:
  """
  Generate text from Gemini using the configured model for the specific task.
  Supports async execution, retries, and observability.
  """
  model, model_name = _get_model_for_task(task_type)
  timeout = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))
  
  # Only use Langfuse observability if a current observation exists
  has_obs = False
  if HAS_LANGFUSE and os.getenv("LANGFUSE_PUBLIC_KEY"):
    getter = getattr(langfuse_context, "get_current_observation", None)
    if getter and getter() is not None:
      has_obs = True

  if has_obs:
    return await _generate_with_observability(model, model_name, prompt, timeout)
  
  # Standard execution without observability
  response = await model.generate_content_async(
    prompt,
    request_options={"timeout": timeout}
  )
  return _process_response(response, model_name)


async def _generate_with_observability(model, model_name, prompt, timeout):
  # We manually wrap this to avoid issues with the decorator if Langfuse isn't set up
  # but HAS_LANGFUSE is True (e.g. package installed but no keys)
  try:
    langfuse_context.update_current_observation(
      input=prompt[:1000],
      model=model_name,
      metadata={"task_type": "generation", "timeout": timeout}
    )
    
    start_time = time.perf_counter()
    response = await model.generate_content_async(
      prompt, 
      request_options={"timeout": timeout}
    )
    duration = time.perf_counter() - start_time
    
    usage = {}
    if hasattr(response, "usage_metadata"):
      usage = {
        "input_tokens": response.usage_metadata.prompt_token_count,
        "output_tokens": response.usage_metadata.candidates_token_count,
        "total_tokens": response.usage_metadata.total_token_count,
      }
      
    langfuse_context.update_current_observation(
      output=response.text[:1000] if hasattr(response, "text") else "No text",
      usage=usage,
      metadata={"latency": duration}
    )
    return _process_response(response, model_name)
  except Exception as e:
    langfuse_context.update_current_observation(level="ERROR", status_message=str(e))
    raise


def _process_response(response, model_name) -> dict[str, str]:
  try:
    text = response.text
  except Exception:
    text = None

  finish_reason = None
  try:
    if hasattr(response, "candidates") and response.candidates:
      finish_reason = response.candidates[0].finish_reason
  except Exception:
    finish_reason = None

  if not text and hasattr(response, "candidates"):
    parts = []
    for candidate in response.candidates:
      content = getattr(candidate, "content", None)
      if content and hasattr(content, "parts"):
        parts.extend(getattr(part, "text", "") for part in content.parts if hasattr(part, "text"))
    text = "\n".join(part for part in parts if part).strip()
    
  if not text:
    # Log detailed info for debugging
    safety_ratings = "Unknown"
    try:
        if hasattr(response, "candidates") and response.candidates:
            safety_ratings = str(response.candidates[0].safety_ratings)
        elif hasattr(response, "prompt_feedback"):
            safety_ratings = str(response.prompt_feedback)
    except Exception:
        pass
        
    logger.error(f"Gemini empty response. Finish reason: {finish_reason}. Safety: {safety_ratings}")
    raise GeminiClientError(f"Gemini returned an empty response. Reason: {finish_reason}")
  # Strict JSON validation: raise if invalid after a single salvage attempt.
  try:
    json.loads(text)
  except Exception as exc:
    import re

    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
      candidate = match.group(0)
      try:
        json.loads(candidate)
        text = candidate
      except Exception:
        raise GeminiClientError(
          f"Gemini returned non-JSON response (finish_reason={finish_reason}): {exc}"
        ) from exc
    else:
      raise GeminiClientError(
        f"Gemini returned non-JSON response (finish_reason={finish_reason}): {exc}"
      ) from exc

  return {"text": text, "model": model_name, "finish_reason": finish_reason}
