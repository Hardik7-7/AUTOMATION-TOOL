import logging
import subprocess
import sys
from datetime import datetime, timezone

from apps.code_generation.models import TestScript
from apps.code_generation.services import generate_script_for_test
from apps.core.llm.gemini_client import GeminiClient
from apps.test_generation.models import TestCase
from apps.test_runner.models import TestRun


LOG_SNIPPET_CHARS = 500
MAX_RETRIES = 2
logger = logging.getLogger(__name__)


def _combine_logs(stdout: str, stderr: str) -> str:
    return f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"


def analyze_failure(test_run_id: int) -> None:
    test_run = TestRun.objects.get(id=test_run_id)
    logs = test_run.logs or ""
    if not logs.strip():
        test_run.failure_type = "unknown"
        test_run.failure_summary = "No logs available to analyze."
        test_run.save(update_fields=["failure_type", "failure_summary"])
        return

    prompt = (
        "Given the following Playwright test execution logs, classify the failure into one of:\n"
        "1. test automation issue (wrong selector, wait, script logic)\n"
        "2. product bug (application behavior incorrect)\n"
        "3. infrastructure/flaky issue (timeouts, network, intermittent)\n\n"
        "Also provide a short reason and suggestion.\n\n"
        f"Logs:\n{logs}\n"
    )

    client = GeminiClient()
    response = client.generate_text(prompt)
    text = response.text.strip()

    failure_type = "unknown"
    lowered = text.lower()
    if "automation" in lowered:
        failure_type = "test_automation_issue"
    elif "product bug" in lowered or "application" in lowered:
        failure_type = "product_bug"
    elif "infrastructure" in lowered or "flaky" in lowered or "timeout" in lowered:
        failure_type = "infrastructure_flaky_issue"

    test_run.failure_type = failure_type
    test_run.failure_summary = text
    test_run.save(update_fields=["failure_type", "failure_summary"])


def _run_script(script_path: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
    )
    return result.returncode, _combine_logs(result.stdout, result.stderr)


def run_test_by_case_id(test_id: int) -> tuple[TestRun, str]:
    test_case = TestCase.objects.get(id=test_id)

    test_run = TestRun.objects.create(
        test_case=test_case,
        status=TestRun.STATUS_RUNNING,
        started_at=datetime.now(timezone.utc),
        retry_count=0,
    )

    attempt = 0
    aggregated_logs = []

    while attempt <= MAX_RETRIES:
        logger.info("Attempt %s of %s for test_id=%s", attempt + 1, MAX_RETRIES + 1, test_id)

        script = (
            TestScript.objects.filter(test_case=test_case)
            .order_by("-created_at")
            .first()
        )
        if not script:
            raise FileNotFoundError("No TestScript found for this test case")

        try:
            return_code, logs = _run_script(script.script_path)
        except Exception as exc:
            logs = f"Execution failed: {exc}"
            return_code = 1

        aggregated_logs.append(f"--- Attempt {attempt + 1} ---\n{logs}")
        test_run.logs = "\n\n".join(aggregated_logs)

        if return_code == 0:
            test_run.status = TestRun.STATUS_PASSED
            test_run.completed_at = datetime.now(timezone.utc)
            test_run.save(update_fields=["logs", "completed_at", "status"])
            break

        test_run.status = TestRun.STATUS_FAILED
        test_run.completed_at = datetime.now(timezone.utc)
        test_run.save(update_fields=["logs", "completed_at", "status"])

        analyze_failure(test_run.id)

        if test_run.failure_type != "test_automation_issue":
            logger.info("Not retrying: failure_type=%s", test_run.failure_type)
            break

        if test_run.retry_count >= MAX_RETRIES:
            logger.info("Max retries reached for test_id=%s", test_id)
            break

        logger.info("Retrying test due to automation issue...")
        logger.info("Regenerating script...")
        generate_script_for_test(test_id)

        test_run.retry_count += 1
        test_run.save(update_fields=["retry_count"])
        attempt += 1

    snippet = (test_run.logs or "")[:LOG_SNIPPET_CHARS]
    return test_run, snippet
