import asyncio
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from pyquery import PyQuery as pq

BASE_URL = "https://www.w3schools.com/"


# ---------------------------
# Helper: determine tutorial name
# ---------------------------
def extract_tutorial_name(url: str) -> str:
    lower = url.lower()
    for name in ["python", "html", "css", "js", "sql", "java", "cs", "php"]:
        if f"/{name}/" in lower:
            return name.upper() + " Tutorial"
    return "General"


# ---------------------------
# Helper: extract menu links (sidebar only)
# ---------------------------
def extract_menu_links(doc: pq, base_url: str) -> list:
    """Extract links from tutorial left menu/sidebar and resolve to absolute URLs."""
    links = []
    seen = set()
    for a in doc("#leftmenuinner a, .w3-sidebar a").items():
        href = a.attr("href")
        text = a.text().strip()
        if not href or not text:
            continue
        full_url = urljoin(base_url, href)
        if full_url in seen:
            continue
        if "campus.w3schools.com" in full_url or "/cart" in full_url:
            continue  # skip shop links
        seen.add(full_url)
        links.append({"title": text, "url": full_url})
    return links


# ---------------------------
# Helper: extract code snippets
# ---------------------------
def extract_code_snippets(doc: pq) -> list:
    snippets = []
    code_selectors = ["div.w3-example pre", "div.w3-code"]
    seen = set()

    for sel in code_selectors:
        for el in doc(sel).items():
            text = el.text() or ""
            html = el.html() or ""
            if not text.strip():
                continue
            fingerprint = (len(text), html[:50])
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            snippets.append({"text": text.strip(), "html": html.strip()})
    return snippets


# ---------------------------
# Main crawler
# ---------------------------
async def main():
    run_config = CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True,
    )

    tutorials = defaultdict(list)

    async with AsyncWebCrawler(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        browser_args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
        wait_for="document.querySelector('h1') || document.querySelector('.w3-example')",
    ) as crawler:
        try:
            # Step 1: Get tutorials index page
            results = await crawler.arun(
                url="https://www.w3schools.com/tutorials/index.php",
                config=run_config,
            )

            for result in results:
                if not getattr(result, "html", None):
                    continue

                doc = pq(result.html)

                # Step 2: Extract tutorial entry links
                tutorial_links = [a.attr("href") for a in doc(".w3-row .w3-col a").items() if a.attr("href")]

                for tut_link in tutorial_links:
                    tut_url = urljoin(BASE_URL, tut_link)
                    tut_results = await crawler.arun(url=tut_url, config=run_config)

                    for tut in tut_results:
                        if not getattr(tut, "html", None):
                            continue
                        tut_doc = pq(tut.html)

                        tutorial_name = extract_tutorial_name(tut_url)
                        menu_links = extract_menu_links(tut_doc, tut_url)

                        # Step 3: Crawl subpages (sidebar links)
                        for link in menu_links:
                            sub_url = link["url"]
                            sub_results = await crawler.arun(url=sub_url, config=run_config)

                            for sub in sub_results:
                                if not getattr(sub, "html", None):
                                    continue
                                sub_doc = pq(sub.html)
                                title = sub_doc("h1").text().strip() or link["title"]

                                code_snippets = extract_code_snippets(sub_doc)

                                if code_snippets:
                                    page_info = {
                                        "title": title,
                                        "url": sub_url,
                                        "code_snippets": code_snippets,
                                    }
                                    tutorials[tutorial_name].append(page_info)
                                    print(f"📘 {tutorial_name} - {title} ({len(code_snippets)} examples)")

        except Exception as e:
            print(f"❌ Crawl failed: {e}")

    # Save JSON
    out_file = Path("W3Results.json")
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(tutorials, f, ensure_ascii=False, indent=2)
    print(f"✅ Done! Saved tutorials to '{out_file.resolve()}'")


if __name__ == "__main__":
    asyncio.run(main())
