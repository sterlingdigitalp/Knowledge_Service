# SearXNG Provider Specification

## Purpose

This document defines the authoritative API contract for the SearXNG provider service. It serves as the single source of truth for how Knowledge_Service communicates with SearXNG through its search API.

## Infrastructure Details

- **Service**: SearXNG
- **Base URL**: `http://localhost:8080`
- **Authentication**: None required for search endpoints (public instance)
- **Protocol**: HTTP/REST with JSON or HTML responses

## Endpoints

### 1. Search Endpoint

**Endpoint**: `GET /search`

**Purpose**: Execute a search query across configured engines and return results.

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query string |
| `format` | string | No | Response format: `json` or `html` (default: `html`) |
| `categories` | string | No | Comma-separated list of categories (e.g., `general,images,news`) |
| `engines` | string | No | Comma-separated list of engines to use (e.g., `google,duckduckgo,wikipedia`) |
| `language` | string | No | Language code (e.g., `en`, `en-US`, `all`) |
| `pageno` | integer | No | Page number for pagination (default: 1) |

**Request Example**:
```
GET /search?q=Crawl4AI&format=json&language=en
```

### 2. Search Response Format (JSON)

When `format=json` is specified, SearXNG returns a JSON object with the following structure:

**Response Schema**:
```json
{
  "query": "string",                  // The search query
  "number_of_results": integer,       // Total number of results found
  "results": [                        // Array of result objects
    {
      "url": "string",                // Result URL
      "title": "string",              // Result title
      "content": "string",            // Result snippet/content preview
      "thumbnail": string|null,       // Thumbnail URL if available
      "engine": "string",             // Engine that provided this result (e.g., 'google', 'wikipedia')
      "template": "string",           // Template used for rendering (e.g., 'default.html')
      "parsed_url": [string],         // Parsed URL components: [scheme, netloc, path, ...]
      "img_src": string,              // Image source URL if available
      "priority": string,             // Priority indicator
      "engines": [string],            // List of engines that returned this result
      "positions": [integer],         // Position ranks across engines
      "score": float,                 // Relevance score
      "category": "string",           // Result category (e.g., 'general', 'images', 'news')
      "publishedDate": string|null    // Publication date if available
    }
  ],
  "answers": [string],                // Direct answers to the query (if any)
  "questions": [string],              // Related questions (if any)
  "suggestions": [string]             // Search suggestions
}
```

**Example Response**:
```json
{
  "query": "test",
  "results": [
    {
      "url": "https://www.speedtest.net/",
      "title": "Speedtest by Ookla - The Global Broadband Speed Test",
      "content": "Speedtest is better with the app. Download the Speedtest app for more metrics...",
      "thumbnail": null,
      "engine": "google",
      "template": "default.html",
      "parsed_url": ["https", "www.speedtest.net", "/", "", "", ""],
      "img_src": "",
      "priority": "",
      "engines": ["startpage", "google", "duckduckgo"],
      "positions": [1, 1, 1],
      "score": 9.0,
      "category": "general",
      "publishedDate": null
    }
  ],
  "answers": [],
  "questions": [],
  "suggestions": ["testing", "test flight", "test airport code"]
}
```

## Capabilities

Based on the API contract, SearXNG supports:
- `can_search`: true
- `can_crawl`: false (returns links, does not crawl content)
- `can_fetch_api`: false
- `supported_content_types`: [`text/html`, `application/json`]

## Rate Limits & Pagination

- **Pagination**: Supported via `pageno` parameter. Each page typically returns 10-20 results depending on configuration.
- **Rate Limits**: Depends on SearXNG instance configuration. Typical instances enforce per-IP rate limiting to prevent abuse.
- **Engines**: Results may come from multiple engines simultaneously; the `engines` array in each result indicates which engines contributed.

## Health Check

SearXNG does not typically expose a dedicated `/health` endpoint. Health is verified by:
1. Successful HTTP 200 response to `GET /search?q=test&format=json`
2. Valid JSON response with `query` and `results` fields

If the service is unhealthy, requests will return:
- HTTP 503 Service Unavailable
- HTML error page instead of JSON
- Connection refused or timeout

## Limitations & Observations

1. **No Authentication Required**: The SearXNG search endpoint is public and does not require authentication headers.
2. **JSON Format Required**: To return structured data suitable for provider abstraction, requests must include `format=json`.
3. **Result Scoring**: Results include a `score` field and `positions` array indicating ranking across engines; Knowledge_Service should use the `url` field for downstream crawling.
4. **Content Preview Only**: The `content` field in results is a snippet/preview, not the full page content. Full content acquisition requires crawling the `url`.

## Version Information

- **API Contract**: SearXNG REST search API
- **Authentication Scheme**: None (public instance)
- **Content Types**: `application/json` (when `format=json`), `text/html` (default)
