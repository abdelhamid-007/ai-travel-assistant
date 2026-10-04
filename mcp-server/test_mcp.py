"""Starts mcp_server.py like Claude would, lists its tools and calls each one."""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).parent / "mcp_server.py")])


async def main():
    async with stdio_client(SERVER) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        print("Tools:", [t.name for t in tools.tools], "\n")

        for name, args in [
            ("list_destinations", {}),
            ("search_offers", {"request": "beach holiday for a family with kids", "max_price": 2000, "limit": 2}),
            ("agency_policy", {"question": "do I need a visa for Egypt?"}),
        ]:
            result = await session.call_tool(name, args)
            print(f"--- {name}({args})")
            for block in result.content:
                print(block.text[:700])
            print()


asyncio.run(main())
