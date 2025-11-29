# Features for the Capstone Project

This document details the features implemented in the EcoFood project, including architectural decisions, specific agent implementations, and deployment strategies.

## 1. Agent-to-Agent (A2A) Orchestration
**Implementation**: `backend/src/ecofood_backend/agent/a2a/plan_runner.py`

The core of the application is an orchestration engine that manages a workflow of specialized agents. This allows for complex tasks (like weekly meal planning) to be broken down into smaller, manageable steps handled by expert agents.

-   **Workflow Engine**: The `MealPlanningWorkflow` class defines a directed graph of agents.
-   **Execution Modes**: Supports both `sequential` (dependent steps) and `parallel` (independent analysis) execution.

```python
# backend/src/ecofood_backend/agent/a2a/plan_runner.py
async def _execute_planning(job_id: int) -> None:
  workflow = MealPlanningWorkflow()
  # ... setup context ...
  await workflow.run(ctx)
```

### Implemented Agents
Defined in `backend/src/ecofood_backend/agent/a2a/agents.py`.

1.  **Household Profiler** (`sequential`, `rule-based`):
    -   **Role**: Condenses raw household member data (allergies, likes) into a structured profile string.
    -   **Implementation**: Deterministic logic; returns `model: "rule-based"`.
2.  **Meal Architect** (`sequential`, `gemini-2.5-pro`):
    -   **Role**: Uses an LLM to generate the initial weekly meal plan based on the profile.
    -   **Implementation**: Calls `chef.plan-week` tool.
3.  **Chef Curator** (`sequential`, `rule-based`):
    -   **Role**: Refines the raw LLM plan, adding structure and details.
4.  **Nutrition Reviewer** (`parallel`, `tool-based`):
    -   **Role**: Analyzes the nutritional balance of the proposed plan.
5.  **Pantry Reviewer** (`parallel`, `tool-based`):
    -   **Role**: Suggests how to use existing pantry items to reduce waste.
6.  **CO2 Estimator** (`parallel`, `tool-based`):
    -   **Role**: Estimates the carbon footprint of each meal.
    -   **Implementation**: Uses `carbon.estimate-meal` tool.
7.  **Plan Synthesizer** (`sequential`, `tool-based`):
    -   **Role**: Aggregates all reviews and the plan into a final result, generating a shopping list and calendar events.

## 2. Real-Time Streaming & UI Updates
**Implementation**: `apps/web/app/page.tsx` (Frontend) & `backend/src/ecofood_backend/services/plan_jobs.py` (Backend)

The UI provides immediate feedback as agents complete their tasks, rather than waiting for the entire workflow to finish.

-   **Mechanism**: Server-Sent Events (SSE) / Polling.
-   **Flow**:
    1.  Backend agents emit events (e.g., `plan.candidate`, `plan.review.carbon`) as they finish.
    2.  Frontend subscribes to the job stream.
    3.  The "Agent Timeline" component renders cards dynamically as events arrive.

## 3. Gemini Model Integration
**Implementation**: `backend/src/ecofood_backend/agent/clients/gemini.py`

The system leverages Google's Gemini models for intelligence.

-   **Models Used**:
    -   `gemini-2.0-flash`: For high-speed, low-latency tasks (e.g., initial planning).
    -   `gemini-2.5-pro`: For complex reasoning tasks (optional configuration).
-   **Resilience**: Custom `GeminiClient` handles rate limits (`429`) and retries automatically.
-   **Visibility**: The UI explicitly shows which model was used for each step (e.g., "Generated via gemini-2.0-flash" or "Rule-based").

## 4. Kubernetes Deployment (GKE)
**Implementation**: `GKE_deployment/` directory

The project includes a production-ready deployment configuration for Google Kubernetes Engine.

-   **Manifests**:
    -   `app.yaml`: Deploys the bundled Backend + Frontend container.
    -   `postgres.yaml`: StatefulSet for the database.
    -   `langfuse.yaml`: Observability stack.
-   **Automation**: `deploy.sh` script handles building the Docker image, pushing to Google Artifact Registry, and applying manifests to the cluster.

## 5. Observability
**Implementation**: Langfuse Integration

-   **Tracing**: Every agent step and LLM call is traced.
-   **Metrics**: Latency, token usage, and cost are tracked.
-   **Dashboard**: A self-hosted Langfuse instance runs alongside the application for deep inspection of agent behavior.

## 6. Interactive Planner Chat
**Implementation**: `backend/src/ecofood_backend/apis/chat_api.py`

Users can refine the generated plan through a conversational interface.

-   **Context-Aware**: The chat agent knows the current state of the meal plan.
-   **Tool Use**: The agent can execute updates (e.g., "Swap Monday's dinner for tacos") which are immediately reflected in the UI.

## 7. Sessions & Memory
**Implementation**: `backend/src/ecofood_backend/services/session_service.py` & `memory_service.py`

The system maintains state across interactions to provide a personalized experience.

-   **Session Management**:
    -   **Service**: `SessionService` handles chat history and context.
    -   **Storage**: Messages are stored in the database (`SessionMessage` table), allowing the agent to recall previous turns in the conversation.
-   **Long-Term Memory**:
    -   **Service**: `MemoryService` stores persistent facts about the household (e.g., "User dislikes spicy food").
    -   **Retrieval**: Relevant memories are injected into the agent's context during planning and chat, ensuring consistent preferences across different sessions.

## 8. Model Context Protocol (MCP)
**Implementation**: `backend/src/ecofood_backend/mcp/` & `agent/tools/mcp/registry.py`

The project implements the Model Context Protocol in two distinct ways:

1.  **Internal Registry (MCP-inspired)**:
    -   **Pattern**: Tools are grouped into namespaces (e.g., `chef`, `nutrition`) and lazily loaded via `registry.py`.
    -   **Purpose**: Provides a uniform interface for agents to access local capabilities.

2.  **Real MCP Architecture (Client-Host)**:
    -   **Implementation**: The **Calendar Export** feature uses the official `mcp-sdk`.
    -   **Components**:
        -   **Server** (`mcp/calendar_server.py`): Defines an `McpServer` that exposes the `calendar.export-ics` tool.
        -   **Host** (`mcp/host.py`): An `McpHost` instance that registers the server and creates a client.
        -   **Client**: The agent uses this client to call the tool, demonstrating a decoupled, protocol-compliant architecture that could easily be moved to a remote server.

## 9. Context Compaction
**Implementation**: `backend/src/ecofood_backend/services/session_service.py` & `agent/tools/mcp/summarizer.py`

To manage the LLM's context window effectively during long conversations:

-   **Automatic Summarization**: When a chat session exceeds a certain length (e.g., 10 messages), the system triggers a background summarization task.
-   **Summarizer Tool**: A specialized `summarizer.summarize-chat` tool uses a fast LLM (`gemini-2.0-flash`) to condense the conversation history into a concise summary.
-   **Context Injection**: This summary is stored in the `Session` table and injected into the prompt of subsequent agent calls, allowing the agent to retain context without re-processing the entire history.



