# Loom AI - Agent Framework | Graph Builder
# Flow: START → agent → tools ↔ agent → response → END

from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import create_agent_node, create_tool_node, create_response_node
from app.graph.edges import should_continue
from app.tools.document_retriever import create_document_retriever_tool


def build_agent_graph(config: dict):
    """Build and compile the LangGraph agent for a tenant config."""
    retriever_tool = create_document_retriever_tool(
        tenant_name=config["tenant_name"],
        top_k=config.get("retriever_top_k", 5),
        min_confidence=config.get("retriever_min_confidence", 0.3),
    )
    tools = [retriever_tool]

    graph = StateGraph(AgentState)
    graph.add_node("agent", create_agent_node(config, tools))
    graph.add_node("tools", create_tool_node(tools))
    graph.add_node("response", create_response_node(config))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "response": "response"})
    graph.add_edge("tools", "agent")
    graph.add_edge("response", END)

    return graph.compile()
