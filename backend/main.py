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
    """Test LLM connectivity and diagnose Gemini API key issues."""
    import httpx, asyncio
    from app.core.config import settings
    from app.services.llm_service import _key_looks_real

    provider = settings.LLM_PROVIDER
    gemini_key = settings.GEMINI_API_KEY
    gemini_model = settings.GEMINI_MODEL
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

    # ── Phase 1: REST API with full error body capture ─────────────────────────
    async with httpx.AsyncClient(timeout=20) as client:
        # 1a. List models (diagnostic only)
        for api_ver in ["v1beta", "v1"]:
            for auth_header, auth_label in [
                ({"x-goog-api-key": gemini_key}, "api-key-header"),
                ({}, f"?key=... (query param)"),
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
                            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                            result["test_call"] = "SUCCESS (REST)"
                            result["working_model"] = model
                            result["working_auth"] = label
                            result["test_response"] = text.strip()
                            return result
                        else:
                            result[key_tag] = f"HTTP {r.status_code}: {r.text[:200]}"
                    except Exception as e:
                        result[f"rest_{model}_{label}_err"] = str(e)[:200]

    # ── Phase 2: google-generativeai SDK ──────────────────────────────────────
    def _sdk_test() -> str:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=gemini_key)
        for m in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"]:
            try:
                model_obj = genai.GenerativeModel(m)
                resp = model_obj.generate_content(
                    "Reply with one word: WORKING",
                    generation_config={"max_output_tokens": 10},
                )
                return f"SDK success with {m}: {resp.text.strip()}"
            except Exception as e:
                result[f"sdk_{m}"] = str(e)[:200]
        return "SDK: all models failed"

    loop = asyncio.get_running_loop()
    try:
        sdk_result = await loop.run_in_executor(None, _sdk_test)
        if sdk_result.startswith("SDK success"):
            result["test_call"] = "SUCCESS (SDK)"
            result["sdk_result"] = sdk_result
            return result
        result["sdk_result"] = sdk_result
    except Exception as e:
        result["sdk_error"] = str(e)[:300]

    result["test_call"] = "FAILED — check models_list_* and rest_*/sdk_* fields for exact errors"
    return result
