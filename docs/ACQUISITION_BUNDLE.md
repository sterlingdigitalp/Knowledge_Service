# Acquisition Bundle — Contract Between Acquisition and Processing Layers

## Purpose

This document defines the `AcquisitionBundle` — the canonical data structure that passes acquired raw content from the Acquisition Layer to the Processing Layer. It serves as the contract between these two layers, ensuring that all acquired content is delivered with complete context, metadata, and evidence of acquisition.

## Scope

This document specifies:
- The complete structure of the AcquisitionBundle
- All fields and their types
- Provider execution results
- Timing and metrics data
- Warnings and errors encountered during acquisition

## Design Rationale

The AcquisitionBundle exists to ensure that the Processing Layer receives not just raw content, but the complete context of how that content was acquired. This includes:
- Which providers were used
- What the raw responses were
- How long acquisition took
- Any warnings or errors encountered
- Discovered URLs and acquired documents

This context is essential for the Processing Layer to:
1. Normalize content correctly
2. Compute accurate confidence scores
3. Preserve evidence and provenance
4. Handle partial results gracefully

## AcquisitionBundle Structure

### Core Identity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | String | Yes | Correlation ID from the original API request |
| `plan_id` | String | Yes | Identifier for the acquisition plan that was executed |
| `acquisition_timestamp` | ISO 8601 timestamp | Yes | When the acquisition bundle was created/completed |

### Provider Executions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider_executions` | Array of ExecutionRecord objects | Yes | Complete record of each provider execution during plan execution |

#### ExecutionRecord Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step_id` | String | Yes | Identifier for the acquisition step |
| `provider_name` | String | Yes | Name of the provider that executed (e.g., "searxng-main", "crawl4ai-primary") |
| `provider_type` | Enum | Yes | Type classification: `search`, `crawl`, `api`, `rss`, `file_processor`, `database` |
| `target` | String | Yes | The target that was acquired (URL, query string, etc.) |
| `status` | Enum | Yes | Outcome: `success`, `partial`, `failed`, `cached` |
| `raw_response` | Object/Bytes | Conditional | The raw response from the provider. Present only if status is `success` or `partial`. |
| `response_metadata` | Object | Conditional | Provider-specific metadata (headers, status codes, etc.) |
| `latency_ms` | Integer | Yes | Time taken for this execution in milliseconds |
| `error_code` | String | Conditional | Standardized error code if status is `failed`. Omitted on success. |
| `error_message` | String | Conditional | Error message if status is `failed`. Omitted on success. |

### Discovered URLs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `discovered_urls` | Array of Strings | Yes | All URLs discovered during acquisition (from search results, link extraction, etc.) |

### Acquired Documents

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `acquired_documents` | Array of DocumentRecord objects | Yes | Records of each document that was successfully acquired and contains raw content |

#### DocumentRecord Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | String | Yes | Unique identifier for this acquired document (typically derived from URL or job_id) |
| `url` | URI | Yes | The URL of the acquired document |
| `provider_name` | String | Yes | Provider that acquired this document |
| `content_type` | String | Yes | MIME type or format (e.g., `text/html`, `text/markdown`, `application/json`) |
| `raw_content` | Bytes/String | Yes | The raw content acquired from the provider |
| `content_size_bytes` | Integer | Yes | Size of the raw content in bytes |
| `acquired_at` | ISO 8601 timestamp | Yes | When this document was acquired |

### Timing Metrics

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `total_duration_ms` | Integer | Yes | Total time from plan execution start to completion |
| `search_duration_ms` | Integer | Conditional | Time spent on search provider executions |
| `crawl_duration_ms` | Integer | Conditional | Time spent on crawl provider executions |

### Provider Metrics

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `providers_queried` | Integer | Yes | Number of distinct providers queried |
| `providers_successful` | Integer | Yes | Number of provider executions that succeeded |
| `providers_failed` | Integer | Yes | Number of provider executions that failed |
| `cache_hits` | Integer | Yes | Number of acquisitions served from cache |
| `cache_misses` | Integer | Yes | Number of acquisitions requiring fresh acquisition |

### Acquisition Warnings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `warnings` | Array of Warning objects | Optional | Non-fatal issues encountered during acquisition that do not prevent processing |

#### Warning Object Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | String | Yes | Warning code (e.g., `PARTIAL_ACQUISITION`, `HIGH_LATENCY`, `CACHE_STALE`) |
| `message` | String | Yes | Human-readable warning description |
| `affected_steps` | Array of Strings | Optional | Step IDs affected by this warning |

