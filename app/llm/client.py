"""Ollama client configured by agent_models.toml."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, TypeVar
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)

CONFIG_PATH = Path(__file__).with_name("agent_models.toml")

class OllamaClient:
    def __init__(
        self,
        config_path: Path | str = CONFIG_PATH,
    ) -> None:
        with Path(config_path).open("rb") as file:
            config = tomllib.load(file)
        self.url = config["ollama"]["base_url"].rstrip("/") + "/api/chat"
        self.timeout = config["ollama"]["timeout_seconds"]
        self.agents = config["agents"]

    def generate(
        self,
        agent: str,
        system_prompt: str,
        context: Any,
        response_model: type[ModelT],
    ) -> ModelT:
        """Run an explicit prompt through an agent's configured model."""
        if agent not in self.agents:
            raise KeyError(f"unknown agent {agent!r}; configured: {sorted(self.agents)}")

        options = dict(self.agents[agent])
        payload = {
            "model": options.pop("model"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(context)},
            ],
            "stream": False,
            "format": response_model.model_json_schema(),
            "options": options,
        }

        try:
            return response_model.model_validate_json(self._post(payload))
        except (OSError, KeyError, ValueError, ValidationError) as error:
            raise RuntimeError(
                f"agent={agent!r}: {error}"
            ) from error

    def _post(self, payload: dict[str, Any]) -> str:
        request = Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read())["message"]["content"]
