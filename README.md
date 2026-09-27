# AI Agents

This repository contains multiple independent AI agents. Each agent is self-contained and can be developed and run independently.

## Agents

### 1. Library Chatbot Agent

A library assistant that helps students search books, check availability, get recommendations, and perform basic library operations.

**Location:** `library-chatbot-agent/`

**Tech:** React, Vite, Python, FastAPI

## Repository Structure

```text
AI-Agents/
└── library-chatbot-agent/
    ├── backend/
    ├── frontend/
    ├── .env.example
    ├── .gitignore
    └── README.md
```

## Adding New Agents

Each new agent should have its own folder containing its frontend, backend, dependencies, configuration, and documentation.

Each agent should be runnable independently without depending on another agent.
