# Loom AI - Agent Framework | Multi-provider LLM Factory

from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings


def get_llm(provider: str, model: str, streaming: bool = False) -> BaseChatModel:
    """Returns a LangChain chat model for the given provider/model."""
    provider = provider.lower().strip()

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=settings.openai_api_key, streaming=streaming)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=settings.anthropic_api_key, streaming=streaming)

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=settings.google_api_key, streaming=streaming)

    else:
        raise ValueError(f"Unsupported LLM provider: '{provider}'. Supported: openai, anthropic, google")
