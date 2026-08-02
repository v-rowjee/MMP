"""Dashboard generation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.deps import workspace
from app.schemas.dashboard import Dashboard
from app.services.dashboard.service import DashboardService


router = APIRouter(tags=["dashboard"])


@router.post("/dashboard", response_model=Dashboard)
async def generate_dashboard(
    request: Request,
    workspace_id: str = Depends(workspace),
) -> Dashboard:
    try:
        return DashboardService(request.app.state.db).generate_dashboard(
            workspace_id
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


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
