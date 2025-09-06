# Requirements: pip install crawl4ai lxml

import asyncio
import json
from datetime import datetime
from lxml import html
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    DomainFilter,
    ContentTypeFilter
)

# Keywords to score pages
AI_KEYWORDS = [
    "machine learning", "deep learning", "neural network", "artificial intelligence",
    "transformer", "reinforcement learning", "nlp", "computer vision"
]

# Score pages based on keyword presence
def score_ai_papers(result):
    text = ""
    if hasattr(result, "text_content"):
        text = result.text_content() if callable(result.text_content) else (result.text_content or "")
    text = text.lower()
    score = sum(kw in text for kw in AI_KEYWORDS)
    return score / len(AI_KEYWORDS)

# Extract best-guess title
def extract_title(result):
    title = getattr(result, "title", "")
    if not title and hasattr(result, "text_content"):
        text = result.text_content() if callable(result.text_content) else (result.text_content or "")
        lines = text.strip().splitlines()
        if lines:
            title = lines[0][:200]
    return title.strip()

# Extract structured metadata using lxml
def extract_metadata(result):
    metadata = {
        "url": result.url,
        "title": extract_title(result),
        "abstract": "",
        "authors": "",
        "pdf_url": "",
        "year": "",
        "depth": result.metadata.get("depth", 0),
        "score": result.metadata.get("score", 0),
    }

    try:
        content = result.text_content() if callable(result.text_content) else (result.text_content or "")
        tree = html.fromstring(content)

        # Abstract
        abstract_elem = tree.xpath('//blockquote[@class="abstract"]/text()')
        metadata["abstract"] = " ".join(a.strip() for a in abstract_elem).replace("Abstract: ", "")

        # Authors
        authors_elem = tree.xpath('//div[@class="authors"]/a/text()')
        metadata["authors"] = ", ".join(a.strip() for a in authors_elem)

        # PDF link
        pdf_elem = tree.xpath('//a[contains(@href, "/pdf/")]/@href')
        if pdf_elem:
            metadata["pdf_url"] = "https://arxiv.org" + pdf_elem[0]

        # Year
        year_elem = tree.xpath('//meta[@name="citation_date"]/@content')
        if year_elem:
            metadata["year"] = year_elem[0][:4]
    except Exception as e:
        print(f"❌ Failed to extract metadata from {result.url}: {e}")

    return metadata

# Save results to JSON
def save_results(results, filename=None):
    if not filename:
        filename = f"arxiv_ai_papers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    data = [extract_metadata(r) for r in results]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Results saved to {filename}")

# Main async runner
async def run_crawler():
    print("🚀 Starting Crawl4AI on arXiv...")

    # Filters to stay within arxiv.org and only crawl HTML pages
    filter_chain = FilterChain([
        DomainFilter(allowed_domains=["arxiv.org"]),
        ContentTypeFilter(allowed_types=["text/html"]),
    ])

    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=3,
            include_external=False,
            max_pages=100
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        stream=True,
        verbose=True,
        filter_chain=filter_chain,
        scoring_function=score_ai_papers,
    )

    results = []
    async with AsyncWebCrawler() as crawler:
        async for result in crawler.arun(
            "https://arxiv.org/search/?query=machine+learning&searchtype=all",
            config=config
        ):
            if "/abs/" not in result.url:
                continue
            if result.metadata.get("score", 0) == 0:
                continue
            results.append(result)
            print(f"✅ Depth {result.metadata.get('depth', 0)} | Score: {result.metadata.get('score', 0):.2f} | {result.url}")

    print(f"\n📦 Finished crawling. {len(results)} relevant papers found.")
    save_results(results)

# Run script
if __name__ == "__main__":
    asyncio.run(run_crawler())