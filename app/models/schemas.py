# Loom AI - Agent Framework | Pydantic Schemas

from pydantic import BaseModel, Field


class ThemeColors(BaseModel):
    primary: str = "#6366f1"
    secondary: str = "#8b5cf6"


class TenantConfig(BaseModel):
    tenant_name: str
    chatbot_name: str = "Loom AI Assistant"
    agent_instructions: str = "You are a helpful assistant."
    agent_llm_provider: str = "openai"
    agent_model: str = "gpt-4.1"
    response_instructions: str = "Format responses clearly and concisely."
    response_llm_provider: str = "openai"
    response_model: str = "gpt-4.1-mini"
    retriever_top_k: int = Field(default=5, ge=1, le=100)
    retriever_min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    theme_colors: ThemeColors = Field(default_factory=ThemeColors)


class TenantListResponse(BaseModel):
    tenants: list[TenantConfig]
    total: int


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    tenant_name: str
