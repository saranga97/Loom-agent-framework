# Loom AI - Agent Framework | Tenant Config CRUD (async file I/O)

import json
import aiofiles
from pathlib import Path

from app.config import settings
from app.models.schemas import TenantConfig


def _configs_dir() -> Path:
    path = Path(settings.configs_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _tenant_path(tenant_name: str) -> Path:
    return _configs_dir() / f"{tenant_name}.json"


async def list_tenants() -> list[TenantConfig]:
    configs = []
    for file in sorted(_configs_dir().glob("*.json")):
        async with aiofiles.open(file, "r") as f:
            data = json.loads(await f.read())
            configs.append(TenantConfig(**data))
    return configs


async def get_tenant(tenant_name: str) -> TenantConfig | None:
    path = _tenant_path(tenant_name)
    if not path.exists():
        return None
    async with aiofiles.open(path, "r") as f:
        data = json.loads(await f.read())
    return TenantConfig(**data)


async def create_tenant(config: TenantConfig) -> TenantConfig:
    path = _tenant_path(config.tenant_name)
    if path.exists():
        raise ValueError(f"Tenant '{config.tenant_name}' already exists")
    async with aiofiles.open(path, "w") as f:
        await f.write(json.dumps(config.model_dump(), indent=2))
    return config


async def update_tenant(tenant_name: str, config: TenantConfig) -> TenantConfig:
    path = _tenant_path(tenant_name)
    if not path.exists():
        raise ValueError(f"Tenant '{tenant_name}' not found")
    if config.tenant_name != tenant_name:
        path.unlink()
    new_path = _tenant_path(config.tenant_name)
    async with aiofiles.open(new_path, "w") as f:
        await f.write(json.dumps(config.model_dump(), indent=2))
    return config


async def delete_tenant(tenant_name: str) -> bool:
    path = _tenant_path(tenant_name)
    if not path.exists():
        return False
    path.unlink()
    return True
