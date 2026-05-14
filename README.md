# PowerBI Vision Chatbot Application

A ChatGPT-style interface for analyzing PowerBI dashboards and documents with a global rubric. Upload a grading rubric once, then attach different documents to each message for instant AI-powered analysis using OpenAI's GPT-4o Vision model.

## Features

- **Global Rubric** - Upload a PDF, DOCX, or image once. It's automatically applied to all analyses
- **Per-Message Attachments** - Like Claude, attach a different document to each message
- **Multi-Page PDFs** - Automatically converts PDFs to images for analysis
- **Chat History** - Global conversation history with full session management (create, rename, delete, export)
- **No Authentication** - Zero setup, instant use
- **SQLite Storage** - All chats and files stored locally

## Architecture

- **Backend** (FastAPI, Python 3.12) - REST API with SQLite, OpenAI Vision integration
- **Frontend** (React 19, TypeScript) - ChatGPT-style chat interface
- **Database** (SQLite) - Local file-based, zero configuration needed

**2 Terminal Setup:** Just run backend + frontend!

## Prerequisites

- **Python 3.12** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **OpenAI API Key** - Get from [OpenAI Platform](https://platform.openai.com/api-keys)

## Quick Start (5 Minutes)

### Step 1: Get Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Copy the key

### Step 2: Setup Environment

From the project root, create `.env`:

```cmd
copy .env.example .env
```

Edit `.env` and add your OpenAI key:

```
API_SECRET_KEY=dev-secret-key
OPENAI_API_KEY=sk-your-actual-openai-key-here
VITE_API_URL=http://localhost:8000
```

### Step 3: Install Dependencies

**Terminal 1 - Backend:**

```cmd
cd api
pip install uv
uv sync
```

**Terminal 2 - Frontend (open new CMD window):**

```cmd
cd frontend
npm install
```

### Step 4: Run Both Services

**Terminal 1 - Backend:**

```cmd
cd api
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Wait for:
```
Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 - Frontend:**

```cmd
cd frontend
npm run dev
```

Wait for:
```
VITE v5.x.x  ready in xx ms
➜  Local:   http://localhost:5173/
```

### Step 5: Open the App

Open your browser: **http://localhost:3001**

1. **Upload Rubric** (sidebar) - Upload your grading rubric (PDF, DOCX, or image)
2. **Create Chat** - Click "+ New Chat" to start a conversation
3. **Attach Documents** - Use the attachment button (📎) to add a document to a message
4. **Ask Questions** - The rubric + attached document are analyzed together

---

## Usage

### Upload a Rubric

1. In the left sidebar, find the "Rubric" card
2. Click the upload area
3. Select a PDF, DOCX, or image file
4. The rubric is now global - it applies to all messages

### Send a Message with Document

1. Type your question in the input field
2. Click the attachment button (📎) to add a document
3. Click send
4. The AI analyzes the document against your rubric

### Manage Chats

- **New Chat:** Click "+ New Chat" button
- **Rename:** Double-click a chat name in the list
- **Delete:** Hover over a chat and click the delete icon
- **Export:** Click the export button in the top nav to download as .txt
- **Clear All:** Use the "Clear All" tool in the sidebar

---

## API Endpoints

**Rubric** (Global, persistent)
- `POST /rubric/upload` - Upload grading rubric
- `GET /rubric` - Get active rubric
- `DELETE /rubric` - Remove rubric

**Chat** (Global history)
- `POST /chat` - Send message (with optional dashboard_id)
- `GET /chat/history` - Get full chat history

**Dashboards** (Per-message attachments)
- `POST /dashboards/upload` - Upload document
- `GET /dashboards` - List uploaded documents

**Health**
- `GET /health` - API status

**API Docs:** http://localhost:8000/docs

---

## File Formats Supported

- **Images:** PNG, JPG, JPEG
- **Documents:** PDF, DOCX, DOC

PDFs are automatically converted to images (144 DPI, max 10 pages).

---

## Troubleshooting

### Port Already in Use

```cmd
# Find process on port 8000
netstat -ano | findstr :8000

# Kill it (replace PID)
taskkill /PID <PID> /F
```

### `OPENAI_API_KEY not found`

Make sure:
1. `.env` file exists in project root
2. Your actual OpenAI key is set (not placeholder)
3. You used `uv run` command

### `npm install` Fails

```cmd
cd frontend
npm install --legacy-peer-deps
npm run dev
```

### Frontend Can't Connect to API

Check `VITE_API_URL=http://localhost:8000` in `.env`

### Reset Everything

```cmd
# Delete database
del api\app.db

# Delete uploads
rmdir /s /q api\uploads

# Restart backend
cd api
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, TypeScript, Vite, Plain CSS |
| **Backend** | FastAPI, Python 3.12, SQLite |
| **AI** | OpenAI GPT-4o (Vision) |
| **File Processing** | pymupdf (PDF→PNG), reportlab (DOCX→PDF), Pillow (images) |
| **Package Manager** | `uv` (Python), npm (Node) |

---

## What Each Terminal Does

**Terminal 1 (Backend):**
- REST API on port 8000
- File uploads and conversion
- SQLite database
- OpenAI Vision API calls
- Auto-reloads on code changes

**Terminal 2 (Frontend):**
- React dev server on port 5173 (proxied to 3001 in docs)
- ChatGPT-style UI
- Hot-reloads on code changes
- Calls backend at `http://localhost:8000`

---

## Database

SQLite database auto-created at `api/app.db`

**Reset database:**
```cmd
del api\app.db
# Restart backend - it will recreate
```

---

## Common Commands

```cmd
# Start backend
cd api && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Start frontend
cd frontend && npm run dev

# Build frontend for production
cd frontend && npm run build

# Reset database
del api\app.db

# Reset uploads
rmdir /s /q api\uploads
```

---

## Architecture Notes

See [CLAUDE.md](./CLAUDE.md) for detailed architecture, file structure, and development patterns.

---

## License

MIT

---

**Start grading with AI! 🚀**
