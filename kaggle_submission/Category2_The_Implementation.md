# Category 2: The Implementation (Architecture, Code)

## Architecture Overview
EcoFood is built on a modern, scalable microservices-ready architecture designed for resilience and observability.

-   **Backend**: Python **FastAPI** application serving as the agent orchestration layer. It uses **SQLAlchemy (Async)** with **PostgreSQL** for persistence.
-   **Frontend**: **Next.js** (React) application providing a real-time reactive UI. It connects to the backend via **Server-Sent Events (SSE)** to stream agent activities and partial updates to the user.
-   **Infrastructure**: The application was developed to run seamlessly on **Docker Desktop**, with a complete optional deployment configuration for **Google Kubernetes Engine (GKE)** for production scalability.

## AI Integration & Agents
The core of EcoFood is not a single LLM call, but a **Directed Acyclic Graph (DAG)** of specialized agents. We use **Google Gemini** models tailored to each specific task:

-   **Gemini 2.5 Pro**: Used by the **Meal Architect** for complex reasoning, creative menu design, and adhering to strict dietary constraints.
-   **Gemini 2.0 Flash**: Used by the **Summarizer**, **Pantry Reviewer**, and **Carbon Estimator** for high-speed, low-latency tasks where speed is critical.

## Key Concepts Applied
For a detailed breakdown of all features and their implementations, please refer to [FEATURES.md](../FEATURES.md).


## Code Quality
The codebase prioritizes maintainability and correctness:
-   **Type Safety**: Fully typed Python code with **Pydantic** models for strict schema validation of all LLM outputs.
-   **Documentation**: Comprehensive docstrings and comments explaining architectural decisions and agent behaviors.
-   **Observability**: Deep integration with **Langfuse** to trace every agent step, monitor latency, and track token usage/costs in real-time.
