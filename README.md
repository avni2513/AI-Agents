# AI Agents

This repository contains multiple independent AI agents. Each project is organized in its own folder and can be developed and run independently.

## Agents

### 1. Library Chatbot Agent

A library assistant that helps students search for books, check availability, get recommendations, and perform basic library operations.

**Location:** `library-chatbot-agent/`

**Tech Stack:** React, Vite, Python, FastAPI

**Run:**

* Start the backend from `library-chatbot-agent/backend/`
* Start the frontend from `library-chatbot-agent/frontend/`

---

### 2. Travel Agent

An AI-powered travel assistant that helps users plan trips and provides travel-related recommendations based on their requirements.

**Location:** `travel-agent/`

**Tech Stack:** Python, Flask, HTML, CSS, JavaScript

**Run:**

* Enter the `travel-agent/` folder
* Follow the instructions in its README to start the application

---

### 3. Study Agent

An AI study assistant designed to help students with study planning, learning prompts, and structured study support.

**Location:** `study-agent/`

**Tech Stack:** Python, Flask

**Run:**

* Enter the `study-agent/` folder
* Follow the instructions in its README to start the application

---

### 4. AI Movie

An AI-generated mini-movie project demonstrating the use of AI for creating cinematic visual content. The folder contains the generated movie, supporting images, and prompt-related output.

**Location:** `ai-movie/`

**Contents:**

* Generated AI video
* Prompt screenshot
* Supporting image

---

## Repository Structure

```text
AI-Agents/
│
├── ai-movie/
│   ├── generated AI video
│   ├── prompt screenshot
│   └── supporting image
│
├── library-chatbot-agent/
│   ├── backend/
│   ├── frontend/
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
│
├── study-agent/
│   ├── backend/
│   ├── frontend/
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
│
├── travel-agent/
│   ├── backend/
│   ├── frontend/
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
│
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

## Agents

### 1. Library Chatbot Agent

A library assistant that helps students search for books, check availability, get recommendations, and perform basic library operations.

**Location:** `library-chatbot-agent/`

**Tech Stack:** React, Vite, Python, FastAPI

**Run:**

* Start the backend from `library-chatbot-agent/backend/`
* Start the frontend from `library-chatbot-agent/frontend/`

---

### 2. Travel Agent

An AI-powered travel assistant that helps users plan trips and provides travel-related recommendations based on their requirements.

**Location:** `travel-agent/`

**Tech Stack:** Python, Flask, HTML, CSS, JavaScript

**Run:**

* Enter the `travel-agent/` folder
* Follow the instructions in its README to start the application

---

### 3. Study Agent

An AI study assistant designed to help students with study planning, learning prompts, and structured study support.

**Location:** `study-agent/`

**Tech Stack:** Python, Flask

**Run:**

* Enter the `study-agent/` folder
* Follow the instructions in its README to start the application

---

### 4. AI Movie

An AI-generated mini-movie project demonstrating the use of AI for creating cinematic visual content. The folder contains the generated movie, supporting images, and prompt-related output.

**Location:** `ai-movie/`

**Contents:**

* Generated AI video
* Prompt screenshot
* Supporting image

---

## Repository Structure

```text
AI-Agents/
│
├── ai-movie/
│   ├── generated AI video
│   ├── prompt screenshot
│   └── supporting image
│
├── library-chatbot-agent/
│   ├── backend/
│   ├── frontend/
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
│
├── study-agent/
│   ├── backend/
│   ├── frontend/
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
│
├── travel-agent/
│   ├── backend/
│   ├── frontend/
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
│
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
