#!/usr/bin/env python3
import asyncio
import time
import sys

async def test_one(name, source_class, *args):
    """Test a single source with timeout."""
    start = time.time()
    try:
        src = source_class(*args)
        # Add overall timeout
        results = await asyncio.wait_for(
            src.fetch("snapdeal.com"),
            timeout=60.0
        )
        elapsed = time.time() - start
        emails = [r.email for r in results[:3]]
        print(f"{name:25} {len(results):2} emails  {elapsed:6.2f}s  {emails}")
        return len(results), elapsed, None
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"{name:25}  TIMEOUT after {elapsed:.2f}s")
        return 0, elapsed, "TIMEOUT"
    except ConnectionError as e:
        elapsed = time.time() - start
        print(f"{name:25}  CONN ERR in {elapsed:.2f}s - {type(e).__name__}")
        return 0, elapsed, str(type(e).__name__)
    except Exception as e:
        elapsed = time.time() - start
        err = str(e)[:50]
        print(f"{name:25}  ERROR in {elapsed:.2f}s - {err}")
        return 0, elapsed, err

async def main():
    from coldreach.sources.web_crawler import WebCrawlerSource
    from coldreach.sources.whois_source import WhoisSource
    from coldreach.sources.github import GitHubSource
    from coldreach.sources.reddit import RedditSource
    from coldreach.sources.search_engine import SearchEngineSource
    from coldreach.sources.intelligent_search import IntelligentSearchSource
    from coldreach.sources.harvester import HarvesterSource
    from coldreach.sources.spiderfoot import SpiderFootSource
    
    print("=" * 100)
    print("LIVE SOURCE TESTS AGAINST snapdeal.com")
    print("=" * 100)
    
    tests = [
        ("WebCrawlerSource", WebCrawlerSource),
        ("WhoisSource", WhoisSource),
        ("GitHubSource", GitHubSource),
        ("RedditSource", RedditSource),
        ("SearchEngineSource", SearchEngineSource),
        ("IntelligentSearchSource", IntelligentSearchSource),
        ("HarvesterSource", HarvesterSource),
        ("SpiderFootSource", SpiderFootSource),
    ]
    
    for name, cls in tests:
        await test_one(name, cls)

if __name__ == "__main__":
    asyncio.run(main())
