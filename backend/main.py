"""
MathVerse AI — FastAPI Backend Entry Point
"""
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.limiter import limiter
from app.api.routes import solve, graph, formula, topics, quiz, history, user, admin, auth, payments, learning
from app.api.routes import classrooms


def _validate_secrets():
    if settings.has_weak_secrets:
        msg = (
            "[MathVerse] SECURITY WARNING: SECRET_KEY and/or JWT_SECRET_KEY are set to "
            "default placeholder values. Generate real secrets with:\n"
            "  python -c \"import secrets; print(secrets.token_hex(32))\"\n"
            "and set them in your .env file before deploying to production."
        )
        if not settings.DEBUG:
            print(msg, file=sys.stderr)
            raise RuntimeError(
                "Refusing to start in production with default secret keys. "
                "Set SECRET_KEY and JWT_SECRET_KEY in your .env file."
            )
        print(msg, file=sys.stderr)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_secrets()
    await init_db()
    try:
        from app.data.seed_data import seed
        await seed()
    except Exception as e:
        print(f"Seed warning: {e}", file=sys.stderr)
    yield


app = FastAPI(
    title="MathVerse AI API",
    description="Comprehensive mathematics solver, explainer, and knowledge base API",
    version="1.0.0",
    lifespan=lifespan,
    # Hide API docs in production
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
app.include_router(classrooms.router, prefix="/api/v1", tags=["Classrooms"])
app.include_router(learning.router, prefix="/api/v1", tags=["Learning"])
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
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


@app.get("/api/llm-status", tags=["Health"])
async def llm_status(request: Request):
    """Diagnose LLM connectivity. Requires authentication in production."""
    from app.core.auth import get_current_user
    from app.core.database import get_db
    from fastapi.security import HTTPBearer

    # In production, only authenticated users can see this (key prefix is exposed)
    if not settings.DEBUG:
        bearer = HTTPBearer(auto_error=False)
        from fastapi import HTTPException
        credentials = await bearer(request)
        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")

    import httpx
    from app.core.config import settings as s
    from app.services.llm_service import _key_looks_real

    provider = s.LLM_PROVIDER
    gemini_key = s.GEMINI_API_KEY
    gemini_model = s.GEMINI_MODEL
    key_ok = _key_looks_real(gemini_key)

    result: dict = {
        "llm_provider": provider,
        "gemini_model_configured": gemini_model,
        "gemini_key_looks_valid": key_ok,
        "gemini_key_prefix": gemini_key[:12] + "..." if key_ok else "(not set)",
        "test_call": "not attempted",
    }

    if not (provider == "gemini" and key_ok):
        result["test_call"] = f"skipped — LLM_PROVIDER='{provider}', key valid={key_ok}"
        return result

    payload = {
        "contents": [{"parts": [{"text": "Reply with exactly one word: WORKING"}]}],
        "generationConfig": {"maxOutputTokens": 10},
    }
    models_quick = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"]

    async with httpx.AsyncClient(timeout=20) as client:
        for api_ver in ["v1beta", "v1"]:
            for auth_header, auth_label in [
                ({"x-goog-api-key": gemini_key}, "api-key-header"),
                ({}, "query-param"),
            ]:
                list_url = f"https://generativelanguage.googleapis.com/{api_ver}/models"
                params = {} if auth_header else {"key": gemini_key}
                try:
                    r = await client.get(list_url, headers=auth_header, params=params)
                    result[f"models_list_{api_ver}_{auth_label}"] = (
                        f"HTTP {r.status_code} — {r.text[:300]}"
                    )
                    if r.status_code == 200:
                        models = r.json().get("models", [])
                        result["available_models"] = [m["name"].replace("models/", "") for m in models]
                        result["models_api_version"] = api_ver
                        break
                except Exception as e:
                    result[f"models_list_{api_ver}_{auth_label}_err"] = str(e)[:200]

        # 1b. Try generation with multiple auth methods
        for model in models_quick:
            for api_ver in ["v1beta"]:
                base = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model}:generateContent"
                for auth_h, label in [
                    ({"x-goog-api-key": gemini_key}, "x-goog-api-key"),
                    ({}, "query-param"),
                    ({"Authorization": f"Bearer {gemini_key}"}, "bearer"),
                ]:
                    url = base if auth_h != {} else f"{base}?key={gemini_key}"
                    try:
                        r = await client.post(url, json=payload, headers=auth_h)
                        key_tag = f"rest_{model}_{label}"
                        if r.status_code == 200:
                            parts = r.json()["candidates"][0]["content"]["parts"]
                            text = ""
                            for part in parts:
                                if not part.get("thought", False) and "text" in part:
                                    text = part["text"]
                                    break
                            if not text:
                                text = parts[-1].get("text", "")
                            result["test_call"] = "SUCCESS (REST)"
                            result["working_model"] = model
                            result["working_auth"] = label
                            result["test_response"] = text.strip()
                            return result
                        else:
                            result[key_tag] = f"HTTP {r.status_code}: {r.text[:200]}"
                    except Exception as e:
                        result[f"rest_{model}_{label}_err"] = str(e)[:200]

    result["test_call"] = "FAILED — check models_list_* and rest_* fields for exact errors"
    return result
