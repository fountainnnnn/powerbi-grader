# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **PowerBI Vision Chatbot Application**, a lightweight system that allows users to upload PowerBI dashboards, ask natural language questions about them, and receive AI-generated insights powered by OpenAI's vision API.

**Architecture:**
- **API Service** (FastAPI, Python): Single unified REST API with SQLite database
- **Frontend** (React 19, TypeScript): Web UI for dashboard upload and chat interface
- **Database** (SQLite): Local file-based database, no separate server needed
- **AI Integration** (OpenAI): Vision API (gpt-4-vision) called directly from backend

Minimal dependencies - just 2 processes to run!

## Tech Stack & Non-Negotiables

### Backend Stack
- **Runtime:** Python 3.12
- **Package Manager:** `uv` (not pip)
- **Framework:** FastAPI
- **Database:** SQLite (local file-based, no server needed)
- **ORM:** SQLAlchemy (synchronous)
- **API Standards:** JSON request/response bodies only

### Frontend Stack
- **Framework:** React 19
- **Language:** TypeScript (strict mode, no `any` types)
- **Styling:** Plain CSS only (no Tailwind, no styled-components, no Emotion)
- **UI Components:** ShadCN UI for complex components, plain HTML + CSS for custom UX
- **State Management:** React hooks only (no Redux, Zustand, Recoil, MobX)
- **Build Tool:** Vite

### AI Integration
- **LLM Provider:** OpenAI API (gpt-4-vision)
- **Feature:** Vision capability for dashboard image analysis
- **Integration Point:** Direct API calls from backend chat service
- **Rule:** API key stored only in `.env`, NEVER in frontend code

### Forbidden Patterns
- ❌ No CSS utility frameworks (Tailwind, Bootstrap, etc.)
- ❌ No CSS-in-JS libraries (styled-components, Emotion)
- ❌ No state management libraries (Redux, MobX, Zustand, Recoil)
- ❌ No UI component libraries except ShadCN (no Material-UI, Chakra, Ant Design)
- ❌ No API keys in frontend code
- ❌ No `any` types in TypeScript (define proper interfaces)
- ❌ No stub/incomplete files (write files completely)
- ❌ No data transformation in chat endpoint (return raw JSON from OpenAI)

## Development Commands

### First Time Setup

**Windows CMD:**
```cmd
# Copy environment file
copy .env.example .env

# Edit .env with your Gemini API key
notepad .env
```

**Install Dependencies:**

**Terminal 1 - Backend:**
```cmd
cd api
pip install uv
uv sync
```

**Terminal 2 - Frontend:**
```cmd
cd frontend
npm install
```

### Running Services (2 Terminals Only!)

**Terminal 1 - API Backend:**
```cmd
cd api
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```cmd
cd frontend
npm run dev
```

**Access the app:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Docker Compose (Alternative)

```cmd
docker-compose up --build
```

Then access http://localhost:3000

### Testing

```cmd
# API tests (from api/ directory)
cd api
uv run pytest

# Frontend tests (from frontend/ directory)
cd frontend
npm test
```

### Database

SQLite database automatically created at `api/app.db` on first run.

To reset database:
```cmd
# Delete the database file
del api\app.db

