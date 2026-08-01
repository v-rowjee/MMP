"""Dashboard generation endpoints."""

from fastapi import APIRouter

from app.schemas.dashboard import Dashboard


router = APIRouter(tags=["dashboard"])


@router.post(
    "/dashboard/{workspace_id}",
    response_model=Dashboard,
)
async def generate_dashboard(
    workspace_id: str,
) -> Dashboard:
    """
    Generate an analytics dashboard.
    """

    raise NotImplementedError


@router.get(
    "/dashboard/{workspace_id}",
    response_model=Dashboard,
)
async def get_dashboard(
    workspace_id: str,
) -> Dashboard:
    """
    Retrieve an existing dashboard.
    """

    raise NotImplementedError