import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    DomainFilter,
    URLPatternFilter,
    ContentTypeFilter
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

async def run_advanced_crawler():
    # Create a sophisticated filter chain
    filter_chain = FilterChain([
        DomainFilter(
            allowed_domains=["docs.example.com"],
            blocked_domains=["old.docs.example.com"]
        ),
        URLPatternFilter(patterns=["*guide*", "*tutorial*", "*blog*"]),
        ContentTypeFilter(allowed_types=["text/html"])
    ])

    # Create a relevance scorer
    keyword_scorer = KeywordRelevanceScorer(
        keywords=['python', 'html'],
        weight=0.7
    )

    # Set up the configuration
    config = CrawlerRunConfig(
        deep_crawl_strategy=BestFirstCrawlingStrategy(
            max_depth=5,
            include_external=False,
            # filter_chain=filter_chain,
            url_scorer=keyword_scorer,
            max_pages=10
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        stream=True,
        verbose=True
    )

    # Execute the crawl
    results = []
    async with AsyncWebCrawler() as crawler:
        async for result in await crawler.arun("https://www.w3schools.com", config=config):
            results.append(result)  # ✅ keep the full object
            score = result.metadata.get("score", 0)
            depth = result.metadata.get("depth", 0)
            print(f"Depth: {depth} | Score: {score:.2f} | {result.url}")

    # Analyze the results
    print(f"Crawled {len(results)} high-value pages")
    avg_score = sum(r.metadata.get('score', 0) for r in results) / len(results)
    print(f"Average score: {avg_score:.2f}")

    # Group by depth
    depth_counts = {}
    for r in results:
        depth = r.metadata.get("depth", 0)
        depth_counts[depth] = depth_counts.get(depth, 0) + 1

    print("Pages crawled by depth:")
    for depth, count in sorted(depth_counts.items()):
        print(f"  Depth {depth}: {count} pages")

    # Extract only what you need (URL + score + depth + text)
    cleaned_results = []
    for r in results:
        cleaned_results.append({
            "url": r.url,
            "score": r.metadata.get("score", 0),
            "depth": r.metadata.get("depth", 0),
            "text": r.extracted_content
        })

    # Save JSON (already dicts, no need for model_dump)
    with open('W3Results.json', "w") as f:
        json.dump(cleaned_results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(run_advanced_crawler())
