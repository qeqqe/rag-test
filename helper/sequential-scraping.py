import asyncio
import json
import sys
import argparse
from typing import List, Optional, Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import requests
from xml.etree import ElementTree
from urllib.parse import urljoin

def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """Split text into chunks of specified size"""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)
    return chunks

async def crawl_sequential(urls: List[str]) -> List[Dict[str, Any]]:
    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )

    crawl_config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator()
    )

    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    all_chunks = []

    try:
        session_id = "session1"
        for url in urls:
            result = await crawler.arun(
                url=url,
                config=crawl_config,
                session_id=session_id
            )
            if result.success:
                # Extract title from metadata or use URL as fallback
                title = getattr(result.metadata, 'title', '') or url.split('/')[-1] or url
                
                # Chunk the markdown content
                text_chunks = chunk_text(result.markdown.raw_markdown, 500)
                
                # Create chunk objects
                for text_chunk in text_chunks:
                    all_chunks.append({
                        "text": text_chunk,
                        "url": url,
                        "title": title
                    })
                
                print(f"Successfully crawled: {url} ({len(text_chunks)} chunks)", file=sys.stderr)
            else:
                print(f"Failed: {url} - Error: {result.error_message}", file=sys.stderr)
    finally:
        await crawler.close()

    return all_chunks

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

async def scrape_site(base_url: str) -> List[Dict[str, Any]]:
    print(f"\n=== Scraping {base_url} ===", file=sys.stderr)
    
    urls = fetch_sitemap_urls(base_url)
    if urls:
        print(f"Found {len(urls)} URLs to crawl", file=sys.stderr)
        chunks = await crawl_sequential(urls)
        return chunks
    else:
        print("No URLs found in sitemap", file=sys.stderr)
        return []

async def main():
    parser = argparse.ArgumentParser(description='Scrape a website and return chunked content as JSON')
    parser.add_argument('--url', required=True, help='Base URL to scrape')
    
    args = parser.parse_args()
    
    try:
        chunks = await scrape_site(args.url)
        print(json.dumps(chunks, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())