from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ecofood_backend.agent.tools.mcp.chef import chef_chat_analysis, chef_execute_update
from ecofood_backend.database import get_session
from ecofood_backend.services.memory_service import memory_service
from ecofood_backend.services.session_service import session_service

router = APIRouter(prefix="/api/planner", tags=["planner"])


class ChatContext(BaseModel):
    day: str
    slot: str
    current_meal: Dict[str, Any]


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]]
    context: ChatContext
    session_id: Optional[str] = None
    household_id: Optional[int] = None


class ChatResponse(BaseModel):
    message: str
    ready: bool
    summary: Optional[str] = None


class ExecuteRequest(BaseModel):
    history: List[Dict[str, str]]
    context: ChatContext
    session_id: Optional[str] = None
    household_id: Optional[int] = None


class ExecuteResponse(BaseModel):
    updated_meal: Dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
async def chat_with_planner(
    request: ChatRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Analyzes the user's message and returns an agent response.
    Checks if the agent is ready to execute the update.
    """
    try:
        chat_history = request.history
        memories = []
        session = None

        if request.session_id:
            session = await session_service.get_session(db, request.session_id)
            if session:
                # Save user message
                await session_service.add_message(db, session.id, "user", request.message)
                
                # Trigger compaction check
                # We do this asynchronously or just await it (it's fast enough usually)
                await session_service.check_and_compact(db, session.id)

                # Get full history
                history_objs = await session_service.get_history(db, session.id)
                # Convert to list of dicts for chef
                chat_history = [
                    {"role": m.role, "content": m.content} for m in history_objs
                ]
                
                # Get summary if available
                if session.summary:
                    # We can prepend it to memories or pass it explicitly
                    # Let's pass it explicitly to chef_chat_analysis
                    pass

                # Get memories
                if request.household_id:
                    memory_objs = await memory_service.get_memories(
                        db, request.household_id
                    )
                    memories = [m.value for m in memory_objs]

        result = await chef_chat_analysis(
            current_plan=request.context.current_meal,
            chat_history=chat_history,
            user_message=request.message,
            memories=memories,
            summary=session.summary if session else None,
        )

        if session:
            # Save agent response
            await session_service.add_message(db, session.id, "model", result["message"])

        return ChatResponse(
            message=result["message"],
            ready=result["ready"],
            summary=result.get("summary"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecuteResponse)
async def execute_meal_update(
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Executes the meal update based on the conversation history.
    """
    try:
        chat_history = request.history
        memories = []

        if request.session_id:
            session = await session_service.get_session(db, request.session_id)
            if session:
                # Get full history
                history_objs = await session_service.get_history(db, session.id)
                chat_history = [
                    {"role": m.role, "content": m.content} for m in history_objs
                ]

                # Get memories
                if request.household_id:
                    memory_objs = await memory_service.get_memories(
                        db, request.household_id
                    )
                    memories = [m.value for m in memory_objs]

        updated_meal = await chef_execute_update(
            current_plan=request.context.current_meal,
            chat_history=chat_history,
            memories=memories,
        )
        return ExecuteResponse(updated_meal=updated_meal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
