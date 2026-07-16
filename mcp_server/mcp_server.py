# mcp_server.py — Exposes the insurance policy database via MCP (Firestore-backed)
import firebase_admin
from firebase_admin import credentials, firestore
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

server = Server("policy-knowledge-base")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_policy",
            description="Look up an insurance policy by its policy number",
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_number": {
                        "type": "string",
                        "description": "The policy number, e.g. POL-1001"
                    }
                },
                "required": ["policy_number"]
            },
        ),
        Tool(
            name="list_policies",
            description="List all policies in the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {}
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_policy":
        policy_number = arguments["policy_number"]
        doc = db.collection("policies").document(policy_number).get()
        if not doc.exists:
            return [TextContent(type="text", text=f"No policy found for {policy_number}")]
        return [TextContent(type="text", text=str(doc.to_dict()))]

    elif name == "list_policies":
        docs = db.collection("policies").stream()
        result = [doc.to_dict() for doc in docs]
        return [TextContent(type="text", text=str(result))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read, write):
        init_options = server.create_initialization_options()
        await server.run(read, write, init_options)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())