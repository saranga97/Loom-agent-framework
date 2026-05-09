# Loom AI - Agent Framework | Tenant Read-Only Router
# Tenant creation/update/delete is handled by loom-dashboard-api.
# This router exposes read-only endpoints for chat clients and widgets.

from fastapi import APIRouter, HTTPException
from app.models.schemas import TenantConfig, TenantListResponse
from app.services import tenant as tenant_service

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenants"])


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
