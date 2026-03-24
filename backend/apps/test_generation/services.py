import base64
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from apps.test_generation.models import TestCase

MAX_URL_LENGTH = 2000
MAX_HTML_CHARS = 8000
MAX_CRAWL_PAGES = 5
PLAYWRIGHT_TIMEOUT_SECONDS = 20
RUNTIME_SCREENSHOTS_DIR = Path(__file__).resolve().parents[2] / "runtime" / "screenshots"

# Extensions that are assets, not navigable pages
ASSET_EXTENSIONS = {
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".map",
    ".json", ".xml", ".txt", ".pdf", ".zip",
}

logger = logging.getLogger(__name__)


@dataclass
class CrawlPage:
    url: str
    title: str
    html: str
    screenshot_path: str


@dataclass
class GeneratedTest:
    title: str
    description: str
    steps: list[str]


# -------------------------------
# 🛠️ HELPERS
# -------------------------------

def _safe_filename(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)[:80] or "page"


def _is_navigable_url(url: str, base_origin: str) -> bool:
    """
    FIX 1: Only follow same-origin <a href> links that are actual HTML pages.
    Rejects JS bundles, CSS, images, fonts, and any other static assets.
    Previously the crawler was visiting chunk-*.js, styles-*.css, favicon.ico
    which caused Playwright screenshot timeouts and wasted crawl budget.
    """
    try:
        parsed = urlparse(url)
        base_parsed = urlparse(base_origin)

        # Must be http/https
        if parsed.scheme not in ("http", "https"):
            return False

        # Must be same origin
        if parsed.netloc != base_parsed.netloc:
            return False

        # Reject known asset extensions
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in ASSET_EXTENSIONS):
            return False

        return True
    except Exception:
        return False


def _collect_links(base_url: str, page: Any) -> list[str]:
    """
    FIX 1 (continued): Extract links from <a href> only via Playwright,
    not via regex on raw HTML which also picks up script/link/img src tags.
    Filters through _is_navigable_url to exclude assets.
    """
    links = []
    try:
        anchors = page.locator("a[href]").all()
        for anchor in anchors:
            href = anchor.get_attribute("href")
            if not href:
                continue
            absolute = urljoin(base_url, href)
            # Strip fragment — SPAs use fragments for routing but we still
            # want to deduplicate properly
            parsed = urlparse(absolute)
            clean = parsed._replace(fragment="").geturl()
            if _is_navigable_url(clean, base_url):
                links.append(clean)
    except Exception:
        logger.warning("Failed to collect links from page")

    return list(dict.fromkeys(links))  # deduplicate, preserve order


def _load_screenshot_as_base64(path: str) -> str | None:
    """
    FIX 2: Load screenshot bytes and encode as base64 so they can be sent
    to Gemini as vision input. Previously paths were passed as plain strings
    which Gemini cannot read — screenshots were captured but never used by LLM.
    """
    try:
        return base64.b64encode(Path(path).read_bytes()).decode("utf-8")
    except Exception:
        logger.warning("Could not load screenshot for vision: %s", path)
        return None


def _sanitize_html(html: str) -> str:
    return " ".join(html.replace("\n", " ").split())


def _truncate_html(html: str) -> str:
    if len(html) <= MAX_HTML_CHARS:
        return html
    return html[:MAX_HTML_CHARS]


# -------------------------------
# 🔍 CRAWL LAYER
# -------------------------------

