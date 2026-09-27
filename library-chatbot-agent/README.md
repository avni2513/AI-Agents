# Library Chatbot Agent

A self-contained library assistant that helps students find books, check availability, get book information, and perform basic library operations.

## Features

* Book search and availability
* Author and genre search
* Borrow and return books
* Book recommendations
* Library information and FAQs

## Structure

```text
library-chatbot-agent/
├── backend/
│   ├── chatbot.py
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
├── .env.example
├── .gitignore
└── README.md
```

## Tech Stack

* **Frontend:** React + Vite
* **Backend:** Python + FastAPI
* **Chatbot:** Python

## Run

### Backend

```bash
cd backend
pip3 install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

Backend: `http://127.0.0.1:8000`

## Independence

This agent is completely self-contained with its own frontend, backend, dependencies, API routes, chatbot logic, configuration, and documentation.
