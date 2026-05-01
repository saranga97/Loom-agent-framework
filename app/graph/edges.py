# Loom AI - Agent Framework | Conditional Edge Logic

from app.graph.state import AgentState


def should_continue(state: AgentState) -> str:
    """Route to 'tools' if agent made tool calls, otherwise 'response'."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "response"
