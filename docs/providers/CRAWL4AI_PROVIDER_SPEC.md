# Crawl4AI Provider Specification

## Purpose

This document defines the authoritative API contract for the Crawl4AI provider service. It serves as the single source of truth for how Knowledge_Service communicates with Crawl4AI through its REST API.

## Infrastructure Details

- **Service**: Crawl4AI
- **Base URL**: `http://localhost:11235`
- **Authentication**: Bearer token via `Authorization: Bearer <token>` header
- **Protocol**: HTTP/REST with JSON payloads

## Authentication

All requests to the Crawl4AI API require authentication via the `Authorization` header:

```
Authorization: Bearer <configured-token>
```

Requests without valid authentication return:
```json
{"detail": "Authentication required"}
```

## Endpoints

### 1. Crawl Job Submission

**Endpoint**: `POST /crawl`

**Purpose**: Submit a crawl job for one or more URLs.

**Request Schema**:
```json
{
  "url": "string",                    // Required: The URL to crawl
  "session_id": "string",             // Optional: Session identifier for persistent crawling
  "priority": integer,                // Optional: Job priority (default: 1)
  "config": {                         // Optional: Crawl configuration options
    "include_html": boolean,          // Include raw HTML in response
    "include_markdown": boolean,      // Include markdown representation (default: true)
    "extract_media": boolean,         // Extract media references
    "extract_links": boolean          // Extract internal/external links
  }
}
```

**Response Schema** (Job Submitted):
```json
{
  "job_id": "string",                 // Unique identifier for the crawl job
  "status": "pending|processing|completed|failed",
  "message": "string"                 // Optional status message
}
```

**Response Schema** (Job Completed - if synchronous):
```json
{
  "job_id": "string",
  "status": "completed",
  "result": {
    "url": "string",                  // The crawled URL
    "markdown": "string",             // Markdown representation of the content
    "html": "string",                 // Raw HTML (if include_html was true)
    "media": {                        // Extracted media references
      "images": ["url1", "url2"],
      "videos": ["url1"]
    },
    "links": {                        // Extracted links
      "internal": ["url1", "url2"],
      "external": ["url3", "url4"]
    },
    "metadata": {                     // Page metadata
      "title": "string",
      "description": "string",
      "language": "string"
    }
  }
}
```

### 2. Job Status Check

**Endpoint**: `GET /status/{job_id}` or `GET /crawl/{job_id}`

**Purpose**: Check the status of a submitted crawl job or retrieve results if completed.

**Response Schema**:
```json
{
  "job_id": "string",
  "status": "pending|processing|completed|failed",
  "progress": float,                  // 0.0 to 1.0
  "result": {                         // Present only if status is 'completed'
    // Same structure as completed response above
  },
  "error": "string"                   // Present only if status is 'failed'
}
```

### 3. Cancel Job

**Endpoint**: `POST /cancel/{job_id}`

**Purpose**: Cancel a pending or processing crawl job.

**Response Schema**:
```json
{
  "job_id": "string",
  "status": "cancelled",
  "message": "Job cancellation requested"
}
```

### 4. Health Check

**Endpoint**: `GET /health` or `GET /status`

**Purpose**: Verify the Crawl4AI service is operational.

**Response Schema**:
```json
{
  "status": "healthy",
  "version": "string",                // Crawl4AI version
  "workers_available": integer,       // Number of available crawl workers
  "queue_length": integer             // Current number of pending jobs
}
```

## Error Responses

| Status Code | Response Format | Meaning |
|------------|-----------------|---------|
| 401 | `{"detail": "Authentication required"}` | Missing or invalid Bearer token |
| 400 | `{"detail": "Validation error", "errors": [...]}` | Invalid request payload |
| 404 | `{"detail": "Job not found"}` | Job ID does not exist |
| 429 | `{"detail": "Rate limit exceeded"}` | Too many requests |
| 500 | `{"detail": "Internal server error"}` | Crawl4AI internal failure |
| 503 | `{"detail": "Service unavailable"}` | Service temporarily unable to handle request |

## Capabilities

Based on the API contract, Crawl4AI supports:
- `can_crawl`: true
- `can_fetch_api`: false (primarily for HTML/web pages)
- `supported_content_types`: [`text/html`, `application/xhtml+xml`, `text/markdown`]
- `max_depth`: Configurable via request config (typically 1-3 for single-page crawl)

## Limitations & Observations

1. **Authentication Required**: All endpoints require Bearer token authentication. No unauthenticated access is permitted.
2. **Async Job Model**: Crawl operations are typically job-based (submit → poll status → retrieve result), though synchronous completion may be supported depending on configuration.
3. **Markdown Priority**: The `include_markdown` option is the primary output format for Knowledge_Service consumption.
4. **Session Support**: `session_id` parameter enables persistent crawling sessions for multi-page traversal.

## Version Information

- **API Contract**: FastAPI/OpenAPI 3.x
- **Authentication Scheme**: Bearer token in `Authorization` header
- **Content Types**: `application/json` for requests and responses
