# Processing Pipeline — Normalization and Enrichment Specification

## Purpose

This document defines the Processing Pipeline architecture that transforms raw content from providers into canonical Knowledge Objects. The pipeline applies a series of processing stages, each with specific responsibilities, to normalize diverse content formats into a unified representation.

## Scope

This document specifies:
- Pipeline stage definitions and order
- Data transformations at each stage
- Error handling within the pipeline
- Stage skip conditions
- Extension points for new processing capabilities
- Configuration parameters per stage

## Design Rationale

The Processing Pipeline exists because raw content from providers is highly heterogeneous. HTML pages, API JSON responses, RSS feeds, PDF files, and database records all have different structures, encodings, and quality levels. The pipeline normalizes this diversity into a single canonical form (the Knowledge Object) that every downstream subsystem can consume identically.

The pipeline uses a stage-based architecture because:
1. Each stage has a single, well-defined responsibility
2. Stages can be tested independently
3. New stages can be added without modifying existing ones
4. Stages can be conditionally skipped based on content type or processing results
5. Failure at one stage does not necessarily invalidate previous work (partial pipeline recovery)

## Pipeline Architecture

```
Raw Content Bundle → [Clean] → [Normalize] → [Extract] → [Markdown] → [Chunk] → [Enrich] → Knowledge Objects
                                                                                       ↓
                                                                                [Validate] → Storage
```

### Stage Execution Model

- Stages execute sequentially in the order shown above
- Each stage receives the output of the previous stage as input
- A stage may produce multiple outputs (e.g., Chunk produces one object per chunk)
- If a stage fails, downstream stages are skipped; partial results are returned with reduced confidence
- Stage failures do not terminate the entire pipeline — they trigger fallback or confidence reduction

## Pipeline Stages

### Stage 1: Clean

**Input**: Raw content bytes/string from the Acquisition Layer.

**Output**: Cleaned content with markup removed, encoding normalized, and obvious artifacts stripped.

**Responsibilities**:
- Detect and normalize character encoding (UTF-8 conversion)
- Remove HTML tags while preserving readable text structure
- Strip scripts, styles, and non-content elements
- Normalize whitespace (collapse multiple spaces/newlines)
- Remove tracking pixels, ads, navigation menus (for web content)
- Handle binary content detection (skip processing for non-text binaries)

**Configuration**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `strip_scripts` | true | Remove `<script>` and `<style>` tags |
| `strip_navigation` | true | Remove nav, header, footer elements from web pages |
| `normalize_whitespace` | true | Collapse multiple whitespace characters |
| `max_content_length` | 10MB | Maximum content size to process |

**Skip Condition**: Content is already in a clean format (e.g., JSON API response with structured data). The stage passes through without modification.

### Stage 2: Normalize

**Input**: Cleaned content from the Clean stage.

**Output**: Content normalized to a consistent structure with extracted metadata.

**Responsibilities**:
- Identify content type (article, documentation, code snippet, list, table)
- Extract structured metadata if present (Open Graph tags, JSON-LD, meta tags)
- Detect language using language detection library
- Normalize heading hierarchy (ensure H1 exists, fix nested headings)
- Convert relative URLs to absolute URLs
- Standardize quote and special character encoding

**Configuration**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `detect_language` | true | Auto-detect content language |
| `normalize_headings` | true | Fix heading hierarchy inconsistencies |
| `resolve_relative_urls` | true | Convert relative URLs to absolute |

**Skip Condition**: Content has no extractable structured metadata and is already in normalized form.

### Stage 3: Extract

**Input**: Normalized content with metadata from the Normalize stage.

**Output**: Content with extracted entities, citations, references, and structured data fields.

**Responsibilities**:
- Extract title from content (heading analysis or metadata)
- Extract authors from bylines, metadata, or author sections
- Extract publication date from metadata or content patterns
- Detect and extract citation/reference sections
- Identify external links that may represent citations
- Extract tables and convert to structured format where possible
- Identify code blocks and preserve formatting

**Configuration**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `extract_citations` | true | Attempt to find and extract citation references |
| `extract_tables` | true | Parse HTML tables into structured data |
| `extract_authors` | true | Attempt author detection from content |

