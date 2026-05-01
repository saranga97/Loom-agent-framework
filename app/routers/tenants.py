# Loom AI - Agent Framework | Tenant CRUD Router

from fastapi import APIRouter, HTTPException
from app.models.schemas import TenantConfig, TenantListResponse
from app.services import tenant as tenant_service

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.get("/", response_model=TenantListResponse)
async def list_tenants():
    tenants = await tenant_service.list_tenants()
    return TenantListResponse(tenants=tenants, total=len(tenants))


@router.get("/{tenant_name}", response_model=TenantConfig)
async def get_tenant(tenant_name: str):
    config = await tenant_service.get_tenant(tenant_name)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    return config


@router.post("/", response_model=TenantConfig, status_code=201)
async def create_tenant(config: TenantConfig):
    try:
        return await tenant_service.create_tenant(config)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{tenant_name}", response_model=TenantConfig)
async def update_tenant(tenant_name: str, config: TenantConfig):
    try:
        return await tenant_service.update_tenant(tenant_name, config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{tenant_name}")
async def delete_tenant(tenant_name: str):
    if not await tenant_service.delete_tenant(tenant_name):
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    return {"tenant_name": tenant_name, "message": "Tenant deleted successfully"}
