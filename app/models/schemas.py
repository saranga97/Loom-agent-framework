# Loom AI - Agent Framework | Pydantic Schemas

from datetime import datetime
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
    response_instructions: str = "Format responses in Markdown. Use headings, bullet points, numbered lists, bold, and code blocks where appropriate. Keep responses clear and well-structured."
    response_llm_provider: str = "openai"
    response_model: str = "gpt-4.1-mini"
    retriever_top_k: int = Field(default=5, ge=1, le=100)
    retriever_min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    logo_url: str | None = None
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


class StartChatRequest(BaseModel):
    username: str


class StartChatResponse(BaseModel):
    room_id: str
    username: str
    greeting: str


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime | None = None


class ChatRoomSummary(BaseModel):
    room_id: str
    username: str
    created_at: datetime
    updated_at: datetime | None = None
    message_count: int = 0


class ChatRoomListResponse(BaseModel):
    rooms: list[ChatRoomSummary]
    total: int


class ChatHistoryResponse(BaseModel):
    room_id: str
    username: str
    messages: list[ChatMessage]
