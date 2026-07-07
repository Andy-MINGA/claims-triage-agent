# mcp_server.py — Exposes the insurance policy database via MCP
import sqlite3
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("policy-knowledge-base")
db = sqlite3.connect("policies.db", check_same_thread=False)


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
        cursor = db.execute(
            "SELECT * FROM policies WHERE policy_number = ?", (policy_number,)
        )
        row = cursor.fetchone()
        if row is None:
            return [TextContent(type="text", text=f"No policy found for {policy_number}")]
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))
        return [TextContent(type="text", text=str(result))]

    elif name == "list_policies":
        cursor = db.execute("SELECT * FROM policies")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        return [TextContent(type="text", text=str(result))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read, write):
        init_options = server.create_initialization_options()
        await server.run(read, write, init_options)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())