# Provider Inventory — Phase 1.1C

> **Evidence First**: All contracts in this inventory were derived from live infrastructure interrogation, not documentation or memory.

## Crawl4AI

| Attribute | Value | Evidence |
|-----------|-------|----------|
| **Service** | Content crawling and web scraping | OpenAPI spec + live interrogation |
| **Container** | `unclecode/crawl4ai:latest` (ID: `8584c3c394d2`) | `docker ps` |
| **Host** | `http://localhost:11235` | Docker port mapping |
| **Auth** | Bearer token via `Authorization: Bearer <token>` | OpenAPI spec section "BearerAuth" + live 401 response without token |
| **Token source** | Docker env `CRAWL4AI_API_TOKEN=SterlingKnowledge2026` | `docker inspect 8584c3c394d2` |
| **Version** | `0.9.0` | `GET /health` response JSON field `version` |
| **OpenAPI** | `GET /openapi.json` | Live fetch on `http://localhost:11235/openapi.json` |

### Verified Endpoints

| Method | Path | Request | Response | Evidence |
|--------|------|---------|----------|----------|
| `GET` | `/health` | — | `{"status": "ok", "timestamp": ..., "version": "0.9.0"}` | `curl -X GET http://localhost:11235/health -H "Authorization: Bearer SterlingKnowledge2026"` |
| `POST` | `/crawl` | `{"urls": ["https://..."], ...}` | `{"success": true, "results": [{url, html, markdown, cleaned_html, metadata, links, status_code, session_id, media, ...}], "server_processing_time_s": ..., "server_memory_delta_mb": ...}` | `curl -X POST http://localhost:11235/crawl -H "Authorization: Bearer SterlingKnowledge2026" -H "Content-Type: application/json" -d '{"urls":["https://example.com"]}'` |
| `POST` | `/md` | `{"url": "...", "f": "raw"}` | `{"markdown": "...", "success": true}` | `curl -X POST http://localhost:11235/md -H "Authorization: Bearer SterlingKnowledge2026" -H "Content-Type: application/json" -d '{"url":"https://example.com"}'` |
| `POST` | `/html` | — | — | OpenAPI spec |
| `POST` | `/screenshot` | — | — | OpenAPI spec |
| `POST` | `/pdf` | — | — | OpenAPI spec |
| `POST` | `/execute_js` | — | — | OpenAPI spec |

### Async Limitation

`POST /crawl/job` returns HTTP 500 in version 0.9.0. Must use synchronous `POST /crawl`.

### Response Field Map

| Crawl4AI field | Provider metadata key | Type | Notes |
|----------------|----------------------|------|-------|
| `results[0].markdown` | (content) | `str` | Primary content for Processing Layer |
| `results[0].html` | (fallback content) | `str` | Used when markdown is empty |
| `results[0].metadata.title` | `title` | `Optional[str]` | From `<title>` tag |
| `results[0].metadata.description` | `description` | `Optional[str]` | From `<meta name="description">` |
| `results[0].metadata.keywords` | `keywords` | `Optional[str]` | From `<meta name="keywords">` |
| `results[0].metadata.author` | `author` | `Optional[str]` | From `<meta name="author">` |
| `results[0].url` | `url` | `str` | Crawled URL |
| `results[0].status_code` | `status_code` | `int` | HTTP status of crawled page |
| `results[0].session_id` | `session_id` | `str` | Unique session identifier |
| `results[0].links.internal` | `links.internal` | `list` | Internal links |
| `results[0].links.external` | `links.external` | `list` | External links |
| `results[0].media` | `media` | `dict` | Images, videos, etc. |
| `results[0].redirected_url` | `redirected_url` | `Optional[str]` | Final URL after redirects |
| `results[0].cache_status` | `cache_status` | `Optional[str]` | Cache hit/miss |
| `results[0].extracted_content` | (fallback content) | `str` | Used when no markdown or html |
| `server_processing_time_s` | `server_processing_time_s` | `float` | Server-side processing time |
| `server_memory_delta_mb` | `server_memory_delta_mb` | `float` | Memory delta |

---

## SearXNG

