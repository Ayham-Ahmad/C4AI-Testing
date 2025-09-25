# w3_multi_crawler_template.py
import asyncio
import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin
from typing import Optional

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from pyquery import PyQuery as pq

# ---------- CONFIG ----------
INDEX_URL = "https://www.w3schools.com/bootstrap5/index.php"
OUTPUT_DIR = Path("W3_Tutorials_ALL")
OUTPUT_DIR.mkdir(exist_ok=True)

# How many courses to discover from the tutorials index (set to None for no limit)
COURSE_LIMIT = 20

# How many sections to crawl per course (set to None to crawl ALL sections)
SECTIONS_LIMIT = 3

# Crawler settings (throttle)
DELAY_BETWEEN_COURSES = 1.0  # seconds

logging.basicConfig(
    filename="crawl_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# ---------- FILTERS / CLEANUP ----------
STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "these", "those",
    "click", "here", "your", "about", "into", "over", "under", "while",
    "example", "examples", "tutorial", "introduction", "learn", "default"
}
JUNKWORDS = {"sales", "services", "contact", "analytics", "certificate", "certificates", "subscribe"}
BAD_TERMS = {
    "tutorial", "tutorials", "tip", "tips", "spaces", "w3", "w3css", "w3 css",
    "w3schools", "navbar", "vertical", "building", "web building",
    "default", "introduction", "learn", "overview", "home", "reference", "references"
}


def sanitize_filename(name: str) -> str:
    """Make a filesystem-safe lower_snake filename for the course."""
    n = name.strip().lower()
    n = re.sub(r"[^\w\s-]", "", n)   # remove punctuation
    n = re.sub(r"\s+", "_", n)       # spaces -> underscore
    n = n.strip("_")
    if not n:
        n = "course"
    return n


def clean_word(text: str) -> Optional[str]:
    """
    Clean and filter a candidate glossary word/phrase.
    Returns a normalized word (lowercase) or None if rejected.
    """
    if not text:
        return None
    w = text.strip().lower()
    # replace other chars with space, allow a-z0-9 + # - .
    w = re.sub(r"[^a-z0-9+#\-\.\s]", " ", w)
    w = re.sub(r"\s+", " ", w).strip()

    if len(w) < 2 or len(w) > 50:
        return None

    tokens = w.split()
    if len(tokens) > 2:
        return None

    if w in BAD_TERMS:
        return None
    if any(tok in STOPWORDS for tok in tokens):
        return None
    if any(tok in JUNKWORDS for tok in tokens):
        return None

    if not re.search(r"[a-z]", w):
        return None

    return w


# ---------- EXTRACTORS ----------
def extract_menu_links(doc: pq, base_url: str) -> list:
    """Return list of {title, url} for section links in the left menu of a course page."""
    links, seen = [], set()
    for a in doc("#leftmenuinner a").items():
        href = a.attr("href")
        text = a.text().strip()
        if not href or not text:
            continue
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        full = urljoin(base_url, href)
        if full in seen:
            continue
        seen.add(full)
        links.append({"title": text, "url": full})
    return links


def extract_code_snippets(doc: pq) -> list:
    snippets, seen = [], set()
    for sel in ["div.w3-example pre", "div.w3-code", "pre", "code"]:
        for el in doc(sel).items():
            text = el.text() or ""
            if not text.strip():
                continue
            fp = (len(text), text[:80])
            if fp in seen:
                continue
            seen.add(fp)
            snippets.append(text.strip())
    return snippets


def extract_description(doc: pq) -> str:
    """Take the first meaningful paragraphs from the main content as description."""
    main = doc("#main") or doc(".w3-main") or doc("body")
    parts = []
    for p in main("p").items():
        t = p.text().strip()
        if t:
            parts.append(t)
        if len(" ".join(parts)) > 900:
            break
    return " ".join(parts)[:1000]


def extract_summary(doc: pq) -> str:
    """Extract h2/h3/p/li text inside the article/main area for the page summary."""
    main = doc("#main") or doc(".w3-main") or doc("body")
    parts = []
    for el in main("h2, h3, p, li").items():
        t = el.text().strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def extract_glossary(doc: pq, menu_links: list) -> list:
    """Collect candidate glossary words from headings + menu + code + strong, then clean and limit."""
    raw = set()

    for el in doc("h1, h2, h3, strong, b, code").items():
        w = clean_word(el.text())
        if w:
            raw.add(w)

    for link in menu_links:
        w = clean_word(link["title"])
        if w:
            raw.add(w)

    glossary = sorted(raw)
    return glossary[:400]


def extract_objectives(doc: pq) -> list:
    """Extracts learning objectives (e.g., first bullet list after h1)."""
    main = doc("#main") or doc(".w3-main") or doc("body")
    objectives = []
    ul = main("h1").next_all("ul").eq(0)
    for li in ul("li").items():
        txt = li.text().strip()
        if txt:
            objectives.append(txt)
    return objectives[:10]


# ---------- OBJECTIVE EXTRACTION HANDLER ----------
def extract_objectives(doc: pq) -> list:
    """
    Extract learning objectives:
    - Look for the first bullet list (<ul>) in #main that has at least 2 items
    - Fall back to the first few <li> in #main
    """
    main = doc("#main") or doc(".w3-main") or doc("body")
    objectives = []

    # try first non-trivial <ul> in main
    for ul in main("ul").items():
        lis = [li.text().strip() for li in ul("li").items() if li.text().strip()]
        if len(lis) >= 2:  # consider it objectives only if >1 items
            objectives = lis
            break

    # fallback: grab first 5 <li> in main
    if not objectives:
        objectives = [li.text().strip() for li in main("li").items() if li.text().strip()][:5]

    return objectives[:10]



