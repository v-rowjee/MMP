from app.llm.prompt_loader import PromptLoader


def test_dashboard_prompts_load_from_toon_files():
    loader = PromptLoader()
    names = [
        "dashboard_planner",
        "kpis_and_trends",
        "anomalies",
        "forecasts",
        "insights",
        "dashboard_builder",
    ]

    prompts = [loader.load(name) for name in names]

    assert all(prompt.startswith("role: ") for prompt in prompts)
    assert all("task: " in prompt and "output: " in prompt for prompt in prompts)
