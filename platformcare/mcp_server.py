from mcp.server.fastmcp import FastMCP
from .tools import TOOLS

server = FastMCP("PlatformCare read-only operations")
for tool in TOOLS:
    server.tool()(tool)

if __name__ == "__main__":
    server.run(transport="stdio")
