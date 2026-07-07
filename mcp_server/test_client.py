import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python", args=["mcp_server.py"]
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            result = await session.call_tool(
                "get_policy", {"policy_number": "POL-1001"}
            )
            print("get_policy result:")
            print(result.content[0].text)

            result2 = await session.call_tool("list_policies", {})
            print("list_policies result:")
            print(result2.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())