**Skip Condition**: Content type does not support extraction (e.g., pure code files with no metadata).

### Stage 4: Markdown

**Input**: Extracted content with metadata from the Extract stage.

**Output**: Canonical markdown representation of the content.

**Responsibilities**:
- Convert cleaned HTML/content to standardized markdown
- Preserve heading hierarchy in markdown (`#`, `##`, `###`)
- Convert lists, tables, code blocks, and blockquotes to markdown equivalents
- Preserve image references (store as markdown `![alt](url)` with metadata)
- Ensure consistent markdown formatting (spacing, emphasis syntax)
- Generate content hash for deduplication

**Configuration**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `preserve_code_formatting` | true | Maintain code block language tags and indentation |
| `max_heading_depth` | 6 | Maximum heading level to preserve (1-6) |
| `inline_images` | false | Store image data inline vs. reference by URL |

**Output Guarantee**: The markdown output is deterministic given the same input. This ensures that re-processing identical content produces identical markdown (and thus identical content_hash).

### Stage 5: Chunk

**Input**: Markdown content from the Markdown stage.

**Output**: One or more chunk Knowledge Objects, each representing a retrievable unit of the parent document.

**Responsibilities**:
- Split markdown content into chunks based on configured strategy
- Each chunk preserves context (heading hierarchy, surrounding text)
- Chunks reference their parent document via `parent_id`
- Compute overlap between adjacent chunks to preserve continuity
- Assign chunk indices and total count metadata

**Chunking Strategies** (configurable):

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `semantic` | Split at natural boundaries (headings, paragraph breaks) | General purpose, preserves meaning |
| `fixed_size` | Split by character/word count with overlap | Uniform chunk sizes for embedding models |
| `hierarchical` | Create nested chunks (section → subsection → paragraph) | Multi-granularity search |

**Configuration**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `strategy` | semantic | Chunking strategy to use |
| `chunk_size_tokens` | 512 | Target chunk size in tokens (for fixed_size strategy) |
| `overlap_tokens` | 50 | Token overlap between adjacent chunks |
| `min_chunk_size_tokens` | 50 | Minimum chunk size; smaller content is not chunked |

**Skip Condition**: Content is shorter than `min_chunk_size_tokens`. A single document-type Knowledge Object is created without chunking.

### Stage 6: Enrich

**Input**: Chunk (or document) Knowledge Objects from the Chunk stage.

**Output**: Knowledge Objects with computed confidence scores, relationship data, and semantic metadata.

**Responsibilities**:
- Compute confidence score based on source trust, content completeness, processing quality, and evidence strength
- Detect relationships to existing knowledge objects in the Knowledge Layer (similar content, referenced topics)
- Assign topic classifications from predefined taxonomy or learned classification
- Extract entities (persons, organizations, products, concepts) for graph storage
- Compute word count and other derived metrics
- Attach acquisition chain records

**Configuration**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `compute_confidence` | true | Calculate confidence score |
| `detect_relationships` | true | Find related existing knowledge objects |
| `classify_topics` | true | Assign topic labels |
| `extract_entities` | false | Extract named entities (optional, resource-intensive) |

**Note**: Some enrichment operations (LLM-based classification, entity extraction) may be optional and configurable based on available resources.

### Stage 7: Validate

**Input**: Enriched Knowledge Objects from the Enrich stage.

**Output**: Validated Knowledge Objects ready for storage, or rejection with reason.

**Responsibilities**:
- Verify all required fields are present and valid
- Check that content hashes are correctly computed
- Verify parent-child relationships for chunks (parent exists)
- Validate confidence score is within acceptable range (0.0 - 1.0)
- Ensure no duplicate content (hash comparison against existing objects)
- Verify evidence requirements from the acquisition plan are met

**Validation Outcomes**:

| Outcome | Action |
|---------|--------|
| `passed` | Object is ready for storage |
| `warning` | Object stored with warning flags; confidence may be reduced |
| `rejected` | Object discarded; reason logged; acquisition chain records preserved |

## Error Handling Within Pipeline

### Stage Failure Behavior

When a stage fails:

