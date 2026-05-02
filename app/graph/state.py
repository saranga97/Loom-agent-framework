# Loom AI - Agent Framework | LangGraph State Definition

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    tenant_name: str
    tenant_config: dict
    chat_summary: str