def get_course_objectives(tut_doc: pq) -> list:
    """
    Wrapper around extract_objectives.
    Provides a single place to modify or extend objective logic later.
    """
    return extract_objectives(tut_doc)


async def process_objectives_for_file(filepath: Path, crawler: AsyncWebCrawler, run_config: CrawlerRunConfig):
    """
    Process a single course file: fetch HTML, extract objectives,
    and update the JSON file in place.
    """
    with filepath.open("r", encoding="utf-8") as infile:
        data = json.load(infile)

    if "objectives" in data:
        print(f"⏭️ Skipping {filepath.name}, already has objectives")
        return

    url = data.get("course_url")
    if not url:
        print(f"⚠️ No course_url in {filepath.name}, skipping")
        return

    results = await crawler.arun(url=url, config=run_config)
    tut_html = next((r.html for r in results if getattr(r, "html", None)), None)

    if not tut_html:
        print(f"❌ No HTML for {url}")
        return

    tut_doc = pq(tut_html)
    data["objectives"] = get_course_objectives(tut_doc)

    with filepath.open("w", encoding="utf-8") as outfile:
        json.dump(data, outfile, indent=2, ensure_ascii=False)

    print(f"✅ Updated {filepath.name} with {len(data['objectives'])} objectives")


async def add_objectives():
    """
    Iterate over all course files and update them with objectives if missing.
    """
    run_config = CrawlerRunConfig(scraping_strategy=LXMLWebScrapingStrategy(), verbose=False)
    async with AsyncWebCrawler() as crawler:
        for f in OUTPUT_DIR.glob("*.json"):
            await process_objectives_for_file(f, crawler, run_config)


# ---------- CRAWLING LOGIC ----------
async def crawl_course(crawler: AsyncWebCrawler, run_config: CrawlerRunConfig, course_name: str, tut_url: str):
    filename = sanitize_filename(course_name) + ".json"
    out_file = OUTPUT_DIR / filename

    logging.info(f"➡️  Crawling course: {course_name} -> {tut_url}")

    try:
        results = await crawler.arun(url=tut_url, config=run_config)
    except Exception as e:
        logging.error(f"❌ Failed to fetch course root {tut_url}: {e}")
        return

    tut_html = next((r.html for r in results if getattr(r, "html", None)), None)
    if not tut_html:
        logging.warning(f"❌ No HTML for {tut_url}")
        return

    tut_doc = pq(tut_html)

    menu_links = extract_menu_links(tut_doc, tut_url)
    glossary = extract_glossary(tut_doc, menu_links)

    description = ""
    objectives = []
    course_summary = []

    for idx, link in enumerate(menu_links):
        section_url = link["url"]

        try:
            sec_results = await crawler.arun(url=section_url, config=run_config)
        except Exception as e:
            logging.warning(f"Failed to fetch section {section_url}: {e}")
            continue

        sec_html = next((sr.html for sr in sec_results if getattr(sr, "html", None)), None)
        if not sec_html:
            logging.warning(f"No HTML for section {section_url}")
            continue

        sec_doc = pq(sec_html)

        if idx == 0:
            # ✅ Only extract description + objectives from FIRST section
            description = extract_description(sec_doc)
            objectives = get_course_objectives(sec_doc)
            logging.info(f"   • Description extracted ({len(description)} chars)")
            logging.info(f"   • Objectives extracted ({len(objectives)} items)")
            break   # ⛔ stop after first section


        title = sec_doc("h1").text().strip() or link.get("title", "")
        summary = extract_summary(sec_doc)
        examples = extract_code_snippets(sec_doc)

        course_summary.append({
            "title": title or link.get("title", ""),
            "summary": summary,
            "examples": examples
        })
        logging.info(f"   • Section: {title} ({len(examples)} examples)")

    out = {
        "course_name": course_name,
        "description": description,
        "course_summary": course_summary,
        "glossary": glossary,
        "objectives": objectives,   # ✅ now pulled from first section only
    }

    try:
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ Saved {course_name} -> {out_file.name}")
    except Exception as e:
        logging.error(f"❌ Failed to write file {out_file}: {e}")




async def main():
    run_config = CrawlerRunConfig(scraping_strategy=LXMLWebScrapingStrategy(), verbose=True)

    async with AsyncWebCrawler(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0.0.0 Safari/537.36",
        browser_args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        wait_for="document.querySelector('h1') || document.querySelector('.w3-example')",
    ) as crawler:

        try:
            idx_results = await crawler.arun(url=INDEX_URL, config=run_config)
        except Exception as e:
            logging.error(f"Failed to fetch index {INDEX_URL}: {e}")
            return

        index_html = None
        for r in idx_results:
            if getattr(r, "html", None):
                index_html = r.html
                break
        if not index_html:
            logging.error("No HTML for tutorials index page")
            return

        index_doc = pq(index_html)

        courses = {}
        for a in index_doc("#leftmenuinnerinner a.no-checkmark, #leftmenuinnerinner a").items():
            href = a.attr("href")
            text = a.text().strip()
            if not href or not text:
                continue
            full = urljoin(INDEX_URL, href)
            name_key = text.strip()
            if name_key not in courses:
                courses[name_key] = full

        logging.info(f"Discovered {len(courses)} courses")
        print(f"Discovered {len(courses)} courses")

        for name, url in courses.items():
            fname = sanitize_filename(name) + ".json"
            # if (OUTPUT_DIR / fname).exists():
            #     logging.info(f"⏭️ Skipping {name} (file exists: {fname})")
            #     print(f"⏭️ Skipping {name} (file exists: {fname})")
            #     continue

            await crawl_course(crawler, run_config, name, url)
            await asyncio.sleep(DELAY_BETWEEN_COURSES)


if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.run(add_objectives())
