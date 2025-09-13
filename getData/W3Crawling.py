import asyncio
import json
import logging
from pathlib import Path
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from pyquery import PyQuery as pq


BASE_URL = "https://www.w3schools.com/tutorials/index.php"
OUTPUT_DIR = Path("W3_Tutorials")
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename="crawl_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def extract_code_snippets(doc: pq) -> list:
    snippets, seen = [], set()
    for sel in ["div.w3-example pre", "div.w3-code"]:
        for el in doc(sel).items():
            text = el.text() or ""
            html = el.html() or ""
            if not text.strip():
                continue
            fp = (len(text), html[:50])
            if fp in seen:
                continue
            seen.add(fp)
            snippets.append({"text": text.strip(), "html": html.strip()})
    return snippets


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


async def crawl_language(crawler, run_config, lang_name: str, tut_url: str):
    tutorials = []

    try:
        tut_results = await crawler.arun(url=tut_url, config=run_config)
    except Exception as e:
        logging.error(f"❌ Failed to open {lang_name} main page: {e}")
        return

    for tut in tut_results:
        if not getattr(tut, "html", None):
            continue
        tut_doc = pq(tut.html)
        menu_links = extract_menu_links(tut_doc, tut_url)

        for link in menu_links:
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
                title = sub_doc("h1").text().strip() or link["title"]

                code_snippets = extract_code_snippets(sub_doc)
                if code_snippets:
                    tutorials.append(
                        {
                            "title": title,
                            "code": code_snippets,
                            "metadata": {"url": sub_url},
                        }
                    )
                    logging.info(f"{lang_name}: {title} ({len(code_snippets)} examples)")

    out_file = OUTPUT_DIR / f"{lang_name}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump({"language": lang_name, "tutorials": tutorials}, f, indent=2, ensure_ascii=False)
    logging.info(f"✅ Saved {lang_name} tutorials to {out_file.resolve()}")


async def main():
    run_config = CrawlerRunConfig(scraping_strategy=LXMLWebScrapingStrategy(), verbose=True)

    async with AsyncWebCrawler(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0.0.0 Safari/537.36",
        browser_args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        wait_for="document.querySelector('h1') || document.querySelector('.w3-example')",
    ) as crawler:
        # Get all tutorial links from the main Tutorials page
        results = await crawler.arun(url=BASE_URL, config=run_config)
        if not results:
            logging.error("Could not load tutorial index page.")
            return

        doc = pq(results[0].html)
        tutorial_links = extract_menu_links(doc, BASE_URL)

        for link in tutorial_links:
            lang_name = link["title"].split()[0].upper()
            tut_url = link["url"]
            await crawl_language(crawler, run_config, lang_name, tut_url)
            await asyncio.sleep(1)  # throttle to avoid rate limiting


if __name__ == "__main__":
    asyncio.run(main())
