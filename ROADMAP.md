# EcoFood Roadmap

This roadmap tracks how the capstone features from `FEATURES.md` will be implemented over time.

It is organized into three sections:
- **BACKLOG** – Detailed tasks that are not started yet.
- **IN-PROGRESS** – Tasks currently being worked on.
- **FINISH** – Tasks that are done.

Move items between sections as you work.

---

## BACKLOG

### 1. Foundation & Architecture

- [ ] Finalize high-level architecture document (frontend ↔ backend ↔ agents ↔ tools ↔ database).
- [ ] Define service boundaries: API layer, agent orchestration layer, data-access layer.
- [ ] Choose database schema migration tool (e.g. Alembic) and basic conventions.
- [ ] Define environment layout: `local`, `dev`, `prod` and how `.env` and Docker configs map to them.
- [ ] Specify security baseline (API auth approach, rate limiting strategy, secret handling).

### 2. Core Domain & Database Model

- [ ] Design initial ERD for:
  - [ ] Household
  - [ ] HouseholdMember
  - [ ] Preference (cuisine, taste profile, dislikes)
  - [ ] Allergen / DietaryRestriction
  - [ ] PantryItem (ingredients available at home)
  - [ ] Recipe (internal or external reference)
  - [ ] Meal (recipe + metadata)
  - [ ] MealPlan (weekly / daily plan)
- [ ] Create SQL migrations to create baseline tables for the above.
- [ ] Implement database connection handling in the backend (FastAPI + async DB client or ORM).
- [ ] Implement basic CRUD for Households (create, read, update, archive).
- [ ] Implement CRUD for members and their allergens/preferences.
- [ ] Implement CRUD for pantry items (inventory, quantities, expiration).
- [ ] Implement endpoints to get and update a weekly MealPlan per household.

### 3. Backend API – HTTP Interface

- [ ] Define API contract (OpenAPI-first or FastAPI route-first) for:
  - [ ] Household & profile management.
  - [ ] Preferences & allergens management.
  - [ ] Pantry and leftovers.
  - [ ] Weekly meal plan retrieval and update.
  - [ ] “Ask the planner” endpoints (agents proposing menus).
- [ ] Implement health and readiness endpoints (e.g. `/health`, `/ready`).
- [ ] Add basic error handling and error response schema (standard error envelope).
- [ ] Add pagination / filtering for large collections (e.g. recipes, pantry items).

### 4. Multi-Agent System & Orchestration

- [ ] Define agent types and responsibilities:
  - [ ] Household profiler agent (builds a structured profile from user input).
  - [ ] Meal plan architect agent (creates weekly plan candidates).
  - [ ] Nutrition coach agent (scores and adjusts plans for balance).
  - [ ] Pantry optimizer agent (tries to use existing ingredients).
  - [ ] Diversity agent (ensures variety across weeks).
- [ ] Decide on orchestration model:
  - [ ] Sequential flows (e.g. profile → initial plan → nutrition adjustment → diversity adjustment).
  - [ ] Parallel agents for generating alternative plans in parallel.
  - [ ] Loop agents for iterative refinement until constraints are satisfied.
- [ ] Implement an orchestration engine to coordinate agent calls and maintain shared state.
- [ ] Implement a standard agent interface (input schema, output schema, metadata).
- [ ] Add a simple in-memory agent registry for experimentation.
- [ ] Implement at least one loop-based refinement workflow for weekly planning.

### 5. Gemini & External Tooling Integration

- [ ] Add Gemini client wrapper with:
  - [ ] Configurable model name and temperature.
  - [ ] Request/response logging hooks (even if Langfuse is off for now).
  - [ ] Retry and timeout strategy.
- [ ] Define prompt templates for:
  - [ ] Household profiling.
  - [ ] Weekly meal plan generation.
  - [ ] Plan critique and improvement (nutrition, diversity, waste reduction).
- [ ] Implement OpenAI-style / tool-calling style schemas if needed for structured outputs.
- [ ] Implement external recipe API integration (OpenAPI tool):
  - [ ] Choose a recipe API and define an OpenAPI spec or typed client.
  - [ ] Create a tool wrapper that agents can call for recipes.
- [ ] Implement an optional nutrition API tool (for macro / micro nutrient estimates).
- [ ] Implement “long-running operations” for heavy planning:
  - [ ] Async job model (job ID, status, result location).
  - [ ] Start job endpoint for “generate weekly plan”.
  - [ ] Poll job status endpoint.

### 6. Sessions, Memory & Context Engineering

- [ ] Implement session service (e.g. `InMemorySessionService`) for:
  - [ ] Tracking user interactions during a planning session.
  - [ ] Storing agent messages and intermediate results.
- [ ] Design structure for long-term memory (e.g. Memory Bank):
  - [ ] What gets stored: accepted meal plans, strong likes/dislikes, repeated rejections.
  - [ ] How to index and retrieve relevant memories for new planning requests.