### Acquisition Errors

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `errors` | Array of Error objects | Optional | Fatal issues that prevented completion of the acquisition plan |

#### Error Object Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | String | Yes | Error code (e.g., `ALL_PROVIDERS_FAILED`, `TIMEOUT_EXCEEDED`) |
| `message` | String | Yes | Human-readable error description |
| `severity` | Enum | Yes | `critical`, `warning`, `info` |

## Complete AcquisitionBundle Example (Conceptual)

```
AcquisitionBundle {
  request_id: "req-abc-123",
  plan_id: "plan-def-456",
  acquisition_timestamp: "2026-06-25T15:30:00Z",

  provider_executions: [
    {
      step_id: "step-search-001",
      provider_name: "searxng-main",
      provider_type: "search",
      target: "Crawl4AI",
      status: "success",
      raw_response: {
        query: "Crawl4AI",
        results: [...],
        number_of_results: 15
      },
      response_metadata: { status_code: 200 },
      latency_ms: 340,
      error_code: null,
      error_message: null
    },
    {
      step_id: "step-crawl-001",
      provider_name: "crawl4ai-primary",
      provider_type: "crawl",
      target: "https://github.com/unclecode/crawl4ai",
      status: "success",
      raw_response: {
        job_id: "job-xyz-789",
        status: "completed",
        result: {
          url: "https://github.com/unclecode/crawl4ai",
          markdown: "# Crawl4AI...\n\n...",
          metadata: { title: "crawl4ai..." }
        }
      },
      response_metadata: { status_code: 200 },
      latency_ms: 1250,
      error_code: null,
      error_message: null
    }
  ],

  discovered_urls: [
    "https://github.com/unclecode/crawl4ai",
    "https://crawl4ai.com",
    "https://pypi.org/project/crawl4ai/"
  ],

  acquired_documents: [
    {
      document_id: "doc-github-crawl4ai-001",
      url: "https://github.com/unclecode/crawl4ai",
      provider_name: "crawl4ai-primary",
      content_type: "text/markdown",
      raw_content: "# Crawl4AI...\n\n...",
      content_size_bytes: 45200,
      acquired_at: "2026-06-25T15:30:01Z"
    }
  ],

  total_duration_ms: 1650,
  search_duration_ms: 340,
  crawl_duration_ms: 1250,

  providers_queried: 2,
  providers_successful: 2,
  providers_failed: 0,
  cache_hits: 0,
  cache_misses: 2,

  warnings: [],

  errors: []
}
```

## Usage by Processing Layer

The Processing Layer consumes the AcquisitionBundle to:

1. **Iterate through acquired_documents**: Each DocumentRecord represents raw content that needs normalization
2. **Reference provider_executions for context**: Execution records provide metadata about how content was acquired (latency, status, provider name)
3. **Check warnings and errors**: If errors exist, Processing may need to reject or flag the bundle; warnings may reduce confidence scores
4. **Use discovered_urls for relationship mapping**: Discovered URLs may be used to identify related content or future acquisition targets

## Constraints and Guarantees

- **No Processing**: The AcquisitionBundle contains only raw acquired content and acquisition context. No normalization, chunking, or Knowledge Object creation occurs in the Acquisition Layer.
- **No Knowledge Objects**: The AcquisitionBundle is not a Knowledge Object. It is the input to the Processing Layer, which produces Knowledge Objects.
- **Preservation of Raw Content**: All raw_content fields preserve the exact bytes/string received from providers, without modification.
- **Evidence of Acquisition**: The provider_executions array serves as the acquisition history/evidence for all acquired documents.

## Extension Points

### Adding New Provider Types

New provider types (e.g., `pdf_processor`, `youtube_transcript`) can be added by:
1. Extending the `provider_type` enum in ExecutionRecord
2. Ensuring the provider returns raw_response in the format expected by the Processing Layer

### Adding New Warning/Error Codes

New warning or error codes extend the existing code enums without breaking consumers. The Processing Layer ignores codes it does not recognize (forward compatibility).

## Assumptions

- ISO 8601 timestamps are supported by all systems
- JSON is the primary serialization format for the bundle
- Raw content may be large; streaming or pagination may be required for very large bundles

## Future Evolution

Future phases may add:
- Content hash pre-computation (computed by Acquisition Layer before passing to Processing)
- Provider health metrics integration
- Cost tracking per execution

All additions must maintain the contract that Acquisition Layer produces raw content + context, and Processing Layer produces Knowledge Objects.