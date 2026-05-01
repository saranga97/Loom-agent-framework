# Loom AI - Agent Framework | Graph Nodes (agent, tools, response)

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode

from app.graph.state import AgentState
from app.llm.factory import get_llm


def create_agent_node(config: dict, tools: list):
    """Agent node: tool-calling LLM that decides to search docs or respond."""
    llm = get_llm(provider=config["agent_llm_provider"], model=config["agent_model"], streaming=False)
    llm_with_tools = llm.bind_tools(tools)
    system_message = SystemMessage(content=config["agent_instructions"])

    async def agent_node(state: AgentState) -> dict:
        messages = [system_message] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    return agent_node


def create_tool_node(tools: list) -> ToolNode:
    """Tool node: executes tool calls via LangGraph's built-in ToolNode."""
    return ToolNode(tools)


def create_response_node(config: dict):
    """Response node: separate streaming LLM for final answer formatting."""
    llm = get_llm(provider=config["response_llm_provider"], model=config["response_model"], streaming=True)
    system_message = SystemMessage(content=config["response_instructions"])

    async def response_node(state: AgentState) -> dict:
        messages = [system_message] + state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    return response_node
