# Loom AI - Agent Framework | Configuration

import os
from pathlib import Path
from pydantic_settings import BaseSettings

_project_root = Path(__file__).resolve().parent.parent
_environment = os.getenv("ENVIRONMENT", "live")
_env_file = _project_root / f".env.{_environment}"
_env_fallback = _project_root / ".env"


class Settings(BaseSettings):
    environment: str = "live"
    agent_framework_port: int = 8002
    doc_retriever_url: str = "http://localhost:8001"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    configs_dir: str = str(_project_root / "configs")

    model_config = {
        "env_file": (_env_file, _env_fallback),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