# Restart the backend - it will recreate the database
```

## Backend Architecture

### API Service (`/api`)

**Purpose:** Unified REST API with integrated Gemini AI and SQLite database

**Key Endpoints:**
- `POST /dashboards/upload` - Accept PowerBI dashboard images
- `POST /chat` - Process user messages and call Gemini API directly
- `GET /dashboards` - List user's dashboards
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication

**Directory Structure:**
```
api/
├── src/
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Environment and database config
│   ├── database.py          # SQLAlchemy setup, async engine
│   ├── models/              # Pydantic request/response schemas
│   │   ├── chat.py
│   │   ├── dashboard.py
│   │   └── user.py
│   ├── db/                  # Database models and operations
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   └── crud.py          # Database query operations
│   ├── routes/              # API route handlers
│   │   ├── chat.py
│   │   ├── dashboards.py
│   │   └── auth.py
│   ├── services/            # Business logic
│   │   ├── ai_client.py     # HTTP client for AI microservice
│   │   ├── file_handler.py  # Image upload/storage
│   │   └── chat_service.py  # Chat coordination
│   └── utils/
│       └── errors.py        # Custom exceptions
├── pyproject.toml           # uv package configuration
├── Dockerfile
└── tests/
```

**Key Patterns:**
- Synchronous SQLAlchemy (SQLite)
- Pydantic models for request validation
- All database operations in `db/crud.py`
- Direct Gemini API calls in `services/ai_client.py`
- JWT-based authentication

### Frontend Service (`/frontend`)

**Purpose:** React SPA for user interaction

**Key Pages:**
- Login/Auth page
- Dashboard upload page
- Chat interface with dashboard display

**Directory Structure:**
```
frontend/
├── src/
│   ├── main.tsx             # React entry point
│   ├── App.tsx              # Root component with routing
│   ├── components/
│   │   ├── ChatInterface.tsx
│   │   ├── DashboardUpload.tsx
│   │   ├── DashboardViewer.tsx
│   │   └── shared/          # Reusable components
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Upload.tsx
│   │   └── Chat.tsx
│   ├── hooks/               # Custom React hooks
│   │   ├── useChat.ts
│   │   ├── useAuth.ts
│   │   └── useDashboard.ts
│   ├── types/               # TypeScript interfaces
│   │   ├── api.ts
│   │   ├── chat.ts
│   │   └── dashboard.ts
│   ├── services/
│   │   ├── api.ts           # HTTP client
│   │   └── auth.ts          # Auth utilities
│   ├── styles/
│   │   ├── index.css        # Global styles
│   │   └── [component].css  # Component-specific CSS
│   └── utils/
│       └── constants.ts     # API endpoints, constants
├── vite.config.ts
├── tsconfig.json
├── package.json
├── Dockerfile
└── public/
```

**Key Patterns:**
- Strict TypeScript: all types defined in `types/` directory
- Custom hooks for API calls (useChat, useDashboard, useAuth)
- Component-specific CSS files (not global)
- No state management library: use React context + hooks for shared state
- API client in `services/api.ts` using fetch

### OpenAI Vision Integration

**Purpose:** OpenAI Vision API integration for dashboard image analysis (built into API service)

**Integration:**
- Direct calls to OpenAI API from `services/ai_client.py`
- Base64 image encoding for API requests
- Model: `gpt-4-vision`

**Critical Rules:**
- OpenAI API key stored only in `.env`, never in code
- Image analysis returns raw JSON from OpenAI
- No data transformation of responses
- Includes token usage metrics in response

## Environment Variables

All environment variables in `.env` (see `.env.example`):

**API Service:**
- `API_SECRET_KEY` - Secret for JWT tokens (required)

**OpenAI API:**
- `OPENAI_API_KEY` - OpenAI API key (required)

**Frontend:**
- `VITE_API_URL` - API endpoint URL (default: http://localhost:8000)

**Database:**
- Automatically uses SQLite at `api/app.db` (no configuration needed)

## File Upload & Storage

- Uploaded dashboard images stored in `api/uploads/` directory
- Images referenced by unique ID in database
- File validation: PNG, JPG, JPEG only, max 10MB
- Files accessible via `/uploads/<file_id>` endpoint

## Database Schema (SQLite)

**Auto-created on startup. Tables:**

**users**
- `id` (TEXT primary key - UUID)
- `email` (TEXT, unique)
- `password_hash` (TEXT)
- `created_at` (DATETIME)

**dashboards**
- `id` (TEXT primary key - UUID)
- `user_id` (TEXT, foreign key)
- `filename` (TEXT)
- `file_path` (TEXT)
- `uploaded_at` (DATETIME)

**messages**
- `id` (TEXT primary key - UUID)
- `dashboard_id` (TEXT, foreign key)
- `user_message` (TEXT)
- `ai_response` (JSON)
- `created_at` (DATETIME)

## Authentication & Security

- JWT token-based authentication
- Tokens issued on login, validated on protected routes
- Password hashing with bcrypt
- CORS configured for localhost development
- No API keys in frontend code

## Common Development Tasks

### Adding a New API Endpoint

1. Define request/response models in `api/src/models/`
2. Add database model if needed in `api/src/db/models.py`
3. Add CRUD operation in `api/src/db/crud.py` if needed
4. Create route in `api/src/routes/` and register in `main.py`
5. Call from frontend using `services/api.ts` client

### Adding a New Frontend Page

1. Create component in `src/pages/`
2. Define types in `src/types/`
3. Add route in `App.tsx`
4. Use custom hooks for API calls

### Updating OpenAI Integration

1. Modify OpenAI client in `api/src/services/ai_client.py`
2. Update config in `api/src/config.py` (model, temperature, max_tokens)
3. Test with chat endpoint: `POST /chat`
4. Response is automatically stored in database with token usage

## Debugging Tips

- **API logs:** FastAPI reload mode shows request/response logging
- **Database queries:** Enable SQLAlchemy echo mode in config for SQL logging
- **Frontend:** Use React DevTools browser extension
- **CORS issues:** Check `corsMiddleware` config in `api/src/main.py`
- **Docker issues:** Use `docker-compose logs [service]` to view service logs

## Code Quality Standards

- **Formatting:** Black (Python), Prettier (TypeScript)
- **Linting:** Ruff (Python), ESLint (TypeScript)
- **Type Safety:** Strict TypeScript (no `any`), type hints on all Python functions
- **Database:** Synchronous SQLAlchemy with SQLite
- **Error Handling:** Custom exception classes in `api/src/utils/errors.py`
- **API:** JSON request/response, no data transformation
