"""
Agent-to-Agent (A2A) orchestration utilities for EcoFood.

This package currently exposes:
- Context helpers for storing intermediate artifacts.
- Specialized agents (household profiler, meal architect, reviewers).
- Workflow orchestrators that coordinate sequential and parallel phases.
"""

from .workflow import MealPlanningWorkflow

__all__ = ["MealPlanningWorkflow"]

