# AI Student Planner

> An intelligent, multi-agent study planning system that helps students manage their semester schedules using LLM-powered agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org/)

---

## Overview

**AI Student Planner** is a production-grade application that uses a **multi-agent architecture** to help students:
- Upload and parse course syllabi (PDF/DOCX)
- Generate personalized study schedules
- Chat with an AI assistant for planning advice
- Adapt plans based on weekly feedback
- Export schedules to Google Calendar/Outlook

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent System** | LangGraph-powered agents (Parser, Planner, Reflector, Memory, Calendar) |
| **Smart Fallback** | Groq API with automatic Ollama fallback for reliability |
| **Real-time Chat** | WebSocket-based chat interface with conversation history |
| **Plan Versioning** | Track changes to study plans over time |
| **Feedback Loop** | Weekly reflections automatically trigger plan adjustments |
| **Calendar Export** | Generate `.ics` files compatible with all major calendar apps |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js + Tailwind)                │
│  Dashboard │ Chat Interface │ Upload Panel │ Calendar View      │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST + WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                    Backend (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Agent Orchestrator (LangGraph)                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│  │  │  Parser  │→│ Planner  │→│Reflector │→│  Memory  │     │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  LLM Gateway (Groq → Ollama Fallback)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   PostgreSQL Database                           │
│  users │ syllabi │ chats │ plans │ feedback │ tokens            │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

1. **Parser Agent**: Extracts dates, assignments, and deadlines from syllabi
2. **Planner Agent**: Creates optimized study schedules based on student preferences
3. **Reflector Agent**: Analyzes feedback and adapts plans
4. **Memory Agent**: Retrieves relevant context from past conversations
5. **Calendar Agent**: Generates `.ics` calendar files

---

## Tech Stack

| Layer | Technology | Why? |
|-------|-----------|------|
| **Frontend** | Next.js 14, Tailwind CSS, shadcn/ui | Server components, fast iteration |
| **Backend** | FastAPI, Python 3.11+ | Async-native, WebSocket support |
| **Database** | PostgreSQL 15 | Strong relationships, analytics-ready |
| **AI/LLM** | Groq API, Ollama (fallback) | Fast inference, local backup |
| **Agents** | LangGraph | Modular agent orchestration |
| **Auth** | JWT with refresh tokens | Stateless, scalable |
| **Deployment** | Docker, Docker Compose | Consistent environments |

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Ollama installed locally (optional, for fallback)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/student-planner.git
cd student-planner

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 3. Start the database
docker-compose up -d postgres

# 4. Set up backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 5. Run database migrations
alembic upgrade head

# 6. Start backend server
uvicorn app.main:app --reload

# 7. Set up frontend (new terminal)
cd ../frontend
npm install
npm run dev
```

Visit: [http://localhost:3000](http://localhost:3000)

---

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

---

## API Documentation

Once running, visit:
- **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Example API Usage

```python
import requests

# Sign up
response = requests.post("http://localhost:8000/auth/signup", json={
    "email": "student@university.edu",
    "password": "securepass123",
    "full_name": "Jane Doe"
})

# Upload syllabus
with open("syllabus.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/syllabus/upload",
        files={"file": f},
        headers={"Authorization": f"Bearer {access_token}"}
    )
```


## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---


<p align="center">Made with ❤️ by students, for students</p>
