"""Validated structured responses from dashboard agents."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError


PROMPT_DIR = Path(__file__).parents[2] / "llm" / "prompts"


def load_prompt(name: str) -> str:
    try:
        return (PROMPT_DIR / f"{name}.toon").read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RuntimeError("Prompt could not be loaded") from error


class DashboardStructuredOutputService:
    def __init__(self, llm: Any):
        self.llm = llm

    def request(
        self,
        agent: str,
        prompt_name: str,
        context: dict[str, Any],
        response_model: type[BaseModel],
        error_message: str,
    ) -> dict[str, Any]:
        try:
            instruction = load_prompt(prompt_name)
            response = self.llm.chat(
                agent,
                [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": json.dumps(context)},
                ],
                response_format=response_model.model_json_schema(),
            )
            return response_model.model_validate_json(response).model_dump()
        except (RuntimeError, ValidationError, ValueError) as error:
            raise ValueError(error_message) from error
