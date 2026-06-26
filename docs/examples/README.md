# Knowledge Object Examples — Phase 1.2B

> Reference implementations showing the complete Knowledge Object structure for different content types.

## Example 1: Programming Documentation

```json
{
  "id": "019f00a3-8a10-7b4a-b8e1-3c5d6e7f8a9b",
  "version": 1,
  "type": "document",
  "source_id": "crawl4ai-primary",
  "source_url": "https://docs.python.org/3/tutorial/classes.html",
  "source_type": "web_page",
  "acquired_at": "2026-06-25T14:30:00Z",
  "published_at": "2026-06-20T09:00:00Z",
  "updated_at": "2026-06-25T14:30:00Z",
  "markdown": "# Classes\n\nClasses provide a means of bundling data and functionality together.\n\n## Class Definition Syntax\n\n```python\nclass ClassName:\n    <statement-1>\n    ...\n    <statement-N>\n```\n\n## Class Objects\n\nClass objects support two kinds of operations: attribute references and instantiation.",
  "structured_data": null,
  "raw_content_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "content_hash": "f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5",
  "title": "Classes — Python 3.13 Documentation",
  "authors": ["Python Software Foundation"],
  "language": "en",
  "topics": ["programming", "documentation"],
  "word_count": 1200,
  "confidence": 0.92,
  "evidence_count": 3,
  "citations": [
    {
      "target_id": null,
      "target_url": "https://docs.python.org/3/tutorial/classes.html",
      "context": "Official Python documentation for classes",
      "citation_type": "reference"
    }
  ],
  "acquisition_chain": [
    {
      "provider_name": "crawl4ai-primary",
      "provider_type": "crawler",
      "request_id": "req-py-docs-001",
      "timestamp": "2026-06-25T14:30:00Z",
      "status": "success",
      "response_size_bytes": 45200,
      "latency_ms": 1200
    }
  ],
  "storage_backend": "primary-store-01",
  "index_status": "indexed",
  "retention_policy_id": "default-long-term"
}
```

---

## Example 2: Research Paper

```json
{
  "id": "019f00a3-8a11-7b4a-b8e1-4c5d6e7f8a9c",
  "version": 1,
  "type": "document",
  "source_id": "crawl4ai-primary",
  "source_url": "https://arxiv.org/abs/2401.12345",
  "source_type": "web_page",
  "acquired_at": "2026-06-25T15:00:00Z",
  "published_at": "2024-01-15T00:00:00Z",
  "updated_at": "2026-06-25T15:00:00Z",
  "markdown": "# Attention Is All You Need\n\n**Abstract**: The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...\n\n## 1. Introduction\n\nRecurrent neural networks have been the dominant approach for sequence modeling...\n\n## 2. Background\n\n### 2.1 Transformer Architecture\n\nThe Transformer follows an encoder-decoder structure...",
  "structured_data": {
    "doi": "10.1234/arxiv.2401.12345",
    "arxiv_id": "2401.12345",
    "submitted_date": "2024-01-15",
    "authors_full": ["Vaswani, Ashish", "Shazeer, Noam", "Parmar, Niki"],
    "categories": ["cs.CL", "cs.LG"]
  },
  "raw_content_hash": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
  "content_hash": "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
  "title": "Attention Is All You Need",
  "authors": ["Vaswani, Ashish", "Shazeer, Noam", "Parmar, Niki"],
  "language": "en",
  "topics": ["programming", "data_science", "science"],
  "word_count": 8500,
  "confidence": 0.88,
  "evidence_count": 5,
  "citations": [
    {
      "target_id": null,
      "target_url": "https://arxiv.org/abs/1706.03762",
      "context": "Original Transformer paper being referenced",
      "citation_type": "reference"
    }
  ],
  "acquisition_chain": [
    {
      "provider_name": "crawl4ai-primary",
      "provider_type": "crawler",
      "request_id": "req-arxiv-001",
      "timestamp": "2026-06-25T15:00:00Z",
      "status": "success",
      "response_size_bytes": 128000,
      "latency_ms": 3400
    }
  ],
  "storage_backend": "primary-store-01",
  "index_status": "indexed",
  "retention_policy_id": "permanent"
}
```

---

## Example 3: News Article

