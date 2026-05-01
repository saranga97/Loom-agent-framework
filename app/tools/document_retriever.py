# Loom AI - Agent Framework | Document Retriever Tool (async HTTP call to doc-retriever)

import httpx
from langchain_core.tools import tool
from app.config import settings


def create_document_retriever_tool(tenant_name: str, top_k: int = 5, min_confidence: float = 0.3):
    """Factory: creates a retriever tool with tenant params baked into the closure."""

    @tool
    async def document_retriever(query: str) -> str:
        """Search the knowledge base for relevant documents. Use this when you need information to answer the user's question."""
        url = f"{settings.doc_retriever_url}/api/v1/documents/search/{tenant_name}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json={
                    "query": query,
                    "top_k": top_k,
                    "min_confidence": min_confidence,
                })
                response.raise_for_status()
                data = response.json()

            documents = data.get("documents", [])
            if not documents:
                return "No relevant documents found for this query."

            results = []
            for i, doc in enumerate(documents, 1):
                results.append(f"[Result {i}] (confidence: {doc.get('confidence', 0):.2f})\n{doc.get('context', '')}")
            return "\n\n---\n\n".join(results)

        except httpx.HTTPStatusError as e:
            return f"Error searching documents: HTTP {e.response.status_code}"
        except httpx.ConnectError:
            return "Error: Could not connect to the document retriever service."
        except Exception as e:
            return f"Error searching documents: {str(e)}"

    return document_retriever
