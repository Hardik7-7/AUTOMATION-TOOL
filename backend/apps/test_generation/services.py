import json
import logging
from dataclasses import dataclass
from typing import Any

from apps.test_generation.models import TestCase

MAX_URL_LENGTH = 2000
PLAYWRIGHT_TIMEOUT_MS = 20000
MIN_INTERACTIVE_ELEMENTS = 1

logger = logging.getLogger(__name__)


@dataclass
class GeneratedTest:
    title: str
    description: str
    steps: list[str]


# -------------------------------
# 🔍 OBSERVATION LAYER
# -------------------------------
def _observe_page(url: str) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT_MS)

            # FIX 1: Explicitly wait for SPA to hydrate before scraping.
            # networkidle alone is not enough for hash-routed SPAs like Vue/React.
            try:
                page.wait_for_selector(
                    "input, button, h1, h2, h3, a",
                    timeout=5000,
                )
            except Exception:
                logger.warning("No interactive elements appeared after waiting — page may be blank")

            data = {
                "url": page.url,
                "title": page.title(),
                "headings": page.locator("h1, h2, h3").all_text_contents(),
                "buttons": [
                    b.strip()
                    for b in page.locator("button").all_text_contents()
                    if b.strip()
                ],
                "links": [
                    {
                        "text": a.inner_text().strip(),
                        "href": a.get_attribute("href") or "",
                    }
                    for a in page.locator("a").all()
                    if a.inner_text().strip()
                ],
                "inputs": [],
                # FIX 2: Also capture visible text labels so the LLM knows
                # what error messages, hints, and descriptions actually exist.
                "visible_labels": [
                    t.strip()
                    for t in page.locator("label, span, p, small").all_text_contents()
                    if t.strip()
                ],
            }

            for inp in page.locator("input").all():
                data["inputs"].append({
                    "name": inp.get_attribute("name"),
                    "placeholder": inp.get_attribute("placeholder"),
                    "type": inp.get_attribute("type"),
                    # FIX 3: Capture aria-label too — SPAs often skip name/placeholder
                    "aria_label": inp.get_attribute("aria-label"),
                })

            logger.info("Observed page data:\n%s", json.dumps(data, indent=2))
            return data

        finally:
            try:
                context.close()
                browser.close()
            except Exception:
                logger.warning("Browser cleanup failed")


# -------------------------------
# 🧠 LLM JSON EXTRACTION
# -------------------------------
def _extract_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


# -------------------------------
# 🧪 NORMALIZATION
# -------------------------------
def _normalize_tests(payload: dict[str, Any] | None, raw_text: str) -> list[GeneratedTest]:
    if not payload or "tests" not in payload:
        logger.warning("Invalid LLM response format")
        return []

    tests = []

    for entry in payload.get("tests", []):
        title = str(entry.get("title", "Generated Test")).strip()
        description = str(entry.get("description", "")).strip()

        steps = entry.get("steps", [])
        if not isinstance(steps, list):
            steps = [str(steps)]

        steps = [str(step).strip() for step in steps if str(step).strip()]

        if steps:
            tests.append(GeneratedTest(title, description, steps))

    return tests


# -------------------------------
# 🚨 VALIDATION (ANTI-HALLUCINATION)
# -------------------------------

# UI-specific keywords the LLM might hallucinate.
# If a step mentions one of these, it MUST be grounded in observed page data.
_UI_SIGNAL_WORDS = {
    "button", "link", "input", "field", "checkbox", "dropdown",
    "click", "select", "check", "navigate", "verify", "label",
    "heading", "title", "placeholder", "text", "icon", "modal",
    "redirect", "url", "page",
}


def _page_data_corpus(page_data: dict) -> set[str]:
    """
    Build a set of meaningful tokens from observed page data.
    Only includes tokens longer than 2 chars to avoid false positives
    from common short words like 'to', 'in', 'a'.
    """
    raw = json.dumps(page_data).lower()
    return {token for token in raw.split() if len(token) > 2}


