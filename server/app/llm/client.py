"""Ollama client configured by agent_models.toml."""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


class OllamaClient:
    def __init__(self, config_path: Path | str | None = None):
        try:
            path = config_path or Path(__file__).with_name("agent_models.toml")
            with Path(path).open("rb") as file:
                config = tomllib.load(file)
            self.base_url = config["ollama"]["base_url"].rstrip("/")
            self.timeout = config["ollama"]["timeout_seconds"]
            self.agents = config["agents"]
        except Exception as error:
            raise RuntimeError("Ollama request failed") from error

    def chat(
        self,
        agent: str,
        messages: Sequence[Mapping[str, str]],
        response_format: str | dict[str, Any] | None = None,
    ) -> str:
        try:
            config = self.agents[agent]
            payload: dict[str, Any] = {
                "model": config["model"],
                "messages": list(messages),
                "stream": False,
                "options": {key: value for key, value in config.items() if key != "model"},
            }
            if response_format:
                payload["format"] = response_format
            request = Request(
                f"{self.base_url}/api/chat",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())["message"]["content"]
        except Exception as error:
            raise RuntimeError("Ollama request failed") from error
