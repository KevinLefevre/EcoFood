from __future__ import annotations

import logging
from typing import Any, Dict, List

from ...clients.gemini import generate_text_async

logger = logging.getLogger(__name__)


async def summarize_chat(messages: List[Dict[str, str]]) -> str:
  """
  Summarizes a list of chat messages into a concise context string.
  """
  if not messages:
    return ""

  conversation_text = "\n".join(
    f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in messages
  )

  prompt = f"""
  Summarize the following conversation between a user and an AI meal planner.
  Focus on key decisions, user preferences, and specific changes requested to the meal plan.
  Ignore casual pleasantries.
  Keep the summary concise (under 200 words).

  Conversation:
  {conversation_text}

  Summary:
  """

  try:
    # Use "default" task type for fast summarization
    response = await generate_text_async(prompt, task_type="default")
    return response.get("text", "").strip()
  except Exception as e:
    logger.error(f"Summarization failed: {e}")
    return "Error generating summary."


TOOLS: Dict[str, Any] = {
  "summarizer.summarize-chat": summarize_chat,
}