- [ ] Implement long-term memory storage using the database or dedicated KV store.
- [ ] Implement retrieval strategy to build condensed context for agents.
- [ ] Implement context compaction:
  - [ ] Heuristics for dropping or summarizing older conversation segments.
  - [ ] Summarization prompts to compress history while keeping constraints.
- [ ] Add tests (or scripted checks) to ensure context windows stay within model limits.

### 7. Web App UI – Core Experience

- [ ] Implement global layout and navigation shell:
  - [ ] Top navigation (EcoFood brand, household selector).
  - [ ] Main content area with responsive grids.
  - [ ] Futuristic theme (gradients, glassmorphism, subtle neon accents).
- [ ] Implement onboarding flow:
  - [ ] Welcome screen explaining EcoFood’s value.
  - [ ] Step-by-step forms to collect household members, allergens, preferences.
  - [ ] Final summary screen and CTA to “Generate my first plan”.
- [ ] Implement calendar view:
  - [ ] Weekly grid with meals for breakfast / lunch / dinner.
  - [ ] Responsive layout for desktop, tablet, mobile.
  - [ ] Basic interactions (view meal details, edit, delete).
- [ ] Implement “generate plan” flow:
  - [ ] UI controls for planning horizon (1 week, multiple weeks).
  - [ ] Button to trigger backend agent orchestration.
  - [ ] Loading / progress states while agents run.
  - [ ] Display of results with clear labels (e.g. “AI suggestion”, “plan v2 after nutrition check”).
- [ ] Implement plan editing tools:
  - [ ] Swap a meal with alternatives.
  - [ ] Lock certain meals when regenerating.
  - [ ] Mark meals as favorite / avoid.

### 8. Web App UI – Advanced Features

- [ ] Implement pantry management UI:
  - [ ] List of items with quantities and expiration.
  - [ ] Quick add / edit / delete.
  - [ ] Highlight items that will soon expire.
- [ ] Implement “exploration mode” UI:
  - [ ] Toggle to allow more adventurous suggestions.
  - [ ] Controls for cuisines / difficulty level.
- [ ] Implement “nutritional balance coach” UI:
  - [ ] Weekly score visualization (e.g. radar chart or bar chart).
  - [ ] Simple explanations and suggestions for improvement.
- [ ] Implement “budget & season aware planning” settings:
  - [ ] Monthly budget input.
  - [ ] Region / season selector.
  - [ ] Toggle to prioritize seasonal ingredients.

### 9. Observability, Logging & Metrics

- [ ] Define logging strategy (structure, levels, redaction of sensitive data).
- [ ] Add structured logging in the backend (per request, per agent run).
- [ ] Add basic metrics counters/timers (requests, agent runs, failures).
- [ ] Prepare hooks for Langfuse or similar tool:
  - [ ] Centralized place to send traces/spans when enabled.
  - [ ] Configuration flags to turn observability on/off via env vars.

### 10. Testing, Evaluation & Quality

- [ ] Add unit tests for core backend services (domain logic, DB access, agent orchestration).
- [ ] Add API tests for key endpoints (happy paths + error cases).
- [ ] Add simple frontend tests (e.g. key pages rendering, basic flows).
- [ ] Design agent evaluation harness:
  - [ ] Define metrics (user satisfaction proxy, nutritional scores, diversity).
  - [ ] Create a small benchmark set of “household profiles” and expectations.
  - [ ] Script to run agents against the benchmark and capture outputs.
- [ ] Add basic CI pipeline (lint, tests, type-check).

### 11. Deployment & Operations

- [ ] Finalize Docker images for backend and frontend.
- [ ] Add environment-specific configuration for database and secrets.
- [ ] Decide on hosting platform(s) for:
  - [ ] Backend (e.g. container platform).
  - [ ] Frontend (e.g. Vercel or container).
- [ ] Implement zero-downtime deployment strategy for backend.
- [ ] Document operational runbook (restart procedures, log locations, common issues).

---

## IN-PROGRESS

- [ ] Pantry inventory service & UI
  - [ ] Persist pantry items (quantity, expiry) and expose CRUD endpoints.
  - [ ] Replace placeholder pantry callouts in the Calendar with live data.
  - [ ] Feed pantry context into the planner alongside kitchen tools.
- [ ] Meal planning UX polish
  - [x] Add streaming/task feedback when agents are running (plan jobs, SSE overlay).
  - [x] Give users abort/retry controls with clearer day-by-day status updates.
  - [ ] Surface final agent context (nutrition scores, pantry hints) in the Calendar tab.
  - [ ] Persist job timeline segments per day (with job IDs) for deep-dive diagnostics.
  - [ ] Allow editing of plan notes/flags after generation.
- [ ] Recipe fidelity & variety enhancements
  - [ ] Integrate a real recipe datasource or LLM-powered generator to expand beyond the static catalogue.
  - [ ] Add repetition-avoidance logic across weeks (tracking past plans) and introduce cuisine/budget knobs.
  - [ ] Expose planner controls for “adventurous mode”, “kid friendly”, “speed run” etc.
  - [ ] Expand nutrition tooling for macros/micros per recipe and highlight gaps in the weekly view.
