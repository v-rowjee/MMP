"""Dataset-context dashboard node."""

from typing import Any

from app.dashboard.repository import DashboardRepository
from app.dashboard.state import DashboardState


def load_dataset_context(
    repository: DashboardRepository, state: DashboardState
) -> dict[str, Any]:
    return {
        "schema": repository.load_dataset_context(
            state["analysis_id"], state["dataset_ids"]
        )
    }