```json
{
  "id": "019f00a3-8a12-7b4a-b8e1-5c5d6e7f8a9d",
  "version": 1,
  "type": "document",
  "source_id": "crawl4ai-primary",
  "source_url": "https://reuters.com/article/technology/ai-regulation-2026",
  "source_type": "web_page",
  "acquired_at": "2026-06-25T16:00:00Z",
  "published_at": "2026-06-24T08:30:00Z",
  "updated_at": "2026-06-25T16:00:00Z",
  "markdown": "# EU Proposes New AI Regulation Framework\n\nBy Sarah Johnson\n\nBRUSSELS, June 24 (Reuters) — The European Commission proposed a comprehensive framework for regulating artificial intelligence...\n\nThe framework introduces three risk categories...\n\n## Industry Reaction\n\nTech companies have expressed mixed reactions...\n\n\"This is a balanced approach,\" said a spokesperson...",
  "structured_data": null,
  "raw_content_hash": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
  "content_hash": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
  "title": "EU Proposes New AI Regulation Framework",
  "authors": ["Sarah Johnson"],
  "language": "en",
  "topics": ["business", "security"],
  "word_count": 650,
  "confidence": 0.75,
  "evidence_count": 2,
  "citations": [
    {
      "target_id": null,
      "target_url": "https://reuters.com/article/technology/ai-regulation-2026",
      "context": "Original Reuters article",
      "citation_type": "reference"
    }
  ],
  "acquisition_chain": [
    {
      "provider_name": "crawl4ai-primary",
      "provider_type": "crawler",
      "request_id": "req-reuters-001",
      "timestamp": "2026-06-25T16:00:00Z",
      "status": "success",
      "response_size_bytes": 28400,
      "latency_ms": 950
    }
  ],
  "storage_backend": "primary-store-01",
  "index_status": "indexed",
  "retention_policy_id": "default-short-term"
}
```

---

## Example 4: API Documentation

