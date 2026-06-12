# MathVerse AI

A complete AI-powered mathematics learning and solving platform — from basic arithmetic to advanced engineering mathematics.

## Features

- **AI Math Solver** — step-by-step solutions using SymPy + LLM
- **Formula Library** — 100+ formulas across all math topics
- **Math Topics** — Wikipedia-style knowledge base
- **Graphing Calculator** — 2D/3D interactive plots via Plotly
- **Practice Quiz** — AI-generated questions with grading
- **Solve History** — persistent session history
- **Multi-level explanations** — Kids → Expert

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | Python 3.11 + FastAPI + SymPy + NumPy |
| Database | SQLite (dev) → PostgreSQL-ready |
| AI | Anthropic Claude / OpenAI / Gemini (pluggable) |
| Graphs | Plotly (CDN in browser) |

---

## Quick Start (Windows)

### Prerequisites

- Python 3.10+ (recommended: Anaconda)
- Node.js 18+ and npm
- Git

---

### 1. Clone / Open the project

```
cd C:\Users\Sujit\mathverse-ai
```

### 2. Set up the Backend

```powershell
# Create and activate virtual environment
cd backend
python -m venv venv
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY or OPENAI_API_KEY

# Start the backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be running at http://localhost:8000
Interactive docs: http://localhost:8000/docs

### 3. Set up the Frontend

Open a NEW terminal window:

```powershell
cd C:\Users\Sujit\mathverse-ai\frontend

# Install Node dependencies
npm install

# Start the dev server
npm run dev
```

The app will be running at http://localhost:5173

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

```env
# Choose one provider:
LLM_PROVIDER=anthropic          # or: openai, gemini, none

# Set the matching key:
ANTHROPIC_API_KEY=sk-ant-...    # Claude
OPENAI_API_KEY=sk-...           # GPT-4
GEMINI_API_KEY=AIza...          # Gemini

# (Optional) Change models:
ANTHROPIC_MODEL=claude-sonnet-4-6
OPENAI_MODEL=gpt-4o
```

If no API key is set (`LLM_PROVIDER=none`), the solver still works — it uses SymPy for symbolic math and shows a template explanation instead of an LLM response.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/solve` | Solve a math problem |
| POST | `/api/v1/graph` | Plot 2D functions |
| POST | `/api/v1/graph/3d` | Plot 3D surface |
| GET | `/api/v1/formula/search` | Search formulas |
| GET | `/api/v1/topics` | List math topics |
| GET | `/api/v1/topics/{slug}` | Get topic detail |
| POST | `/api/v1/quiz/generate` | Generate quiz |
| POST | `/api/v1/quiz/submit` | Submit and grade quiz |
| GET | `/api/v1/history` | Get solve history |
| GET | `/api/v1/admin/dashboard` | Admin statistics |

Full interactive docs at `/docs` when backend is running.

---

## Project Structure

```
mathverse-ai/
├── backend/
│   ├── main.py                   # FastAPI app entry
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── core/
│       │   ├── config.py         # Settings from .env
│       │   └── database.py       # SQLAlchemy async setup
│       ├── models/
│       │   └── models.py         # DB models
│       ├── services/
│       │   ├── math_engine.py    # SymPy solver
│       │   ├── llm_service.py    # LLM abstraction
│       │   └── graph_service.py  # Plotly data builder
│       ├── api/routes/
│       │   ├── solve.py
│       │   ├── graph.py
│       │   ├── formula.py
│       │   ├── topics.py
│       │   ├── quiz.py
│       │   ├── history.py
│       │   ├── user.py
│       │   └── admin.py
│       └── data/
│           └── seed_data.py      # Seed formulas & topics
└── frontend/
    ├── src/
    │   ├── App.tsx               # Router
    │   ├── main.tsx
    │   ├── index.css
    │   ├── components/           # Reusable UI
    │   ├── pages/                # All 11 pages
    │   ├── services/api.ts       # Axios API layer
    │   ├── hooks/                # useTheme, useSolver
    │   └── types/index.ts
    ├── package.json
    ├── vite.config.ts
    └── tailwind.config.js
```

---

## Deployment Notes

### Backend (Production)
```powershell
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend (Build)
```powershell
npm run build
# Serve the dist/ folder with nginx or any static server
```

### Database upgrade to PostgreSQL
Change `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
```
Then `pip install asyncpg`.

---

## Supported Math Topics

Arithmetic · Algebra · Geometry · Trigonometry · Calculus (Differential + Integral) · Limits · Linear Algebra · Statistics · Probability · Number Theory · Differential Equations · Financial Mathematics · Engineering Mathematics · Data Science Math

---

## Future Roadmap

- [ ] LaTeX rendering (KaTeX inline in solver)
- [ ] Image-based problem input (OCR)
- [ ] Voice input support
- [ ] Multi-language explanations
- [ ] User authentication (JWT)
- [ ] Subscription plans (Stripe)
- [ ] Mobile app (React Native)
- [ ] Teacher dashboard with class progress
- [ ] Offline mode with service workers
- [ ] Export solutions as PDF
