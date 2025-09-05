from typing import List

from mcp.server.fastmcp import FastMCP
from pydantic import TypeAdapter
from app import crud
from app.database import AsyncSessionLocal
from app import schemas


mcp = FastMCP("Glideator-MCP")


@mcp.tool()
async def list_sites() -> List[schemas.SiteListItem]:
    """Get list of all sites with their IDs and names"""
    async with AsyncSessionLocal() as db:
        sites_raw = await crud.get_site_list(db)
        # Use TypeAdapter to convert SQLAlchemy Row objects to Pydantic schemas
        adapter = TypeAdapter(List[schemas.SiteListItem])
        sites_data = [{"site_id": row.site_id, "name": row.name} for row in sites_raw]
        sites = adapter.validate_python(sites_data)
    return sites #[site.model_dump() for site in sites]


@mcp.tool()
async def get_site_info(site_id: int) -> schemas.SiteInfo:
    """Get site info by ID"""
    async with AsyncSessionLocal() as db:
        site_info_model = await crud.get_site_info(db, site_id)
        if site_info_model is None:
            return None
        # Convert SQLAlchemy model to Pydantic schema
        site_info = schemas.SiteInfo(
            site_id=site_info_model.site_id,
            site_name=site_info_model.site_name,
            country=site_info_model.country,
            html=site_info_model.html
        )
    return site_info#.model_dump()