```json
{
  "id": "019f00a3-8a13-7b4a-b8e1-6c5d6e7f8a9e",
  "version": 1,
  "type": "document",
  "source_id": "crawl4ai-primary",
  "source_url": "https://stripe.com/docs/api/charges/create",
  "source_type": "web_page",
  "acquired_at": "2026-06-25T17:00:00Z",
  "published_at": null,
  "updated_at": "2026-06-25T17:00:00Z",
  "markdown": "# Create a Charge\n\n## POST /v1/charges\n\nCreates a new charge object.\n\n### Request Parameters\n\n| Parameter | Type | Required | Description |\n|-----------|------|----------|-------------|\n| `amount` | integer | yes | Amount in cents to charge |\n| `currency` | string | yes | Three-letter ISO currency code |\n| `source` | string | conditional | Payment source ID |\n| `description` | string | no | An arbitrary string |\n\n### Example Request\n\n```bash\ncurl https://api.stripe.com/v1/charges \\\n  -u sk_test_...: \\\n  -d amount=2000 \\\n  -d currency=usd \\\n  -d source=tok_visa\n```",
  "structured_data": {
    "endpoint": "/v1/charges",
    "method": "POST",
    "api_version": "2024-11-20",
    "parameters": [
      {"name": "amount", "type": "integer", "required": true},
      {"name": "currency", "type": "string", "required": true},
      {"name": "source", "type": "string", "required": false},
      {"name": "description", "type": "string", "required": false}
    ]
  },
  "raw_content_hash": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
  "content_hash": "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
  "title": "Create a Charge — Stripe API Reference",
  "authors": ["Stripe"],
  "language": "en",
  "topics": ["programming", "web_development", "documentation"],
  "word_count": 320,
  "confidence": 0.95,
  "evidence_count": 2,
  "citations": [
    {
      "target_id": null,
      "target_url": "https://stripe.com/docs/api/charges/create",
      "context": "Official Stripe API documentation",
      "citation_type": "reference"
    }
  ],
  "acquisition_chain": [
    {
      "provider_name": "crawl4ai-primary",
      "provider_type": "crawler",
      "request_id": "req-stripe-001",
      "timestamp": "2026-06-25T17:00:00Z",
      "status": "success",
      "response_size_bytes": 18500,
      "latency_ms": 780
    }
  ],
  "storage_backend": "primary-store-01",
  "index_status": "indexed",
  "retention_policy_id": "default-long-term"
}
```

---

## Example 5: GitHub README

```json
{
  "id": "019f00a3-8a14-7b4a-b8e1-7c5d6e7f8a9f",
  "version": 1,
  "type": "document",
  "source_id": "crawl4ai-primary",
  "source_url": "https://github.com/unclecode/crawl4ai",
  "source_type": "github_repository",
  "acquired_at": "2026-06-25T18:00:00Z",
  "published_at": null,
  "updated_at": "2026-06-25T18:00:00Z",
  "markdown": "# Crawl4AI\n\n## 🔥 Web Crawling for AI\n\nCrawl4AI is an open-source web crawler designed for AI applications.\n\n## Features\n\n- Async architecture\n- LLM-friendly output\n- JavaScript support\n- Multiple output formats\n\n## Quick Start\n\n```bash\npip install crawl4ai\n```\n\n```python\nimport crawl4ai as c\n\nresult = await c.crawl(url=\"https://example.com\")\nprint(result.markdown)\n```",
  "structured_data": {
    "repository": "unclecode/crawl4ai",
    "stars": 8500,
    "language": "Python",
    "license": "MIT",
    "topics": ["web-crawler", "ai", "scraping"]
  },
  "raw_content_hash": "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
  "content_hash": "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1",
  "title": "unclecode/crawl4ai — Web Crawling for AI",
  "authors": ["Unclecode"],
  "language": "en",
  "topics": ["programming", "web_development", "devops"],
  "word_count": 180,
  "confidence": 0.85,
  "evidence_count": 2,
  "citations": [
    {
      "target_id": null,
      "target_url": "https://github.com/unclecode/crawl4ai",
      "context": "Official repository",
      "citation_type": "reference"
    }
  ],
  "acquisition_chain": [
    {
      "provider_name": "crawl4ai-primary",
      "provider_type": "crawler",
      "request_id": "req-gh-001",
      "timestamp": "2026-06-25T18:00:00Z",
      "status": "success",
      "response_size_bytes": 12400,
      "latency_ms": 1100
    }
  ],
  "storage_backend": "primary-store-01",
  "index_status": "indexed",
  "retention_policy_id": "default-long-term"
}
```

---

## Example 6: Blog Post

```json
{
  "id": "019f00a3-8a15-7b4a-b8e1-8c5d6e7f8aa0",
  "version": 1,
  "type": "document",
  "source_id": "crawl4ai-primary",
  "source_url": "https://vercel.com/blog/nextjs-15-release",
  "source_type": "web_page",
  "acquired_at": "2026-06-25T19:00:00Z",
  "published_at": "2026-06-20T14:00:00Z",
  "updated_at": "2026-06-25T19:00:00Z",
  "markdown": "# Next.js 15 Released\n\n**Posted by the Vercel Team** on June 20, 2026\n\nWe are excited to announce the release of Next.js 15!\n\n## What's New\n\n### React 19 Support\n\nNext.js 15 adds full support for React 19, including Server Components...\n\n### Improved Caching\n\nWe've redesigned the caching layer...\n\n### Breaking Changes\n\n- Minimum Node.js version is now 18.17\n- The `pages` directory API has been updated...\n\n## Migration Guide\n\nSee the [migration guide](https://nextjs.org/docs/app/building-your-application/upgrading/version-15) for details.",
  "structured_data": {
    "framework": "Next.js",
    "version": "15.0.0",
    "release_date": "2026-06-20"
  },
  "raw_content_hash": "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1",
  "content_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "title": "Next.js 15 Released",
  "authors": ["Vercel Team"],
  "language": "en",
  "topics": ["programming", "web_development"],
  "word_count": 850,
  "confidence": 0.80,
  "evidence_count": 2,
  "citations": [
    {
      "target_id": null,
      "target_url": "https://nextjs.org/docs/app/building-your-application/upgrading/version-15",
      "context": "Official migration guide referenced in the blog post",
      "citation_type": "reference"
    }
  ],
  "acquisition_chain": [
    {
      "provider_name": "crawl4ai-primary",
      "provider_type": "crawler",
      "request_id": "req-vercel-001",
      "timestamp": "2026-06-25T19:00:00Z",
      "status": "success",
      "response_size_bytes": 36200,
      "latency_ms": 1050
    }
  ],
  "storage_backend": "primary-store-01",
  "index_status": "indexed",
  "retention_policy_id": "default-long-term"
}
```
