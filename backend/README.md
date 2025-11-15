# EcoFood Backend

This package contains the FastAPI-based backend for EcoFood.

It exposes:
- Health endpoints (e.g. `/health`).
- Admin endpoints for development-only database tools (e.g. `/admin/reset-db` and `/admin/reset-table/{table_name}` stubs).

The backend is designed to host:
- The multi-agent orchestration layer.
- Gemini and external tool integrations.
- Persistence for households, preferences, allergens, and meal plans.

