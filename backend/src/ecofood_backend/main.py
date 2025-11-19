import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import households as households_router
from .routers import meal_plans as meal_plans_router
from .routers import plan_jobs as plan_jobs_router


def create_app() -> FastAPI:
  app = FastAPI(title="EcoFood Backend", version="0.1.0")

  allowed_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
  app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  @app.on_event("startup")
  async def startup_event() -> None:
    await init_db()

  @app.get("/health", tags=["system"])
  async def health() -> dict[str, str]:
    return {"status": "ok"}

  @app.post("/admin/reset-db", tags=["admin"])
  async def reset_db() -> dict[str, str]:
    """
    Stub endpoint for dropping and recreating all core tables.

    Later this will trigger real migrations / truncations; for now it
    only confirms that the wiring between the web UI and backend works.
    """

    return {"status": "not_implemented", "scope": "database"}

  @app.post("/admin/reset-table/{table_name}", tags=["admin"])
  async def reset_table(table_name: str) -> dict[str, str]:
    """
    Stub endpoint for recreating a single table by name.

    The real implementation will run per-table operations to help debug
    schema changes without wiping all data.
    """

    return {"status": "not_implemented", "scope": "table", "table": table_name}

  app.include_router(households_router.router)
  app.include_router(meal_plans_router.router)
  app.include_router(plan_jobs_router.router)

  return app


def run() -> None:
  import uvicorn

  uvicorn.run(
    "ecofood_backend.main:create_app",
    factory=True,
    host="0.0.0.0",
    port=8000,
    reload=True,
  )


if __name__ == "__main__":
  run()
