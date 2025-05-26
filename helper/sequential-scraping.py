import asyncio
from typing import List, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import requests
from xml.etree import ElementTree
from urllib.parse import urljoin

async def crawl_sequential(urls: List[str]):
    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )

    crawl_config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator()
    )

    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        session_id = "session1"
        for url in urls:
            result = await crawler.arun(
                url=url,
                config=crawl_config,
                session_id=session_id
            )
            if result.success:
                print(f"Successfully crawled: {url}")
                print(f"Markdown length: {len(result.markdown.raw_markdown)}")
            else:
                print(f"Failed: {url} - Error: {result.error_message}")
    finally:
        await crawler.close()

def fetch_sitemap_urls(base_url: str) -> List[str]:
    sitemap_locations = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap/sitemap.xml"
    ]
    
    urls = []
    for sitemap_path in sitemap_locations:
        sitemap_url = urljoin(base_url, sitemap_path)
        try:
            response = requests.get(sitemap_url)
            response.raise_for_status()
            
            root = ElementTree.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # first check if this is a sitemap index
            sitemaps = root.findall('.//ns:sitemap/ns:loc', namespace)
            if sitemaps:
                for sitemap in sitemaps:
                    sub_urls = fetch_sitemap_urls(sitemap.text)
                    urls.extend(sub_urls)
            else:
                # Regular sitemap
                found_urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
                urls.extend(found_urls)
            
            # if URLs found no need to try other sitemap locations
            if urls:
                break
                
        except Exception:
            continue
            
    return urls

async def scrape_site(base_url: str):
    print(f"\n=== Scraping {base_url} ===")
    
    urls = fetch_sitemap_urls(base_url)
    if urls:
        print(f"Found {len(urls)} URLs to crawl")
        await crawl_sequential(urls)
    else:
        print("No URLs found in sitemap")

async def main():
    await scrape_site("https://docs.crawl4ai.com")

if __name__ == "__main__":
    asyncio.run(main())