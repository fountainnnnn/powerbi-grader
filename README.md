# Power BI Grader

An AI marking assistant for Power BI dashboard assessments. A lecturer uploads the assessment brief and rubric once, then drops in a student team's `.pbix` file and dashboard screenshots. The app works out which visuals and insights belong to which student and returns marks per rubric component, each one justified with evidence quoted from the submission.

> Built as a prototype for a lecturer at Singapore Polytechnic. The project did not go ahead, so this is the prototype as it stood. No course material, student work or real marks are included.

## How it works

1. **Rubric:** upload the brief and marking rubric (PDF, DOCX or image). It is applied to every grading run.
2. **Submission:** upload the team's `.pbix`. The PBIX inspector opens the file and extracts every page, visual title, axis/legend field and insight text box, then assigns each visual to a student by finding their name in a structural position in the title.
3. **Evidence:** attach screenshots of the dashboard. Multi-page PDFs are split into images.
4. **Grading:** GPT-4o Vision receives the rubric, the extracted PBIX evidence and the images, and grades either one named student or the whole team in one pass.

The grading prompt is deliberately strict:

- marks only in the rubric's fixed bands, never in between
- every comment must cite exact evidence such as a visual title, field name or insight phrase
- missing evidence is reported as "Not assessable" rather than guessed
- generic feedback ("could be clearer") is not allowed unless it names the evidence causing it

## Stack

| Part | Tech |
| --- | --- |
| API | FastAPI (Python 3.12), SQLite, OpenAI GPT-4o Vision |
| PBIX parsing | Custom inspector over the `.pbix` layout JSON (`api/src/services/pbix_inspector.py`) |
| Frontend | React 19, TypeScript, Vite |
| Access | A single login set through environment variables |
| Deploy | Vercel (`vercel.json`), or Docker Compose |

## Run locally

```bash
cp .env.example .env    # add OPENAI_API_KEY, APP_LOGIN_USERNAME, APP_LOGIN_PASSWORD

# API
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev
```

On Windows, `START_APP.bat` checks the `.env` and starts both.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /auth/login`, `GET /auth/session` | Login gate |
| `POST /rubric/upload`, `GET /rubric`, `DELETE /rubric` | Manage the rubric |
| `POST /dashboards/upload`, `GET /dashboards/{id}/students` | Upload a `.pbix` and list detected students |
| `POST /chat`, `GET /chat/history` | Grade and discuss a submission |
| `POST /students`, `POST /grade` | One-shot grading without stored state |

Every route is also served under `/api/...` for the Vercel deployment.

## Tests

```bash
cd api && pytest
```

Covers the health check, the PBIX inspector and the stateless grading routes.