def _render_page_snapshot(url: str, screenshot_path: Path, playwright_instance: Any) -> tuple[str, Any]:
    """
    Renders a single page, takes a screenshot, and returns (html, page_handle).
    Reuses a passed-in playwright instance instead of spawning one per page —
    previously each page opened its own browser which was slow and memory-heavy.
    Returns the live page object so _collect_links can use Playwright's DOM
    querying instead of regex on raw HTML.
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    browser = playwright_instance.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        page.goto(
            url,
            wait_until="networkidle",
            timeout=PLAYWRIGHT_TIMEOUT_SECONDS * 1000,
        )

        # Wait for meaningful content — important for hash-routed SPAs
        try:
            page.wait_for_selector("input, button, h1, h2, a", timeout=5000)
        except Exception:
            logger.warning("No interactive elements found on: %s", url)

        page.screenshot(path=str(screenshot_path), full_page=True)
        html = page.content()
        return html, page, context, browser

    except PlaywrightTimeoutError:
        logger.warning("Timeout while loading page: %s", url)
        try:
            context.close()
            browser.close()
        except Exception:
            pass
        raise TimeoutError(f"Page load timed out for {url}")

    except Exception as e:
        logger.exception("Error rendering page: %s", url)
        try:
            context.close()
            browser.close()
        except Exception:
            pass
        raise e


def _crawl_site(start_url: str) -> list[CrawlPage]:
    from playwright.sync_api import sync_playwright

    visited: set[str] = set()
    queue: list[str] = [start_url]
    pages: list[CrawlPage] = []

    RUNTIME_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        while queue and len(pages) < MAX_CRAWL_PAGES:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            filename = f"{len(pages) + 1}_{_safe_filename(current)}.png"
            screenshot_path = RUNTIME_SCREENSHOTS_DIR / filename

            try:
                html, page, context, browser = _render_page_snapshot(
                    current, screenshot_path, playwright
                )
            except Exception:
                logger.exception("Failed to render page during crawl: %s", current)
                continue

            sanitized = _sanitize_html(html)

            title = ""
            match = re.search(r"<title>(.*?)</title>", sanitized, flags=re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()

            # Collect navigable links using Playwright DOM (not regex on raw HTML)
            new_links = _collect_links(current, page)

            try:
                context.close()
                browser.close()
            except Exception:
                logger.warning("Browser cleanup failed for: %s", current)

            pages.append(
                CrawlPage(
                    url=current,
                    title=title,
                    html=_truncate_html(sanitized),
                    screenshot_path=str(screenshot_path),
                )
            )

            for link in new_links:
                if link not in visited and len(pages) + len(queue) < MAX_CRAWL_PAGES:
                    queue.append(link)

    logger.info("Crawled %s page(s) from %s", len(pages), start_url)
    return pages


# -------------------------------
# 🧠 LLM HELPERS
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


def _build_vision_prompt(
    url: str,
    product_description: str,
    key_workflows: list[str],
    pages: list[CrawlPage],
    prompt_template: str,
) -> tuple[str, list[dict]]:
    """
    FIX 2 (continued): Build the text prompt and a separate list of base64
    image parts to be sent together to Gemini as a multimodal request.
    Previously screenshot paths were inlined as plain strings in the text
    prompt — Gemini cannot read file paths and was ignoring them entirely.

    Returns (text_prompt, image_parts) where image_parts is a list of
    Gemini-compatible inline_data dicts ready to attach to the request.
    """
    workflow_text = "\n".join(f"- {w}" for w in key_workflows) if key_workflows else "Not specified"

    # Text summary of each crawled page (no file paths — those go as images)
    page_summaries = []
    for i, page in enumerate(pages, 1):
        page_summaries.append(
            f"--- Page {i} ---\n"
            f"URL: {page.url}\n"
            f"Title: {page.title}\n"
            f"HTML Snapshot:\n{page.html}\n"
            f"(Screenshot {i} attached as image below)"
        )

    text_prompt = (
        prompt_template
        .replace("{url}", url)
        .replace("{product_description}", product_description.strip() or "Not provided")
        .replace("{key_workflows}", workflow_text)
        .replace("{pages}", "\n\n".join(page_summaries))
    )

    # Build base64 image parts for every screenshot that exists on disk
    image_parts = []
    for page in pages:
        b64 = _load_screenshot_as_base64(page.screenshot_path)
        if b64:
            image_parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": b64,
                }
            })
        else:
            logger.warning("Skipping missing screenshot: %s", page.screenshot_path)

    return text_prompt, image_parts


# -------------------------------
# 🚀 MAIN FUNCTION
# -------------------------------

def generate_tests_from_url(
    url: str,
    product_description: str | None = None,
    key_workflows: list[str] | None = None,
) -> list[TestCase]:
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL exceeds maximum allowed length")

    logger.info("Generating tests for URL: %s", url)

    pages = _crawl_site(url)

    if not pages:
        logger.error("Crawl returned no pages — aborting")
        return []

    from apps.core.llm.gemini_client import GeminiClient
    from apps.core.prompt_loader import PromptLoader

    loader = PromptLoader()
    prompt_template = loader.load("test_generation.txt")

    text_prompt, image_parts = _build_vision_prompt(
        url=url,
        product_description=product_description or "",
        key_workflows=key_workflows or [],
        pages=pages,
        prompt_template=prompt_template,
    )

    try:
        client = GeminiClient()
        # FIX 2: Pass both text prompt and image parts so Gemini actually
        # sees the screenshots. Check your GeminiClient.generate_text signature
        # — if it doesn't accept image_parts yet, add that parameter.
        response = client.generate_text(text_prompt, image_parts=image_parts)
        logger.info("LLM response received (%d image(s) sent)", len(image_parts))
    except Exception:
        logger.exception("LLM generation failed")
        raise

    payload = _extract_json(response.text)
    tests = _normalize_tests(payload, response.text)

    if not tests:
        logger.warning("No tests generated")
        return []

    created = []
    screenshot_paths = [p.screenshot_path for p in pages]

    for test in tests:
        created.append(
            TestCase.objects.create(
                source_url=url,
                title=test.title,
                description=test.description,
                steps_json=test.steps,
                steps_text="\n".join(test.steps),
                screenshots_json=screenshot_paths,
                raw_llm_output=response.text,
            )
        )

    logger.info("Generated %s test(s) from %s crawled page(s)", len(created), len(pages))
    return created