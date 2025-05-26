import asyncio
import subprocess
import json

async def main():
    print("Testing the scraper...")
    
    # Test the Python scraper directly
    test_url = "https://docs.crawl4ai.com"
    
    try:
        # Run the scraper script
        result = subprocess.run([
            "uv", "run", "helper/sequential-scraping.py", "--url", test_url
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            chunks = json.loads(result.stdout)
            print(f"\n=== Results ===")
            print(f"Total chunks: {len(chunks)}")
            
            if chunks:
                print(f"First chunk preview:")
                print(f"URL: {chunks[0]['url']}")
                print(f"Title: {chunks[0]['title']}")
                print(f"Text (first 100 chars): {chunks[0]['text'][:100]}...")
        else:
            print(f"Error running scraper: {result.stderr}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
