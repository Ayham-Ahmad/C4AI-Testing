import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    URLPatternFilter,
    DomainFilter,
    ContentTypeFilter,
    SEOFilter
)

async def main():
    # Configure a 2-level deep crawl
    # Create a chain of filters
    filter_chain = FilterChain([
        # Only follow URLs with specific patterns
        URLPatternFilter(patterns=["*html*", "*css*", "*Python*"]),

        # Only crawl specific domains
        # DomainFilter(
        #     allowed_domains=["https://www.w3schools.com/*"],
        #     # blocked_domains=[r"^https?://.*index\.php/?$"]
        # ),

        # Create an SEO filter that looks for specific keywords in page metadata
        SEOFilter(
            threshold=0.5,  # Minimum score (0.0 to 1.0)
            keywords=["tutorial", "guide", "documentation"]
        ),

        # Only include specific content types
        ContentTypeFilter(allowed_types=["text/html"])
    ])

    # Create a scorer
    scorer = KeywordRelevanceScorer(
        keywords=["HTML", "Example", "Python"],
        weight=0.7
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,
            include_external=False,
            max_pages=10,
            filter_chain=filter_chain,
            url_scorer=scorer,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True,
        # wait_for_timeout=5000,
        stream=False # Non-stream is to wait until the crawl is done to preprocess the data, 
                     # Stream mode is to start preprocessing when getting some data while the crawling is going on.
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://www.w3schools.com", config=config)

        print(f"Crawled {len(results)} pages in total")
        for i, result in enumerate(results[:30]):
            print(f"{i+1} URL: {result.url}")
            print(f"Depth: {result.metadata.get('depth', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
