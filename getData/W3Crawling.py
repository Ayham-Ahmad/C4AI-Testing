# w3_multi_crawler_template.py
import asyncio
import json
import logging
from pathlib import Path
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from pyquery import PyQuery as pq

# ---------- CONFIG ----------
COURSES = {
    "python": "https://www.w3schools.com/python/default.asp",
    "html": "https://www.w3schools.com/html/default.asp",
    "css": "https://www.w3schools.com/css/default.asp",
}
OUTPUT_DIR = Path("W3_Tutorials")
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename="crawl_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def extract_code_snippets(doc: pq) -> list:
    snippets, seen = [], set()
    for sel in ["div.w3-example pre", "div.w3-code", "pre", "code"]:
        for el in doc(sel).items():
            text = el.text() or ""
            if not text.strip():
                continue
            fp = (len(text), text[:50])
            if fp in seen:
                continue
            seen.add(fp)
            snippets.append(text.strip())
    return snippets


def extract_summary(doc: pq) -> str:
    """
    Extract tutorial content text only from the main content div.
    """
    main = doc("#main") or doc(".w3-main") or doc("body")
    parts = []
    for el in main("h2, h3, p, li").items():
        text = el.text().strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def extract_description(doc: pq) -> str:
    """
    Extract description: first few <p> elements in the main content.
    """
    main = doc("#main") or doc(".w3-main") or doc("body")
    desc_parts = []
    for el in main("p").items():
        text = el.text().strip()
        if text:
            desc_parts.append(text)
        if len(" ".join(desc_parts)) > 900:  # limit ~1000 chars
            break
    return " ".join(desc_parts)[:1000]


def extract_menu_links(doc: pq, base_url: str) -> list:
    links, seen = [], set()
    for a in doc("#leftmenuinner a").items():
        href, text = a.attr("href"), a.text().strip()
        if not href or not text:
            continue
        full_url = urljoin(base_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        links.append({"title": text, "url": full_url})
    return links


async def crawl_course(crawler, run_config, course_name: str, tut_url: str):
    course_summary = []
    description = ""

    try:
        tut_result = await crawler.arun(url=tut_url, config=run_config)
    except Exception as e:
        logging.error(f"❌ Failed to open {course_name} tutorial main page: {e}")
        return

    for tut in tut_result:
        if not getattr(tut, "html", None):
            continue
        tut_doc = pq(tut.html)
        menu_links = extract_menu_links(tut_doc, tut_url)

        for idx, link in enumerate(menu_links[:5]):  # first 5 for testing
            sub_url = link["url"]
            try:
                sub_results = await crawler.arun(url=sub_url, config=run_config)
            except Exception as e:
                logging.error(f"Failed {sub_url}: {e}")
                continue

            for sub in sub_results:
                if not getattr(sub, "html", None):
                    continue
                sub_doc = pq(sub.html)

                if idx == 0:
                    description = extract_description(sub_doc)
                    continue

                title = sub_doc("h1").text().strip() or link["title"]
                summary = extract_summary(sub_doc)
                examples = extract_code_snippets(sub_doc)

                course_summary.append(
                    {
                        "title": title,
                        "summary": summary,
                        "examples": examples,
                    }
                )

                logging.info(f"{course_name.upper()}: {title} ({len(examples)} examples)")

    out_data = {
        "course_name": course_name.capitalize(),
        "description": description,
        "course_summary": course_summary,
        "glossary": [],  # leave empty
    }

    out_file = OUTPUT_DIR / f"{course_name}_first5.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)
    logging.info(f"✅ Saved {course_name} tutorials to {out_file.resolve()}")


async def main():
    run_config = CrawlerRunConfig(scraping_strategy=LXMLWebScrapingStrategy(), verbose=True)

    async with AsyncWebCrawler(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0.0.0 Safari/537.36",
        browser_args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        wait_for="document.querySelector('h1') || document.querySelector('.w3-example')",
    ) as crawler:
        for name, url in COURSES.items():
            await crawl_course(crawler, run_config, name, url)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
