# AI Agents

This repository contains multiple independent AI agents. Each project is organized in its own folder and can be developed and run independently.

## Agents

### 1. Library Chatbot Agent

A library assistant that helps students search for books, check availability, get recommendations, and perform basic library operations.

**Location:** `library-chatbot-agent/`

**Tech Stack:** React, Vite, Python, FastAPI

---

### 2. Travel Agent

An AI-powered travel assistant that helps users plan trips and provides travel-related recommendations based on their requirements.

**Location:** `travel-agent/`

**Tech Stack:** Python, Flask, HTML, CSS, JavaScript

---

### 3. Study Agent

An AI study assistant designed to help students with study planning, learning prompts, and structured study support.

**Location:** `study-agent/`

**Tech Stack:** Python, Flask

---

### 4. AI Movie

An AI-generated mini-movie project demonstrating the use of AI for creating cinematic visual content.

**Location:** `ai-movie/`

**Contents:**

* Generated AI video
* Prompt screenshot
* Supporting image

---

## Repository Structure

```text
AI-Agents/
├── ai-movie/
├── library-chatbot-agent/
├── study-agent/
├── travel-agent/
└── README.md
```

## Project Structure Principles

* Each agent is maintained in its own folder.
* Agents are designed to be independent and isolated.
* Each agent maintains its own frontend, backend, dependencies, configuration, and documentation where applicable.
* Environment variables are kept separate using individual `.env.example` files.
* Agents should be runnable independently without depending on another agent.
* New agents can be added by creating a new folder without affecting existing projects.

## Adding a New Agent

To add a new AI agent, create a separate folder containing its own:

* Frontend
* Backend
* Dependencies
* AI logic and prompts
* Configuration
* Environment configuration
* README/documentation

This keeps the repository modular and makes each project independently maintainable.
