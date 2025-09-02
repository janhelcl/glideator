from typing import List

from mcp.server.fastmcp import FastMCP
from app import crud
from app.database import AsyncSessionLocal
from app import schemas


mcp = FastMCP("Glideator-MCP")


@mcp.tool()
async def list_sites() -> List[schemas.SiteListItem]:
    """Get all sites"""
    async with AsyncSessionLocal() as db:
        sites = await crud.get_site_list(db)
    return sites
