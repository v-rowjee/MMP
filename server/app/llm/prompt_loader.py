"""Prompt loading utilities."""
from pathlib import Path


class PromptLoader:
    def __init__(self, prompt_dir: Path | str | None = None):
        self.prompt_dir = Path(prompt_dir) if prompt_dir else Path(__file__).with_name("prompts")

    def load(self, name: str) -> str:
        path = self.prompt_dir / f"{name}.toon"
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise RuntimeError("Prompt could not be loaded") from error