| Attribute | Value | Evidence |
|-----------|-------|----------|
| **Service** | Meta-search engine (aggregates 70+ search engines) | `GET /` HTML, `/config` response |
| **Container** | `searxng/searxng:latest` | `docker ps` |
| **Host** | `http://localhost:8080` | Docker port mapping |
| **Auth** | None (public, no API key required) | Successful `curl` without any auth header |
| **Version** | `2026.6.22+75c1b1dad` | `<meta name="generator" content="searxng-2026.6.22+75c1b1dad">` in root HTML |

### Verified Endpoints

| Method | Path | Request | Response | Evidence |
|--------|------|---------|----------|----------|
| `GET` | `/` | — | HTML with meta generator tag | `curl http://localhost:8080` |
| `GET` | `/search` | `q=test&format=json` | Full search JSON | `curl "http://localhost:8080/search?q=test&format=json"` |
| `GET` | `/config` | — | Engine configuration JSON | `curl http://localhost:8080/config` |
| `GET` | `/about` | — | HTML about page | `curl http://localhost:8080/about` |
| `GET` | `/preferences` | — | HTML preferences page | `curl http://localhost:8080/preferences` |
| `GET` | `/stats` | — | Usage statistics | `curl http://localhost:8080/stats` |

### Search Response Field Map

| SearXNG field | Provider metadata key | Type | Notes |
|---------------|----------------------|------|-------|
| `query` | `query` | `str` | Original search query |
| `results[].url` | `results[].url` | `str` | Result URL |
| `results[].title` | `results[].title` | `str` | Result title |
| `results[].content` | `results[].content` | `str` | Result snippet/content |
| `results[].engine` | `results[].engine` | `str` | Search engine that returned this result |
| `results[].score` | `results[].score` | `float` | Relevancy score |
| `results[].category` | `results[].category` | `str` | Result category |
| `results[].publishedDate` | `results[].published_date` | `Optional[str]` | Publication date |
| `results[].thumbnail` | `results[].thumbnail` | `Optional[str]` | Thumbnail URL |
| `results[].template` | `results[].template` | `str` | UI template type |
| `results[].parsed_url` | `results[].parsed_url` | `list` | Parsed URL parts |
| `suggestions` | `suggestions` | `list[str]` | Search suggestions |
| `answers` | `answers` | `list[str]` | Direct answers |
| `infoboxes` | `infoboxes` | `list[dict]` | Infobox data |
| `corrections` | `corrections` | `list[str]` | Spelling corrections |
| `unresponsive_engines` | `unresponsive_engines` | `list[str]` | Engines that didn't respond |

### Query Parameters

| Parameter | Provider option key | Type | Default | Notes |
|-----------|-------------------|------|---------|-------|
| `q` | (from `request.target`) | `str` | — | Search query (required) |
| `format` | (always `json`) | `str` | `json` | Response format |
| `engines` | `request.options["engines"]` | `str` | — | Comma-separated engine names |
| `language` | `request.options["language"]` | `str` | — | Language code (e.g. `en-US`) |
| `categories` | `request.options["categories"]` | `str` | — | Comma-separated categories |
| `pageno` | `request.options["pageno"]` | `int` | `1` | Page number |

---

## Discovery Methodology

Both provider contracts were derived using the following interrogation sequence:

1. **Container Identification**: `docker ps` to identify running containers, their images, ports, and environment variables
2. **Service Probe**: `curl` to root endpoint, check HTTP response status
3. **OpenAPI Discovery**: Where available (Crawl4AI), fetch `GET /openapi.json` for full schema
4. **Path Fuzzing**: Systematic probe of known/guesed paths (`/health`, `/search`, `/config`, `/about`, etc.)
5. **Auth Discovery**: Request without auth to observe 401/403 behavior; inspect Docker env for token names
6. **Payload Discovery**: Systematic probe of POST endpoints with different JSON shapes to find working schemas
7. **Response Field Mapping**: Parse response JSON, map fields to provider metadata keys
8. **Version Discovery**: From health endpoint (Crawl4AI) or HTML meta tag (SearXNG)
