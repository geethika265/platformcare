import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    async with stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "platformcare.mcp_server"])) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for name, args in [("get_service_health", {}), ("search_logs", {"run_id": "absent"}), ("search_runbooks", {"query": "VALIDATION_FAILED"})]:
                result = await session.call_tool(name, args)
                print(name, result.model_dump_json())

if __name__ == "__main__":
    asyncio.run(main())
