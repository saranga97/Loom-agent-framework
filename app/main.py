# Loom AI - Agent Framework | FastAPI Entry Point

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, tenants


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[Loom AI] Agent Framework starting on port {settings.agent_framework_port}")
    print(f"[Loom AI] Environment: {settings.environment}")
    print(f"[Loom AI] Doc Retriever: {settings.doc_retriever_url}")
    yield
    print("[Loom AI] Agent Framework shutting down")


app = FastAPI(
    title="Loom AI - Agent Framework",
    description="Multi-tenant chat agent framework using LangGraph + LangChain",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants.router)
app.include_router(chat.router)


@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "healthy",
        "service": "agent-framework",
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.agent_framework_port,
        reload=settings.environment == "dev",
    )
