# Loom AI - Agent Framework | Terminal Chat (SSE streaming test client)

import sys
import os
import json
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import settings

BASE_URL = f"http://localhost:{settings.agent_framework_port}"


def print_banner():
    print("\n" + "=" * 60)
    print("  Loom AI - Agent Framework | Terminal Chat")
    print(f"  Environment: {settings.environment}")
    print(f"  Agent Framework: {BASE_URL}")
    print(f"  Doc Retriever: {settings.doc_retriever_url}")
    print("=" * 60)


def list_tenants() -> list[dict]:
    try:
        response = httpx.get(f"{BASE_URL}/api/v1/tenants/", timeout=10.0)
        response.raise_for_status()
        return response.json().get("tenants", [])
    except httpx.ConnectError:
        print(f"\n  [ERROR] Could not connect to Agent Framework at {BASE_URL}")
        print("  Make sure the service is running: python -m app.main")
        sys.exit(1)
    except Exception as e:
        print(f"\n  [ERROR] Failed to list tenants: {e}")
        sys.exit(1)


def select_tenant(tenants: list[dict]) -> str:
    if not tenants:
        print("\n  No tenants found. Create one via POST /api/v1/tenants/")
        sys.exit(1)

    print("\n  Available tenants:")
    print("-" * 40)
    for i, t in enumerate(tenants, 1):
        print(f"  [{i}] {t['tenant_name']} - {t['chatbot_name']}")
    print("-" * 40)

    while True:
        try:
            choice = input(f"\n  Select tenant (1-{len(tenants)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(tenants):
                return tenants[idx]["tenant_name"]
            print(f"  Please enter a number between 1 and {len(tenants)}")
        except ValueError:
            print("  Please enter a valid number")
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye!")
            sys.exit(0)


def stream_chat(tenant_name: str, message: str, history: list[dict]):
    url = f"{BASE_URL}/api/v1/chat/{tenant_name}"
    full_response = ""

    try:
        with httpx.stream("POST", url, json={"message": message, "conversation_history": history}, timeout=120.0) as response:
            response.raise_for_status()
            event_type = None

            for line in response.iter_lines():
                line = line.strip()

                if line.startswith("event:"):
                    event_type = line[6:].strip()
                    continue

                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue

                    if event_type == "token":
                        content = data.get("content", "")
                        print(content, end="", flush=True)
                        full_response += content
                    elif event_type == "tool_call":
                        query = data.get("input", {}).get("query", "")
                        print(f"\n  [TOOL CALL] {data.get('tool', '')}: \"{query}\"", flush=True)
                    elif event_type == "tool_result":
                        result = data.get("result", "")
                        preview = result[:150] + "..." if len(result) > 150 else result
                        print(f"  [TOOL RESULT] {data.get('tool', '')}: {preview}\n", flush=True)
                    elif event_type == "error":
                        print(f"\n  [ERROR] {data.get('error', 'Unknown error')}")

                    event_type = None

    except httpx.HTTPStatusError as e:
        print(f"\n  [ERROR] HTTP {e.response.status_code}: {e.response.text}")
    except httpx.ConnectError:
        print(f"\n  [ERROR] Could not connect to Agent Framework at {BASE_URL}")
    except Exception as e:
        print(f"\n  [ERROR] {e}")

    return full_response


def main():
    print_banner()

    tenants = list_tenants()
    tenant_name = select_tenant(tenants)
    print(f"\n  [OK] Chatting with tenant: {tenant_name}")
    print("  Type your message below. Type 'quit' or 'exit' to stop.\n")

    conversation_history = []

    while True:
        try:
            message = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye!")
            break

        if message.lower() in ("quit", "exit", "q"):
            print("\n  Goodbye!")
            break

        if not message:
            print("  Please enter a message.\n")
            continue

        print("\n  Bot: ", end="", flush=True)
        response = stream_chat(tenant_name, message, conversation_history)
        print("\n")

        if response:
            conversation_history.append({"role": "user", "content": message})
            conversation_history.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
