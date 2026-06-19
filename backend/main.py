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
