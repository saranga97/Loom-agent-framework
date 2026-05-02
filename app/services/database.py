# Loom AI - Agent Framework | MongoDB Database Service

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

_client: AsyncIOMotorClient | None = None

DATABASE_NAME = "loom_ai"


async def connect():
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_url)
    # Verify connection
    await _client.admin.command("ping")
    print(f"[Loom AI] Connected to MongoDB at {settings.mongodb_url}")


async def disconnect():
    global _client
    if _client:
        _client.close()
        _client = None
        print("[Loom AI] Disconnected from MongoDB")


def get_db():
    if _client is None:
        raise RuntimeError("MongoDB client not initialized. Call connect() first.")
    return _client[DATABASE_NAME]
