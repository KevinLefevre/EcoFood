# Category 1: The Pitch (Problem, Solution, Value)

## The Problem
The environmental impact of our daily food choices is often invisible and hard to optimize. Furthermore, modern families struggle with the "what's for dinner?" cognitive load. Meal planning is often rigid, time-consuming, and disconnected from what's actually in the fridge, leading to significant household food waste and unnecessary grocery spending.

## The Solution
**EcoFood** is an agentic AI platform that acts as your personal executive chef and sustainability consultant. Our main goal is to **help people eat better with less CO2** and **minimize the computational footprint** of the AI itself.

Unlike static recipe apps, EcoFood orchestrates a team of specialized AI agents—from a "Meal Architect" to a "Carbon Estimator"—to generate dynamic, personalized meal plans. It intelligently uses up your leftovers, respects your dietary needs, and optimizes for the lowest carbon footprint, all while leveraging efficient, small models (Gemini Flash) to keep energy usage low.

## The Value
-   **Zero Waste**: Proactively suggests meals based on expiring pantry items.
-   **Sustainability**: Provides real-time carbon footprint scoring for every meal.
-   **Efficient AI**: Utilizes smaller, faster models (Gemini Flash) to reduce the environmental impact of inference.
-   **Personalization**: Learns from your feedback and adapts to complex household profiles (e.g., "Dad is vegan, kids hate mushrooms").
-   **Time Saving**: Automates the entire planning-to-shopping workflow.

# Core Concept & Value

## Central Idea: Agent-to-Agent (A2A) Collaboration
The core innovation of EcoFood is its **Agent-to-Agent (A2A)** architecture. Instead of relying on a single monolithic LLM prompt, we built a virtual kitchen staff where specialized agents collaborate:
1.  **Household Profiler**: Maintains a deep understanding of family preferences.
2.  **Meal Architect**: Designs the weekly structure using **Gemini 2.5 Pro**.
3.  **Pantry Reviewer**: Scans inventory to inject "use-it-up" suggestions.
4.  **Carbon Estimator**: Calculates the environmental cost of ingredients.
5.  **Chef Curator**: Adds culinary flair and plating tips.

## Innovation
-   **Real-Time Streaming**: The UI visualizes the agents' "thought process" in real-time, building trust and engagement.
-   **Context Compaction**: We implemented a novel memory system that summarizes long conversations, allowing the AI to retain context over weeks of planning without hitting token limits.
-   **Model Context Protocol (MCP)**: A modular tool registry allows agents to seamlessly interface with calendars, databases, and external APIs.

# Writeup

## Technical Architecture
-   **AI Engine**: Google Gemini (Flash 2.0 & Pro 2.5) via a custom resilient client.
-   **Backend**: Python/FastAPI with a directed-graph workflow engine for agent orchestration.
-   **Frontend**: Next.js with Server-Sent Events (SSE) for live agent feedback.
-   **Infrastructure**: Containerized on **Google Kubernetes Engine (GKE)** for scalability.
-   **Observability**: Integrated **Langfuse** for tracing agent reasoning and cost.

## Dev Journey
I dedicated two full weeks of nights and weekends to this project, working after my regular job to really showcase what I've learned. I started the development in VSCode, but then shifted to Google Antigravity. As the Technical Director at StarClay, I was already deeply engaged with MCP, especially for enterprise integration. But I wanted to contribute to something that makes sense ecologically. As a father of a 2-year-old, I often struggle to find interesting meals to cook with my wife and, more importantly, to plan the ingredients we need to buy. My goal was clear: save time and optimize my personal life, while also making a positive impact by eating better, more responsibly, and avoiding waste.
