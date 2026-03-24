import re
from pathlib import Path

from apps.code_generation.models import TestScript
from apps.core.llm.gemini_client import GeminiClient
from apps.core.prompt_loader import PromptLoader
from apps.test_generation.models import TestCase


RUNTIME_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "runtime" / "scripts"


def _extract_python_code(text: str) -> str:
    match = re.search(r"```python(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"```(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def generate_script_for_test(test_id: int) -> TestScript:
    test_case = TestCase.objects.get(id=test_id)
    if test_case.status != TestCase.STATUS_APPROVED:
        raise ValueError("Test must be approved before code generation")

    loader = PromptLoader()
    prompt_template = loader.load("code_generation.txt")
    prompt = (
        prompt_template.replace("{url}", test_case.source_url)
        .replace("{title}", test_case.title)
        .replace("{description}", test_case.description)
        .replace("{steps}", "\n".join(test_case.steps_json or []))
    )

    client = GeminiClient()
    response = client.generate_text(prompt)
    code = _extract_python_code(response.text)

    RUNTIME_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    script_path = RUNTIME_SCRIPTS_DIR / f"test_{test_case.id}.py"
    script_path.write_text(code, encoding="utf-8")

    return TestScript.objects.create(
        test_case=test_case,
        script_path=str(script_path),
    )
