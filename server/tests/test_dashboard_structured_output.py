from app.services.dashboard.structured_output import load_prompt


def test_dashboard_prompts_load_from_toon_files():
    names = [
        "dashboard_planner",
        "kpis_and_trends",
        "anomalies",
        "forecasts",
        "insights",
        "dashboard_builder",
    ]

    prompts = [load_prompt(name) for name in names]

    assert all(prompt.startswith("role: ") for prompt in prompts)
    assert all("task: " in prompt and "output: " in prompt for prompt in prompts)
