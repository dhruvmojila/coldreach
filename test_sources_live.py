#!/usr/bin/env python3
import asyncio
import time
import sys

async def test_web_crawler():
    from coldreach.sources.web_crawler import WebCrawlerSource
    src = WebCrawlerSource()
    start = time.time()
    try:
        results = await src.fetch("snapdeal.com")
        elapsed = time.time() - start
        emails = [r.email for r in results[:5]]
        print(f"WebCrawlerSource: {len(results)} emails in {elapsed:.2f}s")
        if results:
            print(f"  Sample: {emails}")
        return len(results), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"WebCrawlerSource: ERROR in {elapsed:.2f}s - {e}")
        return 0, elapsed

async def test_whois():
    from coldreach.sources.whois_source import WhoisSource
    src = WhoisSource()
    start = time.time()
    try:
        results = await src.fetch("snapdeal.com")
        elapsed = time.time() - start
        emails = [r.email for r in results[:5]]
        print(f"WhoisSource: {len(results)} emails in {elapsed:.2f}s")
        if results:
            print(f"  Sample: {emails}")
        return len(results), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"WhoisSource: ERROR in {elapsed:.2f}s - {e}")
        return 0, elapsed

async def test_github():
    from coldreach.sources.github import GitHubSource
    src = GitHubSource()
    start = time.time()
    try:
        results = await src.fetch("snapdeal.com")
        elapsed = time.time() - start
        emails = [r.email for r in results[:5]]
        print(f"GitHubSource: {len(results)} emails in {elapsed:.2f}s")
        if results:
            print(f"  Sample: {emails}")
        return len(results), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"GitHubSource: ERROR in {elapsed:.2f}s - {e}")
        return 0, elapsed

async def test_reddit():
    from coldreach.sources.reddit import RedditSource
    src = RedditSource()
    start = time.time()
    try:
        results = await src.fetch("snapdeal.com")
        elapsed = time.time() - start
        emails = [r.email for r in results[:5]]
        print(f"RedditSource: {len(results)} emails in {elapsed:.2f}s")
        if results:
            print(f"  Sample: {emails}")
        return len(results), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"RedditSource: ERROR in {elapsed:.2f}s - {e}")
        return 0, elapsed

async def test_search_engine():
    from coldreach.sources.search_engine import SearchEngineSource
    src = SearchEngineSource()
    start = time.time()
    try:
        results = await src.fetch("snapdeal.com")
        elapsed = time.time() - start
        emails = [r.email for r in results[:5]]
        print(f"SearchEngineSource: {len(results)} emails in {elapsed:.2f}s")
        if results:
            print(f"  Sample: {emails}")
        return len(results), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"SearchEngineSource: ERROR in {elapsed:.2f}s - {e}")
        return 0, elapsed

async def test_intelligent_search():
    from coldreach.sources.intelligent_search import IntelligentSearchSource
    src = IntelligentSearchSource()
    start = time.time()
    try:
        results = await src.fetch("snapdeal.com")
        elapsed = time.time() - start
        emails = [r.email for r in results[:5]]
        print(f"IntelligentSearchSource: {len(results)} emails in {elapsed:.2f}s")
        if results:
            print(f"  Sample: {emails}")
        return len(results), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"IntelligentSearchSource: ERROR in {elapsed:.2f}s - {e}")
        return 0, elapsed

async def test_harvester():
    from coldreach.sources.harvester import HarvesterSource
    src = HarvesterSource()
    start = time.time()
    try:
        results = await src.fetch("snapdeal.com")
        elapsed = time.time() - start
        emails = [r.email for r in results[:5]]
        print(f"HarvesterSource: {len(results)} emails in {elapsed:.2f}s")
        if results:
            print(f"  Sample: {emails}")
        return len(results), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"HarvesterSource: ERROR in {elapsed:.2f}s - {e}")
        return 0, elapsed

async def test_spiderfoot():
    from coldreach.sources.spiderfoot import SpiderFootSource
    src = SpiderFootSource()
    start = time.time()
    try:
        results = await src.fetch("snapdeal.com")
        elapsed = time.time() - start
        emails = [r.email for r in results[:5]]
        print(f"SpiderFootSource: {len(results)} emails in {elapsed:.2f}s")
        if results:
            print(f"  Sample: {emails}")
        return len(results), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"SpiderFootSource: ERROR in {elapsed:.2f}s - {e}")
        return 0, elapsed

async def main():
    print("=" * 70)
    print("LIVE SOURCE TESTS AGAINST snapdeal.com")
    print("=" * 70)
    
    tests = [
        ("WebCrawler", test_web_crawler),
        ("Whois", test_whois),
        ("GitHub", test_github),
        ("Reddit", test_reddit),
        ("SearchEngine", test_search_engine),
        ("IntelligentSearch", test_intelligent_search),
        ("Harvester", test_harvester),
        ("SpiderFoot", test_spiderfoot),
    ]
    
    results = {}
    for name, test in tests:
        print(f"\n[{name}]")
        count, elapsed = await test()
        results[name] = (count, elapsed)
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, (count, elapsed) in results.items():
        print(f"{name:20} {count:3} emails  {elapsed:6.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
