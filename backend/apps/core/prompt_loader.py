from pathlib import Path


class PromptLoader:
    def __init__(self, prompts_dir: Path | None = None) -> None:
        self.prompts_dir = prompts_dir or Path(__file__).resolve().parent / "prompts"

    def load(self, name: str) -> str:
        prompt_path = self.prompts_dir / name
        return prompt_path.read_text(encoding="utf-8")
