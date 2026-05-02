# Current Task

## Now

- Owner agent: Claude Code
- Branch: `main`
- Objective: IntelligentSearchSource: Groq+SearXNG+Reddit multi-stage pipeline. Scrapes company site → Groq generates 6 domain-specific queries + 4 subreddits → runs all concurrently through SearXNG + Reddit. Groq key loaded from pydantic-settings. Context uses SearXNG meta-descriptions (works for JS SPAs). Falls back to heuristic queries without Groq.

## In Progress

- [ ] Test full scan with intelligent_search on snapdeal.com and fareleaders.com — verify Groq-generated queries find emails that generic searches miss

## Done In This Session

- IntelligentSearchSource: Groq+SearXNG+Reddit multi-stage pipeline. Scrapes company site → Groq generates 6 domain-specific queries + 4 subreddits → runs all concurrently through SearXNG + Reddit. Groq key loaded from pydantic-settings. Context uses SearXNG meta-descriptions (works for JS SPAs). Falls back to heuristic queries without Groq.

## Next Action (Single Concrete Step)

- Test full scan with intelligent_search on snapdeal.com and fareleaders.com — verify Groq-generated queries find emails that generic searches miss

## Blockers

- None noted by automation. Update manually if needed.

## Verification Status

- 443 tests pass; Groq key loads from .env via get_settings(); Groq generates travel-industry queries for fareleaders.com; intelligent_search source is in _SLOW_SOURCE_NAMES so it runs after fast sources
