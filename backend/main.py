"""
MathVerse AI — FastAPI Backend Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import solve, graph, formula, topics, quiz, history, user, admin, auth, payments


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB and seed
    await init_db()
    try:
        from app.data.seed_data import seed
        await seed()
    except Exception as e:
        print(f"Seed warning: {e}")
    yield
    # Shutdown: nothing needed for SQLite


app = FastAPI(
    title="MathVerse AI API",
    description="Comprehensive mathematics solver, explainer, and knowledge base API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(solve.router, prefix="/api/v1", tags=["Solver"])
app.include_router(graph.router, prefix="/api/v1", tags=["Graph"])
app.include_router(formula.router, prefix="/api/v1", tags=["Formulas"])
app.include_router(topics.router, prefix="/api/v1", tags=["Topics"])
app.include_router(quiz.router, prefix="/api/v1", tags=["Quiz"])
app.include_router(history.router, prefix="/api/v1", tags=["History"])
app.include_router(user.router, prefix="/api/v1", tags=["User"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(payments.router, prefix="/api/v1", tags=["Payments"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


@app.get("/api/llm-status", tags=["Health"])
async def llm_status():
    """Test LLM connectivity. Open this URL in browser to diagnose Gemini issues."""
    from app.core.config import settings
    from app.services.llm_service import _key_looks_real, _call_gemini
    provider = settings.LLM_PROVIDER
    gemini_key = settings.GEMINI_API_KEY
    gemini_model = settings.GEMINI_MODEL
    key_ok = _key_looks_real(gemini_key)

    result = {
        "llm_provider": provider,
        "gemini_model": gemini_model,
        "gemini_key_looks_valid": key_ok,
        "gemini_key_prefix": gemini_key[:8] + "..." if key_ok else "(not set or placeholder)",
        "test_call": "not attempted",
    }

    if provider == "gemini" and key_ok:
        try:
            response = await _call_gemini("Say the word: WORKING", max_tokens=10)
            result["test_call"] = "SUCCESS"
            result["test_response"] = response[:50]
        except Exception as e:
            result["test_call"] = "FAILED"
            result["test_error"] = str(e)
    else:
        result["test_call"] = f"skipped — provider is '{provider}', key_ok={key_ok}"

    return result