def _step_references_unobserved_ui(step: str, corpus: set[str]) -> bool:
    """
    Returns True if a step makes a UI claim that isn't grounded in page_data.

    Strategy: extract quoted strings from the step (e.g. 'Forgot Password?',
    'Sign Up') — these are explicit UI label references. If any quoted label
    has NO token overlap with the observed corpus, the step is hallucinated.
    """
    import re

    # Extract all quoted strings — these are explicit UI element references
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", step)

    for label in quoted:
        label_tokens = {t for t in label.lower().split() if len(t) > 2}
        if label_tokens and label_tokens.isdisjoint(corpus):
            logger.debug(
                "Hallucination detected — quoted label '%s' not in page corpus", label
            )
            return True

    return False


def _validate_tests(
    tests: list[GeneratedTest], page_data: dict
) -> list[GeneratedTest]:
    # FIX 4: Abort immediately if page scrape returned nothing useful.
    has_buttons = bool(page_data.get("buttons"))
    has_inputs = bool(page_data.get("inputs"))
    has_links = bool(page_data.get("links"))

    if not (has_buttons or has_inputs or has_links):
        logger.error(
            "Page data has no interactive elements — scrape likely failed, rejecting all tests"
        )
        return []

    corpus = _page_data_corpus(page_data)
    valid_tests = []

    for test in tests:
        valid_steps = []

        for step in test.steps:
            # FIX 5: Reject steps that reference quoted UI labels not in page corpus.
            # This catches hallucinated button/link names like 'Forgot Password?'
            # or 'Sign Up' that don't exist on the actual page.
            if _step_references_unobserved_ui(step, corpus):
                logger.warning("Dropping hallucinated step: %s", step)
                continue

            valid_steps.append(step)

        if valid_steps:
            test.steps = valid_steps
            valid_tests.append(test)
        else:
            logger.warning("Dropping fully hallucinated test: '%s'", test.title)

    return valid_tests


# -------------------------------
# 🚀 MAIN FUNCTION
# -------------------------------
def generate_tests_from_url(url: str) -> list[TestCase]:
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL exceeds maximum allowed length")

    logger.info("Generating tests for URL: %s", url)

    # 🔍 Step 1: Observe page
    try:
        page_data = _observe_page(url)
    except Exception:
        logger.exception("Failed to observe page")
        page_data = {}

    if not page_data:
        logger.error("No page data found — aborting test generation")
        return []

    # 🧠 Step 2: Prepare prompt
    from apps.core.llm.gemini_client import GeminiClient
    from apps.core.prompt_loader import PromptLoader

    loader = PromptLoader()
    prompt_template = loader.load("test_generation.txt")

    # FIX 6: Inject a strict grounding instruction so the LLM knows
    # it must not invent UI elements beyond what's in page_data.
    grounding_note = (
        "IMPORTANT: Only generate test steps that reference UI elements "
        "explicitly present in the page_data provided. "
        "Do NOT invent buttons, links, labels, error messages, URLs, or "
        "text that are not listed in page_data. "
        "If an element is not observed, do not reference it."
    )

    prompt = (
        prompt_template
        .replace("{url}", url)
        .replace("{page_data}", json.dumps(page_data, indent=2))
        .replace("{grounding_note}", grounding_note)
    )

    # 🤖 Step 3: Call LLM
    try:
        client = GeminiClient()
        response = client.generate_text(prompt)
        logger.info("LLM Response:\n%s", response.text)
    except Exception:
        logger.exception("LLM generation failed")
        raise

    # 🧪 Step 4: Parse + normalize
    payload = _extract_json(response.text)
    tests = _normalize_tests(payload, response.text)

    # 🚨 Step 5: Validate against observed data
    tests = _validate_tests(tests, page_data)

    if not tests:
        logger.warning("All generated tests were filtered out (hallucination likely)")
        return []

    # 💾 Step 6: Save
    created = []

    for test in tests:
        created.append(
            TestCase.objects.create(
                source_url=url,
                title=test.title,
                description=test.description,
                steps_json=test.steps,
                steps_text="\n".join(test.steps),
                raw_llm_output=response.text,
            )
        )

    logger.info("Generated %s valid test(s)", len(created))
    return created