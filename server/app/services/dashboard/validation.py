"""Dashboard layout validation."""

from typing import Any

from pydantic import ValidationError

from app.schemas.dashboard import DashboardLayout


class DashboardValidationService:
    def validate(self, dashboard: dict[str, Any]) -> list[str]:
        try:
            layout = DashboardLayout.model_validate(dashboard)
        except ValidationError as error:
            return [
                f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                for item in error.errors()
            ]

        errors: list[str] = []
        chart_ids = [chart.id for chart in layout.charts]
        if len(chart_ids) != len(set(chart_ids)):
            errors.append("Dashboard chart IDs must be unique")

        for chart in layout.charts:
            if not chart.id.strip():
                errors.append("Dashboard chart ID cannot be blank")
            if not chart.title.strip():
                errors.append(f"Dashboard chart {chart.id!r} title cannot be blank")
            if not chart.dataset.strip():
                errors.append(f"Dashboard chart {chart.id!r} dataset cannot be blank")
            if not chart.sql.strip():
                errors.append(f"Dashboard chart {chart.id!r} SQL cannot be blank")
            if chart.type in {"line", "area", "scatter"} and chart.x_axis is None:
                errors.append(f"Dashboard chart {chart.id!r} requires an x-axis")
            if chart.type != "table" and not chart.series:
                errors.append(f"Dashboard chart {chart.id!r} requires at least one series")
            if any(
                not series.name.strip() or not series.column.strip()
                for series in chart.series
            ):
                errors.append(
                    f"Dashboard chart {chart.id!r} has a blank series name or column"
                )
        return errors
