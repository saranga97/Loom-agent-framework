# Loom AI - Agent Framework | Tenant Config CRUD (MongoDB + In-Memory Cache)

import time

from app.models.schemas import TenantConfig
from app.services.database import get_db

COLLECTION = "tenant_configs"
CACHE_TTL = 60  # seconds

_cache: dict[str, tuple[TenantConfig, float]] = {}


def _collection():
    return get_db()[COLLECTION]


def _cache_get(tenant_name: str) -> TenantConfig | None:
    entry = _cache.get(tenant_name)
    if entry is None:
        return None
    config, ts = entry
    if time.time() - ts > CACHE_TTL:
        del _cache[tenant_name]
        return None
    return config


def _cache_set(config: TenantConfig):
    _cache[config.tenant_name] = (config, time.time())


def _cache_evict(tenant_name: str):
    _cache.pop(tenant_name, None)


async def warm_cache():
    """Load all tenant configs from MongoDB into cache. Called at startup."""
    col = _collection()
    count = 0
    async for doc in col.find():
        doc.pop("_id", None)
        config = TenantConfig(**doc)
        _cache_set(config)
        count += 1
    print(f"[Loom AI] Loaded {count} tenant configs into cache")


async def list_tenants() -> list[TenantConfig]:
    col = _collection()
    configs = []
    async for doc in col.find().sort("tenant_name", 1):
        doc.pop("_id", None)
        config = TenantConfig(**doc)
        _cache_set(config)
        configs.append(config)
    return configs


async def get_tenant(tenant_name: str) -> TenantConfig | None:
    cached = _cache_get(tenant_name)
    if cached is not None:
        return cached
    col = _collection()
    doc = await col.find_one({"tenant_name": tenant_name})
    if doc is None:
        return None
    doc.pop("_id", None)
    config = TenantConfig(**doc)
    _cache_set(config)
    return config


async def create_tenant(config: TenantConfig) -> TenantConfig:
    col = _collection()
    existing = await col.find_one({"tenant_name": config.tenant_name})
    if existing:
        raise ValueError(f"Tenant '{config.tenant_name}' already exists")
    await col.insert_one(config.model_dump())
    _cache_set(config)
    return config


async def update_tenant(tenant_name: str, config: TenantConfig) -> TenantConfig:
    col = _collection()
    result = await col.find_one_and_update(
        {"tenant_name": tenant_name},
        {"$set": config.model_dump()},
    )
    if result is None:
        raise ValueError(f"Tenant '{tenant_name}' not found")
    if config.tenant_name != tenant_name:
        _cache_evict(tenant_name)
    _cache_set(config)
    return config


async def delete_tenant(tenant_name: str) -> bool:
    col = _collection()
    result = await col.delete_one({"tenant_name": tenant_name})
    _cache_evict(tenant_name)
    return result.deleted_count > 0
