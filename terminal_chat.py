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


def get_username() -> str:
    while True:
        try:
            username = input("\n  Enter your username: ").strip()
            if username:
                return username
            print("  Username cannot be empty.")
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye!")
            sys.exit(0)


def list_rooms(tenant_name: str) -> list[dict]:
    try:
        response = httpx.get(f"{BASE_URL}/api/v1/chat/{tenant_name}/rooms", timeout=10.0)
        response.raise_for_status()
        return response.json().get("rooms", [])
    except Exception:
        return []


def select_or_create_room(tenant_name: str, username: str) -> tuple[str, str | None]:
    """Returns (room_id, greeting_or_none). Greeting is set only for new rooms."""
    rooms = list_rooms(tenant_name)

    if rooms:
        print(f"\n  Existing chat rooms for '{tenant_name}':")
        print("-" * 60)
        for i, r in enumerate(rooms, 1):
            created = r.get("created_at", "")[:19]
            print(f"  [{i}] {r['room_id']} | {r['username']} | {r.get('message_count', 0)} msgs | {created}")
        print(f"  [N] Start a new chat")
        print("-" * 60)

        while True:
            try:
                choice = input(f"\n  Select room (1-{len(rooms)}) or N for new: ").strip().lower()
                if choice == "n":
                    break
                idx = int(choice) - 1
                if 0 <= idx < len(rooms):
                    return rooms[idx]["room_id"], None
                print(f"  Please enter a number between 1 and {len(rooms)}, or N")
            except ValueError:
                print("  Please enter a valid number or N")
            except (KeyboardInterrupt, EOFError):
                print("\n\n  Goodbye!")
                sys.exit(0)

    # Create new room
    try:
        response = httpx.post(
            f"{BASE_URL}/api/v1/chat/{tenant_name}/start",
            json={"username": username},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["room_id"], data["greeting"]
    except Exception as e:
        print(f"\n  [ERROR] Failed to create chat room: {e}")
        sys.exit(1)


def stream_chat(tenant_name: str, room_id: str, message: str):
    url = f"{BASE_URL}/api/v1/chat/{tenant_name}/{room_id}"
    full_response = ""

    try:
        with httpx.stream("POST", url, json={"message": message}, timeout=120.0) as response:
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
    username = get_username()

    room_id, greeting = select_or_create_room(tenant_name, username)

    print(f"\n  [OK] Room: {room_id}")
    print(f"  [OK] Chatting as: {username}")
    print("  Type your message below. Type 'quit' or 'exit' to stop.\n")

    if greeting:
        print(f"  Bot: {greeting}\n")

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
        stream_chat(tenant_name, room_id, message)
        print("\n")


if __name__ == "__main__":
    main()