1. The failure is caught and recorded in the acquisition chain
2. Confidence score is reduced proportionally to the stage's importance
3. Downstream stages are skipped
4. Partial results (output from completed stages) are returned with warning flags
5. The Knowledge Layer stores partial objects if they meet minimum validation criteria

### Confidence Reduction Rules

| Stage Failed | Confidence Impact |
|-------------|-------------------|
| Clean | -0.10 (content may have artifacts) |
| Normalize | -0.05 (metadata may be incomplete) |
| Extract | -0.10 (citations/entities missing) |
| Markdown | -0.15 (canonical form not achieved) |
| Chunk | 0 (chunking is optional optimization) |
| Enrich | -0.05 (relationships/topics missing) |
| Validate (warning) | -0.05 (minor issues detected) |

Confidence cannot go below 0.0 or above 1.0 after adjustments.

### Pipeline Recovery

If a stage fails but previous stages produced valid output:
- The pipeline attempts to recover by skipping the failed stage and continuing with downstream stages that don't depend on the failed output
- Example: If Chunking fails, the document is stored as a single unchunked object rather than being discarded entirely

## Extension Points

### Adding a New Processing Stage

1. Define the stage's input/output types (must be compatible with adjacent stages)
2. Implement the stage logic
3. Register the stage in the pipeline configuration
4. Specify its position in the execution order
5. No changes required to other stages or higher layers

### Adding a New Content Format Handler

1. Add format detection logic to the Clean or Normalize stage
2. Implement format-specific cleaning/normalization
3. Ensure output is compatible with the Markdown stage
4. Register the handler in configuration

### Adding LLM-Based Enrichment

LLM-based operations (classification, entity extraction, summarization) are added as optional enrichment sub-steps:
1. Configure which enrichment steps use LLM vs. rule-based approaches
2. Provide fallback (rule-based) when LLM is unavailable
3. LLM calls are made within the Enrich stage; results are attached to Knowledge Objects

## Configuration Summary

All pipeline stages are configurable without code changes. Key configuration categories:

| Category | Examples |
|----------|----------|
| Stage activation | Enable/disable specific stages |
| Stage parameters | Chunk size, overlap, max content length |
| Strategy selection | Chunking strategy, confidence weight defaults |
| Resource limits | Max processing time per stage, memory limits |
| LLM integration | Which enrichment steps use LLM, model selection, fallback behavior |

Configuration is documented in the CONFIGURATION.md specification.

## Assumptions

- Content encoding detection libraries are available in the implementation environment
- Language detection is accurate enough for basic classification
- Markdown conversion preserves semantic meaning of the original content
- Chunking boundaries align with natural content divisions (headings, paragraphs)

## Tradeoffs

### Deterministic vs Probabilistic Processing

**Decision**: Core pipeline stages (Clean through Markdown) are deterministic. Enrichment stage may use probabilistic methods (LLM classification).

**Rationale**: Deterministic processing ensures reproducibility and consistent output for the same input. Probabilistic enrichment adds value but is clearly separated as an optional enhancement that doesn't affect core content representation.

### Eager vs Lazy Chunking

**Decision**: Chunking happens eagerly during processing, not lazily during retrieval.

**Rationale**: Pre-chunked objects enable consistent indexing and retrieval. Lazy chunking would require storing full documents and computing chunks at query time, which is less efficient for high-throughput scenarios. Storage overhead of duplicated overlap content is acceptable given retrieval performance benefits.

### All-or-Nothing vs Partial Pipeline Results

**Decision**: Partial results are accepted when they meet minimum quality thresholds.

**Rationale**: Rejecting all partial results due to one stage failure wastes the work done by previous stages and reduces system availability. Confidence reduction provides applications with quality signals to make their own tradeoff decisions.

## Future Evolution

Future phases may add:
- Parallel processing of independent content pieces within a bundle
- Streaming processing for very large documents (process as content arrives)
- Multi-modal processing (images, audio transcripts, video metadata)
- Collaborative enrichment where multiple knowledge objects contribute to each other's metadata
- Automated quality feedback loops that tune pipeline parameters based on downstream usage patterns

All additions must integrate into the existing stage model without requiring restructuring.
