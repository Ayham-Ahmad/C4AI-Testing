import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import DFSDeepCrawlStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    DomainFilter,
    URLPatternFilter,
    ContentTypeFilter
)

async def crawl():

    # Keywords for the scorer
    keyword_scorer = KeywordRelevanceScorer(
        ['tutorial'],
        0.7
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=DFSDeepCrawlStrategy(
            max_depth=10,
            max_pages=100,
            score_threshold=0.0,
            include_external=False,
            url_scorer=keyword_scorer
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        # Wait for ALL results to be collected before returning
        results = await crawler.arun("https://www.w3schools.com", config=config)

        for result in results:
            print(result)

        for r in results:
            print(">>> Page:", r.url)
            if "links" in r.metadata:
                print("Links found:", r.metadata["links"])
            else:
                print("No links discovered")


    # Cleaning to save in JSON
    cleaned_results = []
    for r in results:
        cleaned_results.append({
            "url": r.url,
            "score": r.metadata.get("score", 0),
            "depth": r.metadata.get("depth", 0),
            "text": r.extracted_content
        })

    # Save JSON
    with open('W3Results.json', "w") as f:
        json.dump(cleaned_results, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    asyncio.run(crawl())