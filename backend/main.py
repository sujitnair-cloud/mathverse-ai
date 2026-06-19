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
    """Test LLM connectivity and list available Gemini models for this API key."""
    import httpx
    from app.core.config import settings
    from app.services.llm_service import _key_looks_real

    provider = settings.LLM_PROVIDER
    gemini_key = settings.GEMINI_API_KEY
    gemini_model = settings.GEMINI_MODEL
    key_ok = _key_looks_real(gemini_key)

    result = {
        "llm_provider": provider,
        "gemini_model_configured": gemini_model,
        "gemini_key_looks_valid": key_ok,
        "gemini_key_prefix": gemini_key[:10] + "..." if key_ok else "(not set)",
        "available_models": [],
        "test_call": "not attempted",
    }

    if not (provider == "gemini" and key_ok):
        result["test_call"] = f"skipped — LLM_PROVIDER='{provider}', key valid={key_ok}"
        return result

    async with httpx.AsyncClient(timeout=20) as client:
        # 1. List all models this key has access to
        for api_ver in ["v1beta", "v1"]:
            try:
                r = await client.get(
                    f"https://generativelanguage.googleapis.com/{api_ver}/models",
                    headers={"x-goog-api-key": gemini_key},
                )
                if r.status_code == 200:
                    models = r.json().get("models", [])
                    result["available_models"] = [m["name"].replace("models/", "") for m in models]
                    result["models_api_version"] = api_ver
                    break
                else:
                    result[f"models_list_{api_ver}"] = f"HTTP {r.status_code}"
            except Exception as e:
                result[f"models_list_{api_ver}_error"] = str(e)

        # 2. Try a test generation with each available model until one works
        models_to_try = result.get("available_models", []) or [
            "gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-2.0-flash-lite",
            "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro",
        ]
        payload = {
            "contents": [{"parts": [{"text": "Reply with one word: WORKING"}]}],
            "generationConfig": {"maxOutputTokens": 10},
        }
        for model in models_to_try[:8]:
            for api_ver in ["v1beta", "v1"]:
                url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model}:generateContent"
                try:
                    r = await client.post(url, json=payload, headers={"x-goog-api-key": gemini_key})
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    result["test_call"] = "SUCCESS"
                    result["working_model"] = model
                    result["working_api_version"] = api_ver
                    result["test_response"] = text.strip()
                    return result
                except Exception as e:
                    result[f"tried_{model}_{api_ver}"] = str(e)[:80]

        result["test_call"] = "FAILED — no model worked. See tried_* fields above."
    return result
