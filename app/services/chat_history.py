# Loom AI - Agent Framework | Chat History Service

import uuid
from datetime import datetime, timezone

from app.services.database import get_db


def _generate_room_id(tenant_name: str) -> str:
    return f"{tenant_name}_{uuid.uuid4().hex[:8]}"


async def create_room(tenant_name: str, username: str) -> str:
    db = get_db()
    collection = db[tenant_name]
    room_id = _generate_room_id(tenant_name)
    now = datetime.now(timezone.utc)

    document = {
        "_id": room_id,
        "room_id": room_id,
        "tenant_name": tenant_name,
        "username": username,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    await collection.insert_one(document)
    return room_id


async def save_message(tenant_name: str, room_id: str, role: str, content: str):
    db = get_db()
    collection = db[tenant_name]
    now = datetime.now(timezone.utc)

    await collection.update_one(
        {"_id": room_id},
        {
            "$push": {"messages": {"role": role, "content": content, "timestamp": now}},
            "$set": {"updated_at": now},
        },
    )


async def get_history(tenant_name: str, room_id: str) -> dict | None:
    db = get_db()
    collection = db[tenant_name]
    return await collection.find_one({"_id": room_id})


async def list_rooms(tenant_name: str) -> list[dict]:
    db = get_db()
    collection = db[tenant_name]
    cursor = collection.find(
        {},
        {
            "room_id": 1,
            "username": 1,
            "created_at": 1,
            "updated_at": 1,
            "message_count": {"$size": "$messages"},
        },
    ).sort("updated_at", -1)
    return await cursor.to_list(length=100)
