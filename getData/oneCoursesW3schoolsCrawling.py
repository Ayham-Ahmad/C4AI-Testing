# single_course_crawler.py
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
COURSE_URL = "https://www.w3schools.com/c/index.php"   # 👈 Paste your course link here
COURSE_NAME = "C"
OUTPUT_DIR = Path("W3_Tutorials_SINGLE")
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename="crawl_log_single.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ---------- FILTERS ----------
STOPWORDS = {
    "the","and","for","with","from","this","that","these","those",
    "click","here","your","about","into","over","under","while",
    "example","examples","tutorial","introduction","learn","default"
}
JUNKWORDS = {"sales","services","contact","analytics","certificate","certificates","subscribe"}
BAD_TERMS = {
    "tutorial","tutorials","tip","tips","spaces","w3","w3css","w3 css",
    "w3schools","navbar","vertical","building","web building",
    "default","introduction","learn","overview","home","reference","references"
}

# ---------- HELPERS ----------
def sanitize_filename(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r"[^\w\s-]", "", n)
    n = re.sub(r"\s+", "_", n)
    return n.strip("_") or "course"

def clean_word(text: str) -> Optional[str]:
    if not text:
        return None
    w = text.strip().lower()
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

def extract_menu_links(doc: pq, base_url: str) -> list:
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

def extract_description(doc: pq) -> str:
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
    main = doc("#main") or doc(".w3-main") or doc("body")
    parts = []
    for el in main("h2, h3, p, li").items():
        t = el.text().strip()
        if t:
            parts.append(t)
    return "\n".join(parts)

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

def extract_objectives(doc: pq) -> list:
    main = doc("#main") or doc(".w3-main") or doc("body")
    for ul in main("ul").items():
        lis = [li.text().strip() for li in ul("li").items() if li.text().strip()]
        if len(lis) >= 2:
            return lis[:10]
    return [li.text().strip() for li in main("li").items() if li.text().strip()][:5]

def extract_glossary(doc: pq, menu_links: list) -> list:
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

# ---------- CRAWLER ----------
async def crawl_single_course(course_name: str, course_url: str):
    run_config = CrawlerRunConfig(scraping_strategy=LXMLWebScrapingStrategy(), verbose=True)
    filename = sanitize_filename(course_name) + ".json"
    out_file = OUTPUT_DIR / filename

    async with AsyncWebCrawler(
        user_agent="Mozilla/5.0",
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"],
        wait_for="document.querySelector('h1') || document.querySelector('.w3-example')",
    ) as crawler:

        results = await crawler.arun(url=course_url, config=run_config)
        tut_html = next((r.html for r in results if getattr(r, "html", None)), None)
        if not tut_html:
            print(f"❌ Failed to load {course_url}")
            return

        tut_doc = pq(tut_html)
        menu_links = extract_menu_links(tut_doc, course_url)
        glossary = extract_glossary(tut_doc, menu_links)

        description, objectives, course_summary = "", [], []

        for idx, link in enumerate(menu_links):
            section_url = link["url"]
            sec_results = await crawler.arun(url=section_url, config=run_config)
            sec_html = next((r.html for r in sec_results if getattr(r, "html", None)), None)
            if not sec_html:
                continue

            sec_doc = pq(sec_html)
            title = sec_doc("h1").text().strip() or link.get("title", "")
            summary = extract_summary(sec_doc)
            examples = extract_code_snippets(sec_doc)

            if idx == 0:
                description = extract_description(sec_doc)
                objectives = extract_objectives(sec_doc)

            course_summary.append({
                "title": title,
                "summary": summary,
                "examples": examples
            })

            print(f"✅ Section: {title} ({len(examples)} examples)")

        out = {
            "course_name": course_name,
            "course_url": course_url,
            "description": description,
            "course_summary": course_summary,
            "glossary": glossary,
            "objectives": objectives, 
        }

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)

        print(f"🎉 Done! Saved -> {out_file.name}")

# ---------- MAIN ----------
if __name__ == "__main__":
    asyncio.run(crawl_single_course(COURSE_NAME, COURSE_URL))