- [ ] Export & automation
  - [ ] Let users trigger “export groceries” for CSV/PDF as well as text, and push to shopping-list apps.
  - [ ] Add calendar export (ICS) download UI with per-slot toggles.

## FINISH

- [x] Initial multi-tab web UI:
  - [x] Futuristic landing shell with gradients and glassmorphism.
  - [x] Top navigation tabs for Calendar, Household, and Settings.
- [x] Household & member management:
  - [x] CRUD for households, members, allergens, preferences.
  - [x] Assistant-guided member intake chat.
  - [x] Kitchen inventory card with default cookware seeds and per-tool quantity controls.
  - [x] Meal participation editor with advanced day-by-day schedules.
- [x] Meal planning workflow (v1):
  - [x] FastAPI meal-plan router (list, get, create, delete, entry patch).
  - [x] Multi-agent orchestration (household profiler, meal architect, nutrition reviewer, pantry reviewer, plan synthesizer).
  - [x] CORS-enabled backend with structured schemas for recipes, steps, prep/cook times, calories.
- [x] Calendar experience:
  - [x] Weekly grid (breakfast/lunch/dinner) with responsive layout.
  - [x] Meal viewer modal showing ingredients, steps, cooking hints, and editing entry chat context.
  - [x] Attendee/guest management per slot tied to household schedules.
- [x] Session timeline & agent transparency:
  - [x] Detailed timeline cards describing each agent, inputs, outputs, and action schema.
  - [x] Session viewer modal with scrollable history and metadata.
- [x] Shopping export:
  - [x] Gather grouped shopping list from plan synthesis and expose “Export groceries” modal.
  - [x] Copy-to-clipboard and TXT download actions with grouped sections (produce, grains, protein, etc.).
- [x] Database bootstrap helpers:
  - [x] Automatic column backfill for new recipe attributes, kitchen tools, and meal schedules when running without migrations.
- [x] Gemini-driven chef planning:
  - [x] Gemini client wrapper with configurable model + env-controlled API key.
  - [x] `chef.plan-week` tool that prompts Gemini for full-week menus (21 meals, structured recipes).
  - [x] Meal Architect wired to Gemini outputs (no static fallback), surfacing prompts/raw text for debugging.
  - [x] Chef Curator action schema + timeline visibility so users understand the LLM stage.
  - [x] Optimized day-based generation (3 meals/call) to reduce latency and rate-limit errors.
- [x] Loop planning jobs & diagnostics:
  - [x] `/plan-jobs` endpoint launching async planning runs with job metadata stored in Postgres.
  - [x] Day-by-day loop agent runner with Gemini fallback logic plus structured events per day.
  - [x] SSE event stream powering the planning overlay, incremental calendar updates, and completion callbacks.
  - [x] Job cancellation endpoint + frontend abort button to stop runs mid-week.
- [x] MCP calendar export:
  - [x] Minimal in-process MCP server + host wiring the `calendar.export-ics` tool via `mcp_sdk`.
  - [x] Plan synthesis agent now calls the MCP client to build ICS files surfaced in the UI download button.
- [x] Calendar tab (UI-only prototype):
  - [x] Weekly grid layout with breakfast / lunch / dinner slots.
  - [x] Static example meals and visual highlights for pantry-aware / balanced options.
- [x] Household tab (UI-only prototype):
  - [x] Local-only management of household members, allergens, and taste preferences.
  - [x] Summary of profiles and tracked allergens.
- [x] Settings tab for database debug tools:
  - [x] Buttons to trigger full DB reset and per-table reset (wired to stub backend endpoints).
  - [x] Status panel showing responses from the backend admin endpoints.
- [x] Unified Docker dev container:
  - [x] Single `app` service running both FastAPI backend and Next.js web app.
  - [x] Ports exposed for API (`8000`) and web UI (`3000`) from the same container.
- [x] Initial A2A workflow scaffolding:
  - [x] Sequential agents (household profiler, meal architect, synthesis).
  - [x] Parallel review agents (nutrition, pantry) coordinated in the same run.
  - [x] `/plans/generate` endpoint returning timeline, final plan, shopping list, and calendar export.
- [x] Household management experience:
  - [x] SQLAlchemy models + CRUD endpoints for households and members stored in Postgres.
  - [x] Frontend Household tab wired to backend (empty-by-default, add/remove persisted members).
  - [x] Dialog assistant endpoint + UI modal that captures allergens/preferences and saves to SQL.
- [x] Kitchen tooling awareness:
  - [x] KitchenTool model/CRUD with default cookware inventory seeded per household.
  - [x] Household UI for adjusting tool counts, adding custom gear, and syncing to backend.
  - [x] Meal planner agents incorporate kitchen tools to avoid suggesting unavailable cookware.
- [x] Week lifecycle management:
  - [x] Backend `DELETE /households/{id}/plans/{week}` endpoint to reset the calendar.
  - [x] Calendar UI “Reset week” control tied to that endpoint with status messaging.
