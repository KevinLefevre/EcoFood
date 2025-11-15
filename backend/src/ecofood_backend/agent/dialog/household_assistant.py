from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas import AssistantMessageResponse, MemberCreate
from ...services import households as household_service


@dataclass
class AssistantState:
  stage: str = "ask_name"
  name: Optional[str] = None
  role: str = "Adult"
  allergens: List[str] = field(default_factory=list)
  likes: List[str] = field(default_factory=list)


class HouseholdAssistant:
  """
  Simple dialog agent that guides users through adding a household member.
  """

  def __init__(self) -> None:
    self.sessions: Dict[str, AssistantState] = {}

  async def handle_message(
    self,
    *,
    db: AsyncSession,
    household_id: int,
    session_id: str,
    user_message: Optional[str],
  ) -> AssistantMessageResponse:
    state = self.sessions.get(session_id)
    if state is None:
      state = AssistantState()
      self.sessions[session_id] = state
      return AssistantMessageResponse(
        session_id=session_id,
        stage=state.stage,
        agent_message="Hi! Let's add someone new. What's their name?",
        completed=False,
      )

    message = (user_message or "").strip()

    if state.stage == "ask_name":
      if not message:
        return AssistantMessageResponse(
          session_id=session_id,
          stage=state.stage,
          agent_message="I didn't catch the name. Who are we adding?",
          completed=False,
        )
      state.name = message
      state.stage = "ask_role"
      return AssistantMessageResponse(
        session_id=session_id,
        stage=state.stage,
        agent_message=f"Great! What role does {state.name} have? (Adult, Child, Guest, ...)",
        completed=False,
      )

    if state.stage == "ask_role":
      state.role = message or "Adult"
      state.stage = "ask_allergens"
      return AssistantMessageResponse(
        session_id=session_id,
        stage=state.stage,
        agent_message="Any allergens to note? You can list several separated by commas, or say 'none'.",
        completed=False,
      )

    if state.stage == "ask_allergens":
      if message.lower() != "none":
        state.allergens = [label.strip() for label in message.split(",") if label.strip()]
      state.stage = "ask_likes"
      return AssistantMessageResponse(
        session_id=session_id,
        stage=state.stage,
        agent_message="What foods or cuisines do they enjoy? (comma separated)",
        completed=False,
      )

    if state.stage == "ask_likes":
      if message:
        state.likes = [label.strip() for label in message.split(",") if label.strip()]
      state.stage = "confirm"
      summary = self._summarize(state)
      return AssistantMessageResponse(
        session_id=session_id,
        stage=state.stage,
        agent_message=f"Here's what I gathered:\n{summary}\nType 'yes' to save or 'start over' to redo.",
        completed=False,
      )

    if state.stage == "confirm":
      if message.lower() in {"start over", "restart"}:
        self.sessions[session_id] = AssistantState()
        return AssistantMessageResponse(
          session_id=session_id,
          stage="ask_name",
          agent_message="No problem. Let's start again. What's the name?",
          completed=False,
        )
      if message.lower() not in {"yes", "y"}:
        return AssistantMessageResponse(
          session_id=session_id,
          stage=state.stage,
          agent_message="Please confirm by typing 'yes', or say 'start over' to redo.",
          completed=False,
        )

      member_payload = MemberCreate(
        name=state.name or "Unnamed",
        role=state.role or "Adult",
        allergens=state.allergens,
        likes=state.likes,
      )
      member = await household_service.create_member(db, household_id, member_payload)
      del self.sessions[session_id]
      return AssistantMessageResponse(
        session_id=session_id,
        stage="completed",
        agent_message=f"Saved {member.name}! They're now part of the household.",
        completed=True,
        member=member,
      )

    # Fallback
    del self.sessions[session_id]
    return AssistantMessageResponse(
      session_id=session_id,
      stage="ask_name",
      agent_message="Let's restart. What's the name?",
      completed=False,
    )

  def _summarize(self, state: AssistantState) -> str:
    allergens = ", ".join(state.allergens) if state.allergens else "None"
    likes = ", ".join(state.likes) if state.likes else "Not specified"
    return (
      f"- Name: {state.name}\n"
      f"- Role: {state.role}\n"
      f"- Allergens: {allergens}\n"
      f"- Preferences: {likes}"
    )
